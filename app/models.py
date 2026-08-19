from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    """A single crawled page, before chunking."""
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """A single chunk of a document, ready for embedding/storage."""
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    """A chunk returned from the vector store, with its scores attached."""
    content: str
    metadata: dict[str, Any]
    semantic_score: float
    lexical_score: float
    hybrid_score: float