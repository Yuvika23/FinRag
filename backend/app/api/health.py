"""
FinRAG — Health and root API endpoints.
"""

from fastapi import APIRouter
from app.services.retrieval.vector_store import vector_store
from app.services.embeddings.embedding_service import embedding_service
from app.services.generation.llm_client import llm_client
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/api/health")
def health_check():
    """Return system health status."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "vector_store": {
            "total_vectors": vector_store.total_vectors,
            "is_empty": vector_store.is_empty(),
        },
        "embedding_model": {
            "model": settings.embedding_model,
            "is_loaded": embedding_service.is_ready(),
        },
        "llm": {
            "provider": settings.llm_provider,
            "is_available": llm_client.is_available(),
        },
    }
