"""
FinRAG — Tests for the FAISS vector store.
"""

import numpy as np
import pytest
import tempfile
import shutil
from app.services.retrieval.vector_store import FAISSVectorStore


@pytest.fixture
def temp_index(tmp_path):
    """Create a temporary FAISS index for each test."""
    store = FAISSVectorStore(index_path=str(tmp_path / "test_faiss"))
    yield store
    # Cleanup is automatic via tmp_path fixture


class TestFAISSVectorStore:
    def _make_embeddings(self, n: int, dim: int = 384) -> np.ndarray:
        """Generate normalized random embeddings."""
        vecs = np.random.randn(n, dim).astype(np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return vecs / norms

    def test_initially_empty(self, temp_index):
        assert temp_index.is_empty()
        assert temp_index.total_vectors == 0

    def test_add_embeddings(self, temp_index):
        embeddings = self._make_embeddings(5)
        chunk_ids = [f"chunk_{i}" for i in range(5)]
        faiss_ids = temp_index.add_embeddings(embeddings, chunk_ids)
        assert len(faiss_ids) == 5
        assert temp_index.total_vectors == 5

    def test_search_returns_results(self, temp_index):
        embeddings = self._make_embeddings(10)
        chunk_ids = [f"chunk_{i}" for i in range(10)]
        temp_index.add_embeddings(embeddings, chunk_ids)

        query = embeddings[0]  # Search for exact match
        results = temp_index.search(query, top_k=3)

        assert len(results) > 0
        assert len(results) <= 3
        # First result should be the query itself (highest similarity)
        first_chunk_id, first_score = results[0]
        assert first_score > 0.9  # Near-perfect match

    def test_search_on_empty_store(self, temp_index):
        query = self._make_embeddings(1)[0]
        results = temp_index.search(query, top_k=5)
        assert results == []

    def test_remove_by_chunk_ids(self, temp_index):
        embeddings = self._make_embeddings(5)
        chunk_ids = [f"chunk_{i}" for i in range(5)]
        temp_index.add_embeddings(embeddings, chunk_ids)
        assert temp_index.total_vectors == 5

        removed = temp_index.remove_by_chunk_ids({"chunk_0", "chunk_1"})
        assert removed == 2
        assert temp_index.total_vectors == 3

    def test_remove_nonexistent_ids(self, temp_index):
        embeddings = self._make_embeddings(3)
        chunk_ids = ["a", "b", "c"]
        temp_index.add_embeddings(embeddings, chunk_ids)

        removed = temp_index.remove_by_chunk_ids({"nonexistent"})
        assert removed == 0
        assert temp_index.total_vectors == 3

    def test_persistence(self, tmp_path):
        """Test that the index is saved and can be reloaded."""
        index_path = str(tmp_path / "persist_test")
        store1 = FAISSVectorStore(index_path=index_path)

        embeddings = self._make_embeddings(5)
        chunk_ids = [f"chunk_{i}" for i in range(5)]
        store1.add_embeddings(embeddings, chunk_ids)
        assert store1.total_vectors == 5

        # Create new store instance pointing to same path
        store2 = FAISSVectorStore(index_path=index_path)
        assert store2.total_vectors == 5

    def test_filter_chunk_ids(self, temp_index):
        embeddings = self._make_embeddings(10)
        chunk_ids = [f"chunk_{i}" for i in range(10)]
        temp_index.add_embeddings(embeddings, chunk_ids)

        # Only search in first 3 chunks
        allowed = {"chunk_0", "chunk_1", "chunk_2"}
        results = temp_index.search(embeddings[0], top_k=10, filter_chunk_ids=allowed)

        for cid, _ in results:
            assert cid in allowed

    def test_mismatched_embeddings_raises(self, temp_index):
        embeddings = self._make_embeddings(3)
        chunk_ids = ["a", "b"]  # Wrong count
        with pytest.raises(ValueError):
            temp_index.add_embeddings(embeddings, chunk_ids)
