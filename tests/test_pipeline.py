"""Smoke test: ingest the sample documents and ask a question end-to-end.

Run with:  python -m pytest tests/  (or just: python tests/test_pipeline.py)
Uses a throwaway database so it never touches data/knowledge.db.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, ingest
from src.qa import answer_question


def test_end_to_end_pipeline():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        ingest.run(config.DOCS_DIR, db_path, reset=True)

        result = answer_question("What is RAG?", db_path=db_path, k=2)
        assert result["answer"]
        assert result["sources"], "expected at least one cited source"
        assert any("rag" in s.lower() for s in result["sources"])


if __name__ == "__main__":
    test_end_to_end_pipeline()
    print("OK")
