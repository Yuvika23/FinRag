"""
FinRAG — Embedding service using Sentence Transformers.
Singleton pattern ensures the model is loaded once.
"""

from __future__ import annotations

from typing import Optional
import numpy as np

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class EmbeddingService:
    """
    Generates text embeddings using a local Sentence Transformers model.
    The model is loaded lazily on first use and cached for the application lifetime.
    """

    _instance: Optional["EmbeddingService"] = None
    _model = None

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_model(self) -> None:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("loading_embedding_model", model=settings.embedding_model)
                self._model = SentenceTransformer(settings.embedding_model)
                logger.info("embedding_model_loaded", model=settings.embedding_model)
            except Exception as e:
                logger.error("embedding_model_load_failed", error=str(e))
                raise RuntimeError(f"Failed to load embedding model: {e}") from e

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        Returns a 2D numpy array of shape (n_texts, embedding_dim).
        """
        self._ensure_model()

        if not texts:
            return np.empty((0, settings.embedding_dimension), dtype=np.float32)

        # Truncate overly long texts to avoid memory issues
        truncated = [t[:4096] if len(t) > 4096 else t for t in texts]

        logger.info("generating_embeddings", count=len(texts), batch_size=batch_size)

        embeddings = self._model.encode(
            truncated,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,  # L2-normalize for cosine similarity via inner product
            convert_to_numpy=True,
        )

        return embeddings.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a single query string.
        Returns a 1D numpy array of shape (embedding_dim,).
        """
        result = self.embed_texts([query])
        return result[0]

    @property
    def dimension(self) -> int:
        return settings.embedding_dimension

    def is_ready(self) -> bool:
        """Check whether the model is loaded."""
        return self._model is not None


# Module-level singleton
embedding_service = EmbeddingService()
