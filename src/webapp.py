"""Flask web UI for the local RAG assistant.

Five tabs: Chat, Documents, Tests, Settings, About. Each route is a thin
wrapper around the same src.* pipeline used by the CLI.

Usage:
    python -m src.webapp
"""

import re
import shutil
import time
from pathlib import Path

from flask import Flask, jsonify, request, render_template

from . import config, db, testsuite
from .embeddings import get_embedding_backend
from .extractors import SUPPORTED_EXTENSIONS as ALLOWED_EXTENSIONS
from .ingest import run as ingest_run
from .llm import get_llm_backend
from .qa import answer_question
from .retrieval import EmbeddingBackendMismatch

app = Flask(
    __name__,
    template_folder=str(config.BASE_DIR / "templates"),
    static_folder=str(config.BASE_DIR / "static"),
)

# Strips path separators and other characters illegal in Windows/Unix paths,
# while preserving non-ASCII letters (unlike werkzeug's secure_filename,
# which strips them) - filenames and collection names may be in any language.
_UNSAFE_PATH_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

_embedder = None
_llm = None


def _safe_component(name: str) -> str:
    name = (name or "").strip()
    name = name.replace("..", "")
    name = _UNSAFE_PATH_CHARS.sub("_", name)
    return name.strip(". ")


def _collection_dir(collection: str) -> Path:
    if collection == config.DEFAULT_COLLECTION:
        return config.DOCS_DIR
    return config.DOCS_DIR / collection


def _backends():
    global _embedder, _llm
    if _embedder is None:
        _embedder = get_embedding_backend()
    if _llm is None:
        _llm = get_llm_backend()
    return _embedder, _llm


def _reindex():
    embedder, _ = _backends()
    ingest_run(config.DOCS_DIR, config.DB_PATH, reset=True, embedder=embedder)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def status():
    embedder, llm = _backends()
    db_path = Path(config.DB_PATH)
    num_chunks = num_docs = 0
    if db_path.exists():
        with db.connect(db_path) as conn:
            num_chunks = db.count_chunks(conn)
            num_docs = db.count_documents(conn)
    return jsonify(
        {
            "embedding_backend": embedder.name,
            "llm_backend": llm.name,
            "offline": True,
            "documents": num_docs,
            "chunks": num_chunks,
            "default_top_k": config.TOP_K,
            "llm_alias": config.LLM_MODEL_ALIAS,
            "embedding_alias": config.EMBEDDING_MODEL_ALIAS,
            "chunk_max_chars": config.CHUNK_MAX_CHARS,
            "chunk_overlap_chars": config.CHUNK_OVERLAP_CHARS,
            "default_collection": config.DEFAULT_COLLECTION,
        }
    )


@app.get("/api/collections")
def list_collections():
    db_path = Path(config.DB_PATH)
    collections = []
    if db_path.exists():
        with db.connect(db_path) as conn:
            collections = [dict(row) for row in db.list_collections(conn)]
    return jsonify({"collections": collections})


@app.delete("/api/collections/<collection>")
def delete_collection(collection):
    safe_collection = _safe_component(collection)
    if safe_collection == config.DEFAULT_COLLECTION:
        return jsonify({"error": "delete files individually from the default collection"}), 400

    target_dir = _collection_dir(safe_collection)
    if not target_dir.exists():
        return jsonify({"error": "collection not found"}), 404
    shutil.rmtree(target_dir)

    try:
        _reindex()
    except SystemExit:
        db.init_db(Path(config.DB_PATH), reset=True)
    return jsonify({"ok": True})


@app.get("/api/documents")
def list_documents():
    db_path = Path(config.DB_PATH)
    documents = []
    if db_path.exists():
        with db.connect(db_path) as conn:
            documents = [dict(row) for row in db.list_documents_with_counts(conn)]
    return jsonify({"documents": documents})


@app.get("/api/documents/<collection>/<path:filename>/chunks")
def document_chunks(collection, filename):
    safe_collection = _safe_component(collection)
    safe_name = _safe_component(filename)
    db_path = Path(config.DB_PATH)
    if not db_path.exists():
        return jsonify({"chunks": []})
    with db.connect(db_path) as conn:
        rows = db.fetch_chunks_for_document(conn, safe_collection, safe_name)
    return jsonify(
        {"chunks": [{"index": r["chunk_index"], "text": r["text"]} for r in rows]}
    )


@app.post("/api/documents")
def upload_document():
    files = request.files.getlist("files") or request.files.getlist("file")
    if not files:
        return jsonify({"error": "no file provided"}), 400

    collection = _safe_component(request.form.get("collection", "")) or config.DEFAULT_COLLECTION
    target_dir = _collection_dir(collection)
    target_dir.mkdir(parents=True, exist_ok=True)

    saved, skipped = [], []
    for file in files:
        filename = _safe_component(file.filename or "")
        if not filename or Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
            skipped.append(file.filename or "?")
            continue
        file.save(target_dir / filename)
        saved.append(filename)

    if saved:
        try:
            _reindex()
        except SystemExit as exc:
            return jsonify({"error": str(exc)}), 500
    return jsonify({"ok": True, "saved": saved, "skipped": skipped, "collection": collection})


@app.delete("/api/documents/<collection>/<path:filename>")
def delete_document(collection, filename):
    safe_collection = _safe_component(collection)
    safe_name = _safe_component(filename)
    target_dir = _collection_dir(safe_collection)
    target = target_dir / safe_name
    if not target.exists():
        return jsonify({"error": "document not found"}), 404
    target.unlink()

    if target_dir != config.DOCS_DIR and not any(target_dir.iterdir()):
        target_dir.rmdir()

    try:
        _reindex()
    except SystemExit:
        # last document was removed - clear the (now stale) database instead
        db.init_db(Path(config.DB_PATH), reset=True)
    return jsonify({"ok": True})


@app.post("/api/reindex")
def reindex():
    try:
        _reindex()
    except SystemExit as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True})


@app.post("/api/ask")
def ask():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400

    try:
        top_k = int(payload.get("top_k", config.TOP_K))
    except (TypeError, ValueError):
        top_k = config.TOP_K
    top_k = max(1, min(top_k, 10))
    collection = (payload.get("collection") or "").strip() or None

    embedder, llm = _backends()
    started = time.perf_counter()
    try:
        result = answer_question(
            question, k=top_k, embedder=embedder, llm=llm, collection=collection
        )
    except EmbeddingBackendMismatch as exc:
        return jsonify({"error": str(exc)}), 409
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000)

    return jsonify(result)


def _run_case(case: dict, embedder, llm) -> dict:
    """Raises EmbeddingBackendMismatch - callers decide how to report it."""
    result = answer_question(case["question"], embedder=embedder, llm=llm)
    return testsuite.update_result(case["id"], result["answer"], result["sources"])


@app.get("/api/tests")
def list_tests():
    return jsonify({"tests": testsuite.list_cases()})


@app.post("/api/tests")
def add_test():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400
    expected_note = (payload.get("expected_note") or "").strip()
    return jsonify(testsuite.add_case(question, expected_note))


@app.delete("/api/tests/<case_id>")
def delete_test(case_id):
    testsuite.delete_case(case_id)
    return jsonify({"ok": True})


@app.post("/api/tests/<case_id>/run")
def run_test(case_id):
    case = testsuite.get_case(case_id)
    if not case:
        return jsonify({"error": "test case not found"}), 404
    embedder, llm = _backends()
    try:
        updated = _run_case(case, embedder, llm)
    except EmbeddingBackendMismatch as exc:
        return jsonify({"error": str(exc)}), 409
    return jsonify(updated)


@app.post("/api/tests/run-all")
def run_all_tests():
    embedder, llm = _backends()
    for case in testsuite.list_cases():
        try:
            _run_case(case, embedder, llm)
        except EmbeddingBackendMismatch as exc:
            return jsonify({"error": str(exc)}), 409
    return jsonify({"tests": testsuite.list_cases()})


@app.post("/api/tests/<case_id>/verdict")
def set_test_verdict(case_id):
    payload = request.get_json(silent=True) or {}
    verdict = payload.get("verdict")
    if verdict not in ("pass", "fail", None):
        return jsonify({"error": "verdict must be 'pass', 'fail', or null"}), 400
    updated = testsuite.set_verdict(case_id, verdict)
    if not updated:
        return jsonify({"error": "test case not found"}), 404
    return jsonify(updated)


def main() -> None:
    _backends()  # warm up / print which backends are active before serving
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
