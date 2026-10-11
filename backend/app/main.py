"""
FinRAG — FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import analytics, chat, companies, documents, evaluation, health
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.database import create_tables

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("finrag_starting", version="1.0.0")

    # Create database tables if they don't exist
    try:
        create_tables()
        logger.info("database_tables_ready")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
        # Don't crash — the app can still serve requests if DB is temporarily unavailable

    yield  # Application runs

    logger.info("finrag_shutdown")


app = FastAPI(
    title="FinRAG API",
    description=(
        "Financial Filing Intelligence Engine — "
        "RAG-powered analysis of annual reports, quarterly filings, and earnings transcripts."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
allowed_origins = [settings.frontend_url, "http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler (no stack traces in production) ──────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    if settings.debug:
        import traceback
        detail = traceback.format_exc()
    else:
        detail = "An internal error occurred. Please try again."
    return JSONResponse(status_code=500, content={"detail": detail})


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(companies.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(analytics.router)
app.include_router(evaluation.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
    )
