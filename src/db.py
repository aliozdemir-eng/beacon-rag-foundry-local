"""SQLite storage for documents, chunks and their embeddings.

Documents belong to a "collection" - a free-text label (e.g. "Cars",
"Course Notes") that lets a question be scoped to a subset of the
knowledge base instead of always searching everything at once.
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    title TEXT NOT NULL,
    collection TEXT NOT NULL DEFAULT 'General'
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL REFERENCES documents(id),
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding TEXT NOT NULL
);
"""


@contextmanager
def connect(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path, reset: bool = False) -> None:
    if reset and db_path.exists():
        db_path.unlink()
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def get_meta(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def insert_document(conn: sqlite3.Connection, filename: str, title: str, collection: str) -> int:
    cur = conn.execute(
        "INSERT INTO documents(filename, title, collection) VALUES (?, ?, ?)",
        (filename, title, collection),
    )
    return cur.lastrowid


def insert_chunk(
    conn: sqlite3.Connection, doc_id: int, chunk_index: int, text: str, embedding: list[float]
) -> None:
    conn.execute(
        "INSERT INTO chunks(doc_id, chunk_index, text, embedding) VALUES (?, ?, ?, ?)",
        (doc_id, chunk_index, text, json.dumps(embedding)),
    )


def fetch_all_chunks(conn: sqlite3.Connection, collection: str | None = None) -> list[sqlite3.Row]:
    if collection and collection.lower() != "all":
        return conn.execute(
            """
            SELECT chunks.id, chunks.text, chunks.embedding, documents.title AS source
            FROM chunks JOIN documents ON chunks.doc_id = documents.id
            WHERE documents.collection = ?
            """,
            (collection,),
        ).fetchall()
    return conn.execute(
        """
        SELECT chunks.id, chunks.text, chunks.embedding, documents.title AS source
        FROM chunks JOIN documents ON chunks.doc_id = documents.id
        """
    ).fetchall()


def count_chunks(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) AS c FROM chunks").fetchone()["c"]


def count_documents(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) AS c FROM documents").fetchone()["c"]


def fetch_chunks_for_document(
    conn: sqlite3.Connection, collection: str, filename: str
) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT chunks.chunk_index, chunks.text
        FROM chunks JOIN documents ON chunks.doc_id = documents.id
        WHERE documents.collection = ? AND documents.filename = ?
        ORDER BY chunks.chunk_index
        """,
        (collection, filename),
    ).fetchall()


def list_documents_with_counts(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT documents.filename, documents.title, documents.collection,
               COUNT(chunks.id) AS chunk_count
        FROM documents LEFT JOIN chunks ON chunks.doc_id = documents.id
        GROUP BY documents.id
        ORDER BY documents.collection, documents.filename
        """
    ).fetchall()


def list_collections(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT documents.collection AS name,
               COUNT(DISTINCT documents.id) AS doc_count,
               COUNT(chunks.id) AS chunk_count
        FROM documents LEFT JOIN chunks ON chunks.doc_id = documents.id
        GROUP BY documents.collection
        ORDER BY documents.collection
        """
    ).fetchall()
