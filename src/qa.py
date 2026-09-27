"""Ties retrieval and generation together into a single answer_question() call."""

from pathlib import Path

from . import config
from .embeddings import get_embedding_backend
from .llm import get_llm_backend
from .retrieval import get_top_chunks


def answer_question(
    question: str,
    db_path: Path = config.DB_PATH,
    k: int = config.TOP_K,
    embedder=None,
    llm=None,
    collection: str | None = None,
) -> dict:
    embedder = embedder or get_embedding_backend()
    llm = llm or get_llm_backend()

    chunks = get_top_chunks(question, db_path=db_path, k=k, embedder=embedder, collection=collection)
    answer = llm.answer(question, chunks)
    return {
        "answer": answer,
        "sources": sorted({c["source"] for c in chunks}),
        "chunks": chunks,
    }
