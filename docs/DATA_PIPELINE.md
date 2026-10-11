# FinRAG Ingestion and Data Pipeline

This document describes the end-to-end data processing workflow for corporate financial reports, filings, and earnings transcripts within FinRAG.

---

## 1. Pipeline Overview

```
Upload Document (.pdf / .txt)
   │
   ▼
[1] Validation & Integrity
   │   • MIME type check
   │   • Size limitation (<100MB)
   │   • SHA-256 fingerprint generation & duplicate check
   │
   ▼
[2] Document & Page Extraction
   │   • PyMuPDF (fitz) text parsing
   │   • Page boundary tracking (page 1, 2, 3...)
   │   • Header, footer & noise normalization
   │
   ▼
[3] Semantic Window Chunking
   │   • Target size: 512 words (approx. 650-700 tokens)
   │   • Overlap: 50 words (preserves sentence context across breaks)
   │   • Page mapping: chunk character offsets linked to physical page number
   │
   ▼
[4] Dense Embedding Generation
   │   • Sentence-Transformers (all-MiniLM-L6-v2)
   │   • 384-dimensional dense vectors
   │   • L2-normalization for cosine similarity
   │
   ▼
[5] Vector Indexing & Sidecar Serialization
   │   • Ingestion into FAISS IndexFlatIP
   │   • ID mapping stored in index_metadata.json
   │   • Checkpoint persisted to disk
   │
   ▼
[6] Relational Persistence & State Transition
       • Chunks inserted into document_chunks table with faiss_id
       • Status set to DocumentStatus.INDEXED
       • IngestionJob logged with execution time & chunk metrics
```

---

## 2. Ingestion Stages in Detail

### Stage 1: Validation and Deduplication
1. **File Fingerprinting**: A full SHA-256 hash is computed over the file's raw byte stream.
2. **Duplicate Check**: The database is queried for an existing `documents` record with the same `file_hash`. If found and already indexed, the pipeline rejects duplicate ingestion with an `HTTP 409 Conflict` (or returns the existing document ID), preventing vector index pollution.
3. **Storage**: The raw document is securely copied to the storage directory (`./uploads/`) with a unique UUID filename, preserving the user's `original_filename` in metadata.

### Stage 2: Page-Preserving Text Extraction
- **PDF Extraction**: Uses PyMuPDF (`fitz`), iterating sequentially through document pages (`doc[page_num]`).
- **Text Preservation**: Page text is extracted with exact page indices (1-indexed for standard financial convention).
- **Page Markers**: Newline boundaries and page delimiters are maintained so extracted chunks know their origin.
- **TXT Extraction**: Plain text documents (such as earnings call transcripts) are extracted, and artificial page boundaries (~500 words per logical page) are assigned when physical pages are absent.

### Stage 3: Sliding Window Chunking
- Financial reports frequently contain dense tables, disclosures, and continuous prose. Sentence boundary splits alone can truncate footnote disclosures.
- **Algorithm**:
  - Text is tokenized into word lists.
  - A sliding window of `CHUNK_SIZE` (default: 512 words) advances with step `CHUNK_SIZE - CHUNK_OVERLAP` (default overlap: 50 words).
  - For each chunk, the character offsets are mapped back to the primary source page.
- **Chunk Metadata**: Each chunk preserves:
  - `chunk_index`: Integer ordering within the document.
  - `page_number`: Physical page reference for auditability.
  - `token_count`: Estimated word/token length.
  - `company_name`, `ticker`, `fiscal_year`: Denormalized for fast filtering.

### Stage 4: Embeddings & Vector Indexing
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`.
- **Properties**: 384 dimensions, fast execution on CPU (typically <5ms per chunk).
- **Index Type**: `faiss.IndexFlatIP`.
- **Normalization**: Vectors are normalized to unit length ($||v||_2 = 1$). Under unit normalization, inner product ($v_1 \cdot v_2$) is mathematically equivalent to cosine similarity.
- **Metadata Alignment**: FAISS stores vectors indexed by integer IDs ($0, 1, 2, \dots, N-1$). A persistent JSON file (`index_metadata.json`) maps each integer ID to the database `DocumentChunk.id` (UUID) and document metadata.

### Stage 5: Deletion and Reindexing
- FAISS `IndexFlatIP` does not support arbitrary in-place deletion without rebuilding.
- When a document is deleted:
  1. The database cascades chunk deletion from `document_chunks`.
  2. The vector store loads all remaining valid chunk embeddings and constructs a fresh FAISS index.
  3. `index_metadata.json` is re-serialized.
