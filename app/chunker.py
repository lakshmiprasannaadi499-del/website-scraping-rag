from __future__ import annotations

import hashlib
import re

from app.config import CHUNK_SIZE, CHUNK_OVERLAP, MIN_CHUNK_CHARS, MAX_CHUNK_CHARS
from app.models import Document, Chunk

# Split on paragraph boundaries first so chunks don't cut mid-sentence
# whenever possible; sentences are the fallback splitting unit.
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _split_into_units(text: str) -> list[str]:
    units: list[str] = []
    for paragraph in _PARAGRAPH_SPLIT.split(text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= MAX_CHUNK_CHARS:
            units.append(paragraph)
        else:
            # Paragraph too long on its own - split by sentence.
            for sentence in _SENTENCE_SPLIT.split(paragraph):
                sentence = sentence.strip()
                if sentence:
                    units.append(sentence)
    return units


def _pack_units(units: list[str]) -> list[str]:
    """Greedily pack units into chunks close to CHUNK_SIZE, with overlap."""

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for unit in units:
        unit_len = len(unit)

        if current and current_len + unit_len + 1 > CHUNK_SIZE:
            chunk_text = "\n\n".join(current)
            if len(chunk_text) >= MIN_CHUNK_CHARS:
                chunks.append(chunk_text)

            # Build overlap: keep trailing units whose combined length is
            # close to CHUNK_OVERLAP, to preserve context across chunks.
            overlap_units: list[str] = []
            overlap_len = 0
            for prev_unit in reversed(current):
                if overlap_len + len(prev_unit) > CHUNK_OVERLAP:
                    break
                overlap_units.insert(0, prev_unit)
                overlap_len += len(prev_unit)

            current = overlap_units
            current_len = overlap_len

        current.append(unit)
        current_len += unit_len + 1

    if current:
        chunk_text = "\n\n".join(current)
        if len(chunk_text) >= MIN_CHUNK_CHARS:
            chunks.append(chunk_text)

    # If a single unit was itself larger than MAX_CHUNK_CHARS (rare, e.g. a
    # huge code block), hard-wrap it as a last resort so nothing is dropped.
    final_chunks: list[str] = []
    for chunk_text in chunks:
        if len(chunk_text) <= MAX_CHUNK_CHARS:
            final_chunks.append(chunk_text)
        else:
            for start in range(0, len(chunk_text), MAX_CHUNK_CHARS - CHUNK_OVERLAP):
                piece = chunk_text[start:start + MAX_CHUNK_CHARS]
                if len(piece) >= MIN_CHUNK_CHARS:
                    final_chunks.append(piece)

    return final_chunks


def chunk_document(document: Document) -> list[Chunk]:
    units = _split_into_units(document.content)
    if not units:
        return []

    texts = _pack_units(units)
    url = document.metadata.get("url", "")

    chunks: list[Chunk] = []
    for index, text in enumerate(texts):
        chunk_id = hashlib.sha256(f"{url}::{index}::{text[:80]}".encode("utf-8")).hexdigest()[:24]

        metadata = dict(document.metadata)
        metadata["chunk_id"] = chunk_id
        metadata["chunk_index"] = index
        metadata["chunk_count"] = len(texts)

        chunks.append(Chunk(content=text, metadata=metadata))

    return chunks


def chunk_documents(documents: list[Document]) -> list[Chunk]:
    all_chunks: list[Chunk] = []
    for document in documents:
        all_chunks.extend(chunk_document(document))
    return all_chunks
