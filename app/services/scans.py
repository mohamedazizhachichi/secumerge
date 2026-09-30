"""Ingestion d'un rapport de scan : validation, normalisation et stockage.

La route HTTP reste mince ; toute la logique vit ici pour rester testable
sans passer par l'API.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import NormalizedFinding
from app.ingestion.parsers import get_parser
from app.ingestion.sarif import has_sarif_runs
from app.models import (
    Finding,
    FindingOccurrence,
    FindingStatus,
    Project,
    Repository,
    ScanExecution,
)

# Taille maximale d'un rapport : 10 Mio.
MAX_REPORT_SIZE = 10 * 1024 * 1024

_READ_CHUNK = 1024 * 1024


class IngestionError(Exception):
    """Erreur d'ingestion, mappée vers une erreur HTTP par la route."""


class InvalidReportError(IngestionError):
    """Le rapport n'est pas un JSON valide ou pas un objet JSON."""


class ReportTooLargeError(IngestionError):
    """Le rapport dépasse la taille maximale autorisée."""


@dataclass
class ScanIngestResult:
    """Résultat d'une ingestion : l'exécution créée et les compteurs."""

    execution: ScanExecution
    findings_created: int = 0
    findings_updated: int = 0
    findings_resolved: int = 0


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


def _upsert_findings(
    db: Session,
    execution: ScanExecution,
    normalized_findings: list[NormalizedFinding],
    seen: set[str],
) -> tuple[int, int]:
    """Crée ou met à jour les findings, et ajoute une occurrence par finding.

    - même empreinte dans le même dépôt  -> même ligne `Finding` ;
    - le statut n'est jamais écrasé par une ré-ingestion ;
    - `seen` est rempli avec les empreintes vues dans ce scan ;
    - une même empreinte répétée dans un rapport ne compte qu'une fois.
    """
    repository = execution.repository
    now = datetime.now(UTC)
    created = 0
    updated = 0

    for item in normalized_findings:
        if item.fingerprint in seen:
            continue
        seen.add(item.fingerprint)

        finding = db.scalar(
            select(Finding).where(
                Finding.repository_id == repository.id,
                Finding.fingerprint == item.fingerprint,
            )
        )

        if finding is None:
            finding = Finding(
                repository=repository,
                fingerprint=item.fingerprint,
                title=item.title,
                description=item.description,
                severity=item.severity.value,
                scanner=item.scanner,
                rule_id=item.rule_id,
                file_path=item.file_path,
                location=item.location,
                first_seen=now,
                last_seen=now,
                status_updated_at=now,
            )
            db.add(finding)
            db.flush()
            created += 1
        else:
            finding.last_seen = now
            finding.title = item.title
            finding.description = item.description
            finding.severity = item.severity.value
            if item.file_path is not None:
                finding.file_path = item.file_path
            if item.location is not None:
                finding.location = item.location
            updated += 1

        db.add(
            FindingOccurrence(
                finding=finding,
                scan_execution=execution,
                file_path=item.file_path,
                location=item.location,
            )
        )

    return created, updated


def _resolve_missing_findings(
    db: Session,
    execution: ScanExecution,
    seen: set[str],
) -> int:
    """Résout les findings du scanner absents d'un scan complet.

    Uniquement les statuts `OPEN` et `CONFIRMED` : `FALSE_POSITIVE` et
    `ACCEPTED_RISK` sont des décisions humaines, jamais écrasées.
    """
    repository = execution.repository
    now = datetime.now(UTC)

    candidates = db.scalars(
        select(Finding).where(
            Finding.repository_id == repository.id,
            Finding.scanner == execution.scanner,
            Finding.status.in_([FindingStatus.OPEN, FindingStatus.CONFIRMED]),
        )
    ).all()

    resolved = 0
    for finding in candidates:
        if finding.fingerprint in seen:
            continue
        finding.status = FindingStatus.RESOLVED.value
        finding.status_updated_at = now
        resolved += 1
    return resolved


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
) -> ScanIngestResult:
    """Stocke l'exécution de scan, normalise ses findings et résout les
    findings disparus lorsqu'un scan complet et exploitable le permet."""
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
    db.flush()

    result = ScanIngestResult(execution=execution)
    parser = get_parser(scanner)
    if parser is not None:
        normalized = parser(raw_report)
        seen: set[str] = set()
        result.findings_created, result.findings_updated = _upsert_findings(
            db, execution, normalized, seen
        )
        if execution.is_complete and has_sarif_runs(raw_report):
            result.findings_resolved = _resolve_missing_findings(db, execution, seen)

    db.commit()
    db.refresh(execution)
    return result
