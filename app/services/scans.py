"""Ingestion d'un rapport de scan : validation et stockage.

La route HTTP reste mince ; toute la logique vit ici pour rester testable
sans passer par l'API.
"""

import json
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Project, Repository, ScanExecution

# Taille maximale d'un rapport : 10 Mio.
MAX_REPORT_SIZE = 10 * 1024 * 1024

_READ_CHUNK = 1024 * 1024


class IngestionError(Exception):
    """Erreur d'ingestion, mappée vers une erreur HTTP par la route."""


class InvalidReportError(IngestionError):
    """Le rapport n'est pas un JSON valide ou pas un objet JSON."""


class ReportTooLargeError(IngestionError):
    """Le rapport dépasse la taille maximale autorisée."""


async def read_upload_limited(upload: UploadFile) -> bytes:
    """Lit l'upload par morceaux en refusant tout dépassement de taille."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(_READ_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_REPORT_SIZE:
            raise ReportTooLargeError(
                f"Rapport trop volumineux (limite : {MAX_REPORT_SIZE} octets)."
            )
        chunks.append(chunk)
    return b"".join(chunks)


def parse_report(raw: bytes) -> dict[str, Any]:
    """Décode et valide le JSON du rapport (objet JSON uniquement)."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidReportError("Le rapport doit être encodé en UTF-8.") from exc

    try:
        report = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidReportError(
            f"JSON invalide : {exc.msg} (ligne {exc.lineno})."
        ) from exc

    if not isinstance(report, dict):
        raise InvalidReportError("Le rapport doit être un objet JSON.")
    return report


def get_or_create_project(db: Session, name: str) -> Project:
    """Retrouve le projet par son nom, ou le crée."""
    project = db.scalar(select(Project).where(Project.name == name))
    if project is None:
        project = Project(name=name)
        db.add(project)
        db.flush()
    return project


def get_or_create_repository(db: Session, project: Project, name: str) -> Repository:
    """Retrouve le dépôt par son nom dans le projet, ou le crée."""
    repository = db.scalar(
        select(Repository).where(
            Repository.project_id == project.id,
            Repository.name == name,
        )
    )
    if repository is None:
        repository = Repository(project=project, name=name)
        db.add(repository)
        db.flush()
    return repository


def ingest_scan(
    db: Session,
    *,
    project_name: str,
    repository_name: str,
    scanner: str,
    commit_sha: str,
    branch: str | None,
    is_complete: bool,
    raw_report: dict[str, Any],
) -> ScanExecution:
    """Crée l'exécution de scan et stocke le rapport brut tel quel."""
    project = get_or_create_project(db, project_name)
    repository = get_or_create_repository(db, project, repository_name)

    execution = ScanExecution(
        repository=repository,
        scanner=scanner,
        commit_sha=commit_sha,
        branch=branch,
        is_complete=is_complete,
        raw_report=raw_report,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution
