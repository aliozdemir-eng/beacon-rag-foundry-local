"""Vector search over the SQLite-backed knowledge base.

Brute-force cosine similarity is deliberately simple: at the scale of a
student project's document set (tens to a few hundred chunks) this is fast
enough, and it avoids pulling in a dedicated vector database.
"""

import json
from pathlib import Path

import numpy as np

from . import config, db
from .embeddings import EmbeddingBackend, get_embedding_backend


class EmbeddingBackendMismatch(RuntimeError):
    pass


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def get_top_chunks(
    question: str,
    db_path: Path = config.DB_PATH,
    k: int = config.TOP_K,
    embedder: EmbeddingBackend | None = None,
    collection: str | None = None,
) -> list[dict]:
    embedder = embedder or get_embedding_backend()

    with db.connect(db_path) as conn:
        stored_backend = db.get_meta(conn, "embedding_backend")
        if stored_backend and stored_backend != embedder.name:
            raise EmbeddingBackendMismatch(
                f"The knowledge base was built with '{stored_backend}' embeddings but the "
                f"active backend is '{embedder.name}'. Re-run ingestion: "
                "python -m src.ingest"
            )

        rows = db.fetch_all_chunks(conn, collection=collection)
        if not rows:
            return []

        query_vector = np.array(embedder.embed([question])[0])
        scored = []
        for row in rows:
            chunk_vector = np.array(json.loads(row["embedding"]))
            score = _cosine_similarity(query_vector, chunk_vector)
            scored.append((score, row))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        top = scored[:k]
        return [
            {"text": row["text"], "source": row["source"], "score": round(score, 4)}
            for score, row in top
        ]
