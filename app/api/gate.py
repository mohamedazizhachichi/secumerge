"""Route du Security Gate."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.gate import GateReport
from app.services.gate import build_gate_report

router = APIRouter(tags=["gate"])


@router.get(
    "/gate",
    response_model=GateReport,
    summary="Verdict PASS/FAIL d'un commit",
)
def get_gate(
    project: str = Query(..., min_length=1, max_length=200),
    repository: str = Query(..., min_length=1, max_length=200),
    commit_sha: str = Query(..., min_length=1, max_length=64),
    db: Session = Depends(get_db),
) -> GateReport:
    """Répond PASS si chaque scanner attendu a un scan complet pour ce commit.

    Répond FAIL sinon (y compris si le dépôt ou le commit est inconnu :
    l'absence de preuve n'est jamais un PASS). Le HTTP reste 200 : c'est
    le champ `status` qui porte le verdict.
    """
    return build_gate_report(
        db,
        project_name=project,
        repository_name=repository,
        commit_sha=commit_sha,
    )
