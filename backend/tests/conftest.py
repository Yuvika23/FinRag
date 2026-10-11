"""FinRAG test configuration and fixtures."""
import os
import sys
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Use test environment
os.environ.setdefault("POSTGRES_DB", "finrag_test")
os.environ.setdefault("LLM_PROVIDER", "none")
os.environ.setdefault("FAISS_INDEX_PATH", "./test_faiss_index")
os.environ.setdefault("UPLOAD_DIR", "./test_uploads")
