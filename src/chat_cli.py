"""Interactive console chat over the local knowledge base.

Usage:
    python -m src.chat_cli                 # interactive loop
    python -m src.chat_cli --query "..."   # single question, then exit
"""

import argparse
from pathlib import Path

from . import config
from .embeddings import get_embedding_backend
from .llm import get_llm_backend
from .qa import answer_question
from .retrieval import EmbeddingBackendMismatch


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask questions about your local documents.")
    parser.add_argument("--query", type=str, default=None, help="Ask a single question and exit.")
    parser.add_argument("--db", type=Path, default=config.DB_PATH)
    parser.add_argument("--top-k", type=int, default=config.TOP_K)
    args = parser.parse_args()

    embedder = get_embedding_backend()
    llm = get_llm_backend()
    print(f"Ready. embeddings={embedder.name} llm={llm.name}\n")

    def ask(question: str) -> None:
        try:
            result = answer_question(
                question, db_path=args.db, k=args.top_k, embedder=embedder, llm=llm
            )
        except EmbeddingBackendMismatch as exc:
            print(f"! {exc}")
            return
        print(f"\n{result['answer']}\n")
        if result["sources"]:
            print(f"Sources: {', '.join(result['sources'])}\n")

    if args.query:
        ask(args.query)
        return

    print("Type a question, or 'exit' to quit.")
    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            break
        ask(question)


if __name__ == "__main__":
    main()
