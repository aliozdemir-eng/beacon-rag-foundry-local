"""Central configuration for the Beacon local RAG assistant."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DOCS_DIR = Path(os.environ.get("BEACON_DOCS_DIR", BASE_DIR / "data" / "documents"))
DB_PATH = Path(os.environ.get("BEACON_DB_PATH", BASE_DIR / "data" / "knowledge.db"))

# Files placed directly in DOCS_DIR belong to this collection. A subfolder of
# DOCS_DIR named e.g. "Cars" becomes its own collection, letting a question
# be scoped to just that subset of the knowledge base.
DEFAULT_COLLECTION = "General"

# Foundry Local model aliases (see: foundry model list).
# Override with env vars if your local catalog uses different aliases.
LLM_MODEL_ALIAS = os.environ.get("BEACON_LLM_ALIAS", "phi-3.5-mini")
EMBEDDING_MODEL_ALIAS = os.environ.get("BEACON_EMBEDDING_ALIAS", "qwen3-embedding-0.6b")

CHUNK_MAX_CHARS = int(os.environ.get("BEACON_CHUNK_CHARS", "800"))
CHUNK_OVERLAP_CHARS = int(os.environ.get("BEACON_CHUNK_OVERLAP", "120"))
TOP_K = int(os.environ.get("BEACON_TOP_K", "3"))

# Fallback embedding dimensionality (used only when Foundry Local is unavailable).
FALLBACK_EMBEDDING_DIM = 512

SYSTEM_PROMPT = (
    "You are Beacon, an offline assistant that answers questions using ONLY the "
    "provided context passages. Rules:\n"
    "1. If the answer is not contained in the context, say you don't know - never guess.\n"
    "2. Keep answers concise and factual.\n"
    "3. After your answer, list the source document names you relied on.\n"
)
