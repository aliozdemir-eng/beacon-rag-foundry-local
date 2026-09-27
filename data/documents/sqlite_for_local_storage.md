# Why SQLite for a Local Knowledge Base

SQLite is a self-contained, serverless SQL database engine: an entire
database lives in a single file on disk, and any process that links the
SQLite library can read and write it directly, with no separate database
server to install, configure, or keep running. That makes it a good fit for a
small local RAG project, where the whole point is to avoid extra
infrastructure.

For this kind of project, a SQLite database typically holds two related
tables: one row per source document, and one row per chunk of that document,
with each chunk storing its own text and its embedding vector. Because
SQLite has no native vector type, the embedding is usually serialized as JSON
or as a raw binary blob and deserialized back into a numeric array at query
time.

## Brute-force search is fine at small scale

At the scale of a student project - tens to a few hundred chunks - there is
no need for a dedicated vector database or an approximate nearest-neighbor
index. A query embedding can simply be compared against every stored chunk
embedding using cosine similarity, and the top few results kept. This is a
few milliseconds of work even for a few thousand vectors. If a knowledge base
grows into the tens of thousands of chunks, that's the point where a
purpose-built vector index becomes worth the added complexity - not before.

## Practical tips

Keep a small "meta" table alongside the documents and chunks tables to record
which embedding model produced the stored vectors. If the embedding backend
ever changes, old and new vectors are not comparable, and mixing them
silently produces nonsense similarity scores instead of an obvious error.
