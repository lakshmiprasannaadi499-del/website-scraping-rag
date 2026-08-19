from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from app.config import CHROMA_COLLECTION, CHROMA_PATH
from app.models import Chunk


class VectorStore:

    def __init__(self) -> None:
        path = Path(CHROMA_PATH)
        path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(path))
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

        print(f"\nChromaDB path       : {path}")
        print(f"ChromaDB collection : {CHROMA_COLLECTION}")
        print(f"Existing vectors    : {self.count()}")

    def reset(self) -> None:
        try:
            self.client.delete_collection(name=CHROMA_COLLECTION)
        except Exception:
            pass

        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        print("ChromaDB collection reset.")

    def count(self) -> int:
        return self.collection.count()

    def add_documents(self, chunks: list[Chunk], embeddings: list[list[float]], batch_size: int = 100) -> int:
        if not chunks:
            return 0

        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must be identical.")

        total = 0
        for start in range(0, len(chunks), batch_size):
            batch_chunks = chunks[start:start + batch_size]
            batch_embeddings = embeddings[start:start + batch_size]

            ids = [chunk.metadata["chunk_id"] for chunk in batch_chunks]
            documents = [chunk.content for chunk in batch_chunks]
            metadatas = [chunk.metadata for chunk in batch_chunks]

            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=batch_embeddings,
            )
            total += len(batch_chunks)

        return total

    def query(self, embedding: list[float], n_results: int) -> dict[str, Any]:
        count = self.count()
        if count == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}

        n_results = min(max(1, n_results), count)

        return self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

    def get_by_url(self, url: str) -> dict[str, Any]:
        """
        Fetch every stored chunk for a single source URL, including
        embeddings. Used by the retriever's "whole-page pull": once it's
        confident which page is relevant, it pulls in ALL of that page's
        chunks so multi-section questions have every section available.
        """

        empty = {"documents": [], "metadatas": [], "embeddings": [], "ids": []}

        if not url or self.count() == 0:
            return empty

        try:
            return self.collection.get(
                where={"url": url},
                include=["documents", "metadatas", "embeddings"],
            )
        except Exception as exc:
            print(f"get_by_url failed for {url}: {exc}")
            return empty

    def all_urls(self) -> list[str]:
        """Return the distinct set of source URLs currently indexed."""
        if self.count() == 0:
            return []

        result = self.collection.get(include=["metadatas"])
        urls = {m.get("url") for m in result.get("metadatas", []) if m.get("url")}
        return sorted(urls)