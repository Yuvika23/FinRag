"""
FinRAG — Evaluation service.
Computes Recall@K, Precision@K, MRR, citation accuracy, and faithfulness.
Uses a labeled evaluation dataset — no fabricated scores.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.evaluation import EvaluationResult, EvaluationRun
from app.services.generation.rag_orchestrator import answer_question

logger = get_logger(__name__)

BUILTIN_DATASET_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / "evaluation" / "eval_dataset.json"


def compute_recall_at_k(relevant_ids: list[str], retrieved_ids: list[str], k: int) -> float:
    """Recall@K = |relevant ∩ retrieved[:k]| / |relevant|"""
    if not relevant_ids:
        return 0.0
    top_k = set(retrieved_ids[:k])
    relevant_set = set(relevant_ids)
    return len(relevant_set & top_k) / len(relevant_set)


def compute_precision_at_k(relevant_ids: list[str], retrieved_ids: list[str], k: int) -> float:
    """Precision@K = |relevant ∩ retrieved[:k]| / k"""
    if k == 0:
        return 0.0
    top_k = set(retrieved_ids[:k])
    relevant_set = set(relevant_ids)
    return len(relevant_set & top_k) / k


def compute_mrr(relevant_ids: list[str], retrieved_ids: list[str]) -> float:
    """Mean Reciprocal Rank = 1 / rank of first relevant result."""
    relevant_set = set(relevant_ids)
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in relevant_set:
            return 1.0 / rank
    return 0.0


def compute_citation_accuracy(
    expected_sources: list[dict],
    citations: list[dict],
) -> float:
    """
    Citation accuracy: fraction of expected sources that appear in generated citations.
    Matches on document name (case-insensitive) and optionally page number.
    """
    if not expected_sources:
        return 1.0  # No expected sources = can't penalize

    matched = 0
    cited_docs = {c.get("document_name", "").lower() for c in citations}

    for expected in expected_sources:
        expected_doc = expected.get("document_name", "").lower()
        if any(expected_doc in cited or cited in expected_doc for cited in cited_docs):
            matched += 1

    return matched / len(expected_sources)


def run_evaluation(
    db: Session,
    run_name: str = "Evaluation Run",
    dataset_path: Optional[str] = None,
    use_builtin: bool = True,
    top_k: int = 5,
) -> EvaluationRun:
    """
    Run evaluation against a labeled dataset.
    Returns the completed EvaluationRun with aggregated metrics.
    """
    # Load dataset
    dataset = _load_dataset(dataset_path, use_builtin)

    if not dataset:
        raise ValueError("Evaluation dataset is empty or could not be loaded.")

    # Create run record
    run = EvaluationRun(
        id=str(uuid.uuid4()),
        name=run_name,
        dataset_path=dataset_path or str(BUILTIN_DATASET_PATH),
        total_questions=len(dataset),
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()

    # Run evaluation for each question
    total_recall, total_precision, total_mrr = 0.0, 0.0, 0.0
    total_citation, total_faithfulness, total_latency = 0.0, 0.0, 0.0
    failed = 0
    completed = 0

    for item in dataset:
        question = item.get("question", "")
        expected_answer = item.get("expected_answer", "")
        expected_sources = item.get("expected_sources", [])
        relevant_chunk_ids = item.get("relevant_chunk_ids", [])

        result_id = str(uuid.uuid4())
        result = EvaluationResult(
            id=result_id,
            run_id=run.id,
            question=question,
            expected_answer=expected_answer,
            expected_sources=expected_sources,
        )

        try:
            t0 = time.time()
            response = answer_question(
                question=question,
                db=db,
                top_k=top_k,
            )
            latency_ms = (time.time() - t0) * 1000

            retrieved_ids = [p["chunk_id"] for p in response.retrieved_passages]
            citations = [
                {"document_name": c.document_name, "page_number": c.page_number}
                for c in response.citations
            ]

            recall = compute_recall_at_k(relevant_chunk_ids, retrieved_ids, top_k)
            precision = compute_precision_at_k(relevant_chunk_ids, retrieved_ids, top_k)
            mrr = compute_mrr(relevant_chunk_ids, retrieved_ids)
            citation_acc = compute_citation_accuracy(expected_sources, citations)

            # Simple faithfulness: check if key phrases from expected answer appear in generated
            faithfulness = _estimate_faithfulness(expected_answer, response.answer)

            result.generated_answer = response.answer
            result.retrieved_sources = citations
            result.recall_at_k = recall
            result.precision_at_k = precision
            result.mrr = mrr
            result.citation_accuracy = citation_acc
            result.faithfulness = faithfulness
            result.latency_ms = latency_ms

            total_recall += recall
            total_precision += precision
            total_mrr += mrr
            total_citation += citation_acc
            total_faithfulness += faithfulness
            total_latency += latency_ms
            completed += 1

        except Exception as e:
            logger.error("eval_question_failed", question=question[:80], error=str(e))
            result.error = str(e)
            failed += 1

        db.add(result)

    db.flush()

    # Aggregate metrics
    n = completed or 1
    run.completed_questions = completed
    run.failed_queries = failed
    run.avg_recall_at_k = total_recall / n
    run.avg_precision_at_k = total_precision / n
    run.avg_mrr = total_mrr / n
    run.avg_citation_accuracy = total_citation / n
    run.avg_faithfulness = total_faithfulness / n
    run.avg_latency_ms = total_latency / n
    run.completed_at = datetime.now(timezone.utc)

    db.commit()
    logger.info("evaluation_complete", run_id=run.id, completed=completed, failed=failed)

    return run


def _load_dataset(dataset_path: Optional[str], use_builtin: bool) -> list[dict]:
    """Load evaluation dataset from JSON file."""
    if dataset_path:
        path = Path(dataset_path)
    elif use_builtin and BUILTIN_DATASET_PATH.exists():
        path = BUILTIN_DATASET_PATH
    else:
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else data.get("questions", [])
    except Exception as e:
        logger.error("dataset_load_failed", path=str(path), error=str(e))
        return []


def _estimate_faithfulness(expected: str, generated: str) -> float:
    """
    Simple faithfulness estimate: fraction of key words from expected that appear in generated.
    Not a replacement for proper NLI-based faithfulness, but avoids LLM-as-judge costs.
    """
    if not expected or not generated:
        return 0.0

    # Extract meaningful words (>4 chars) as key terms
    import re
    key_words = set(re.findall(r"\b\w{4,}\b", expected.lower()))
    if not key_words:
        return 0.5

    gen_lower = generated.lower()
    found = sum(1 for w in key_words if w in gen_lower)
    return min(found / len(key_words), 1.0)
