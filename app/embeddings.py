from __future__ import annotations

from app.config import EMBEDDING_MODEL, EMBEDDING_NORMALIZE, EMBEDDING_BATCH_SIZE, EMBEDDING_DEVICE


class Embedder:
    """Thin wrapper around a sentence-transformers model."""

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        device = None if EMBEDDING_DEVICE == "auto" else EMBEDDING_DEVICE

        print(f"\nLoading embedding model: {EMBEDDING_MODEL} (device={EMBEDDING_DEVICE})")
        self.model = SentenceTransformer(EMBEDDING_MODEL, device=device)
        print("Embedding model loaded.")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            batch_size=EMBEDDING_BATCH_SIZE,
            normalize_embeddings=EMBEDDING_NORMALIZE,
            show_progress_bar=len(texts) > 20,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self.model.encode(
            [text],
            normalize_embeddings=EMBEDDING_NORMALIZE,
            convert_to_numpy=True,
        )
        return embedding[0].tolist()