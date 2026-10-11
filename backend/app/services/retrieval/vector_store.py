"""
FinRAG — FAISS vector store for document chunk embeddings.
Persists index and metadata mappings to disk so they survive restarts.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Optional

import numpy as np

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class FAISSVectorStore:
    """
    Thread-safe FAISS vector index wrapper.

    - Uses IndexFlatIP (inner product) with L2-normalized vectors → cosine similarity.
    - Maps FAISS integer IDs to chunk IDs stored in a JSON sidecar file.
    - The index is loaded from disk at startup if it exists.
    """

    def __init__(self, index_path: Optional[str] = None) -> None:
        self._lock = threading.Lock()
        self._index = None
        self._id_map: dict[int, str] = {}  # faiss_id → chunk_id (UUID string)
        self._next_id: int = 0

        index_dir = Path(index_path or settings.faiss_index_path)
        index_dir.mkdir(parents=True, exist_ok=True)

        self._index_file = index_dir / "index.faiss"
        self._meta_file = index_dir / "metadata.json"

        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load index and metadata from disk if they exist."""
        try:
            import faiss
        except ImportError:
            raise RuntimeError("faiss-cpu is not installed. Run: pip install faiss-cpu")

        if self._index_file.exists() and self._meta_file.exists():
            try:
                self._index = faiss.read_index(str(self._index_file))
                with open(self._meta_file, "r") as f:
                    data = json.load(f)
                self._id_map = {int(k): v for k, v in data["id_map"].items()}
                self._next_id = data.get("next_id", max(self._id_map.keys()) + 1 if self._id_map else 0)
                logger.info(
                    "faiss_index_loaded",
                    index_size=self._index.ntotal,
                    path=str(self._index_file),
                )
            except Exception as e:
                logger.warning("faiss_load_failed", error=str(e), msg="Starting fresh index.")
                self._create_fresh_index()
        else:
            self._create_fresh_index()

    def _create_fresh_index(self) -> None:
        import faiss
        self._index = faiss.IndexFlatIP(settings.embedding_dimension)
        self._id_map = {}
        self._next_id = 0
        logger.info("faiss_fresh_index_created", dimension=settings.embedding_dimension)

    def _save(self) -> None:
        """Persist index and metadata to disk."""
        import faiss
        faiss.write_index(self._index, str(self._index_file))
        with open(self._meta_file, "w") as f:
            json.dump({"id_map": {str(k): v for k, v in self._id_map.items()}, "next_id": self._next_id}, f)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def add_embeddings(
        self,
        embeddings: np.ndarray,
        chunk_ids: list[str],
    ) -> list[int]:
        """
        Add a batch of embeddings and return their assigned FAISS integer IDs.
        chunk_ids must correspond 1-to-1 with embedding rows.
        """
        if embeddings.shape[0] != len(chunk_ids):
            raise ValueError("embeddings and chunk_ids must have the same length")

        with self._lock:
            import faiss

            # Assign sequential integer IDs
            start_id = self._next_id
            faiss_ids = list(range(start_id, start_id + len(chunk_ids)))

            # Update id_map
            for faiss_id, chunk_id in zip(faiss_ids, chunk_ids):
                self._id_map[faiss_id] = chunk_id

            self._next_id += len(chunk_ids)

            # FAISS IndexFlatIP does not support custom IDs, so we rely on positional ordering
            self._index.add(embeddings.astype(np.float32))
            self._save()

        logger.info("faiss_embeddings_added", count=len(chunk_ids), total=self._index.ntotal)
        return faiss_ids

    def remove_by_chunk_ids(self, chunk_ids: set[str]) -> int:
        """
        Remove entries by chunk_id. FAISS does not support deletion directly on IndexFlatIP,
        so we rebuild the index minus the removed IDs.
        Returns the count of removed embeddings.
        """
        import faiss

        with self._lock:
            if not self._id_map:
                return 0

            # IDs to keep
            keep_faiss_ids = [fid for fid, cid in self._id_map.items() if cid not in chunk_ids]
            removed = len(self._id_map) - len(keep_faiss_ids)

            if removed == 0:
                return 0

            if not keep_faiss_ids:
                # Rebuild empty
                self._create_fresh_index()
                self._save()
                return removed

            # Reconstruct vectors for kept IDs
            all_vectors = self._index.reconstruct_n(0, self._index.ntotal)
            kept_vectors = np.array([all_vectors[fid] for fid in keep_faiss_ids], dtype=np.float32)

            # Preserve old id map before creating fresh index
            old_id_map = dict(self._id_map)

            # Rebuild
            self._create_fresh_index()
            self._index.add(kept_vectors)

            # Reassign sequential IDs
            new_id_map = {}
            for new_id, old_id in enumerate(keep_faiss_ids):
                new_id_map[new_id] = old_id_map[old_id]
            self._id_map = new_id_map
            self._next_id = len(new_id_map)
            self._save()

        logger.info("faiss_embeddings_removed", count=removed, remaining=self._index.ntotal)
        return removed

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        filter_chunk_ids: Optional[set[str]] = None,
    ) -> list[tuple[str, float]]:
        """
        Search for the top_k most similar chunks.
        Returns list of (chunk_id, similarity_score) sorted by descending similarity.

        filter_chunk_ids: if provided, only results whose chunk_id is in this set are returned.
        """
        with self._lock:
            if self._index is None or self._index.ntotal == 0:
                return []

            query = query_embedding.reshape(1, -1).astype(np.float32)
            search_k = min(top_k * 3 if filter_chunk_ids else top_k, self._index.ntotal)

            distances, indices = self._index.search(query, search_k)

            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1:
                    continue
                chunk_id = self._id_map.get(idx)
                if chunk_id is None:
                    continue
                if filter_chunk_ids and chunk_id not in filter_chunk_ids:
                    continue
                results.append((chunk_id, float(dist)))
                if len(results) >= top_k:
                    break

            return results

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def total_vectors(self) -> int:
        return self._index.ntotal if self._index else 0

    def get_chunk_id(self, faiss_id: int) -> Optional[str]:
        return self._id_map.get(faiss_id)

    def is_empty(self) -> bool:
        return self.total_vectors == 0


# Module-level singleton
vector_store = FAISSVectorStore()


def get_vector_store() -> FAISSVectorStore:
    return vector_store
