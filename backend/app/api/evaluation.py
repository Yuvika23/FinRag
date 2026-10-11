"""
FinRAG — Evaluation API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.database import get_db
from app.models.evaluation import EvaluationResult, EvaluationRun
from app.schemas.schemas import EvaluationRunRead, RunEvaluationRequest
from app.services.evaluation.evaluation_service import run_evaluation

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])
logger = get_logger(__name__)


@router.post("/run", response_model=EvaluationRunRead)
def run_evaluation_endpoint(
    request: RunEvaluationRequest,
    db: Session = Depends(get_db),
):
    """
    Run evaluation against the labeled dataset.
    Returns aggregated metrics (Recall@K, Precision@K, MRR, etc.).
    Results are computed from actual retrieval — no fabricated scores.
    """
    try:
        evaluation_run = run_evaluation(
            db=db,
            run_name=request.name,
            dataset_path=request.dataset_path,
            use_builtin=request.use_builtin_dataset,
            top_k=request.top_k,
        )
        return evaluation_run
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("evaluation_run_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e}")


@router.get("/results", response_model=list[EvaluationRunRead])
def list_evaluation_runs(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """List all evaluation runs."""
    runs = (
        db.query(EvaluationRun)
        .order_by(EvaluationRun.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return runs


@router.get("/results/{run_id}")
def get_evaluation_run(run_id: str, db: Session = Depends(get_db)):
    """Get detailed results for a specific evaluation run."""
    run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")

    results = (
        db.query(EvaluationResult)
        .filter(EvaluationResult.run_id == run_id)
        .all()
    )

    return {
        "run": {
            "id": run.id,
            "name": run.name,
            "total_questions": run.total_questions,
            "completed_questions": run.completed_questions,
            "failed_queries": run.failed_queries,
            "avg_recall_at_k": run.avg_recall_at_k,
            "avg_precision_at_k": run.avg_precision_at_k,
            "avg_mrr": run.avg_mrr,
            "avg_citation_accuracy": run.avg_citation_accuracy,
            "avg_faithfulness": run.avg_faithfulness,
            "avg_latency_ms": run.avg_latency_ms,
            "created_at": run.created_at,
            "completed_at": run.completed_at,
        },
        "results": [
            {
                "id": r.id,
                "question": r.question,
                "generated_answer": r.generated_answer,
                "recall_at_k": r.recall_at_k,
                "precision_at_k": r.precision_at_k,
                "mrr": r.mrr,
                "citation_accuracy": r.citation_accuracy,
                "faithfulness": r.faithfulness,
                "latency_ms": r.latency_ms,
                "error": r.error,
            }
            for r in results
        ],
    }
