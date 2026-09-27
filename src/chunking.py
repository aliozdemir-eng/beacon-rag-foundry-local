"""Simple paragraph-aware text chunking for the ingestion pipeline."""


def split_into_chunks(text: str, max_chars: int = 800, overlap: int = 120) -> list[str]:
    """Split text into overlapping chunks, preferring paragraph boundaries.

    Small documents fit in a single chunk; longer ones are packed paragraph by
    paragraph up to max_chars, carrying a bit of overlap into the next chunk so
    context isn't lost at the boundary.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n\n{para}" if tail else para
    if current:
        chunks.append(current)
    return chunks
