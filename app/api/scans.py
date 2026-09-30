"""Routes d'ingestion des rapports de scan."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Scanner
from app.schemas.scan import ScanExecutionRead
from app.services.scans import (
    InvalidReportError,
    ReportTooLargeError,
    ingest_scan,
    parse_report,
    read_upload_limited,
)

router = APIRouter(tags=["scans"])


@router.post(
    "/scans",
    response_model=ScanExecutionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Recevoir un rapport de scan",
)
async def create_scan(
    file: UploadFile = File(..., description="Rapport de scan (SARIF/JSON)"),
    project: str = Form(..., min_length=1, max_length=200),
    repository: str = Form(..., min_length=1, max_length=200),
    scanner: Scanner = Form(...),
    commit_sha: str = Form(..., min_length=1, max_length=64),
    branch: str | None = Form(None, max_length=200),
    is_complete: bool = Form(True),
    db: Session = Depends(get_db),
) -> ScanExecutionRead:
    """Valide le rapport reçu et l'enregistre comme exécution de scan.

    Le rapport est traité comme une donnée non fiable : taille limitée,
    JSON strictement validé, contenu jamais exécuté. S'il existe un
    parseur pour le scanner, les findings sont normalisés et stockés.
    """
    try:
        raw = await read_upload_limited(file)
        report = parse_report(raw)
    except ReportTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)
        ) from exc
    except InvalidReportError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    result = ingest_scan(
        db,
        project_name=project,
        repository_name=repository,
        scanner=scanner.value,
        commit_sha=commit_sha,
        branch=branch,
        is_complete=is_complete,
        raw_report=report,
    )
    return ScanExecutionRead.model_validate(result.execution).model_copy(
        update={
            "findings_created": result.findings_created,
            "findings_updated": result.findings_updated,
            "findings_resolved": result.findings_resolved,
        }
    )
