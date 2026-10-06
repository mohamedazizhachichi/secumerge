"""Données du tableau de bord : compteurs et liste des findings.

Requêtes en lecture seule, séparées de la route pour rester testables.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Finding,
    FindingStatus,
    Project,
    Repository,
    RiskAssessment,
    Severity,
)


@dataclass(frozen=True)
class FindingRow:
    """Une ligne du tableau : le finding, son score et son contexte."""

    finding: Finding
    score: int | None
    cwe: str | None
    project_name: str
    repository_name: str


@dataclass(frozen=True)
class DashboardData:
    """Tout ce que la page affiche."""

    total_findings: int
    severity_counts: list[tuple[str, int]]
    status_counts: list[tuple[str, int]]
    rows: list[FindingRow]


def _ordered_counts(
    db: Session,
    column,
    order: list[str],
) -> list[tuple[str, int]]:
    """Compte par valeur et retourne les totaux dans l'ordre métier."""
    raw = dict(db.execute(select(column, func.count()).group_by(column)).all())
    return [(value, raw.get(value, 0)) for value in order]


def build_dashboard_data(
    db: Session,
    *,
    severity: str | None = None,
    status: str | None = None,
    scanner: str | None = None,
) -> DashboardData:
    """Compteurs globaux + liste filtrée, triée par score décroissant."""
    query = (
        select(
            Finding,
            RiskAssessment.score,
            RiskAssessment.cwe,
            Project.name,
            Repository.name,
        )
        .join(Repository, Repository.id == Finding.repository_id)
        .join(Project, Project.id == Repository.project_id)
        .outerjoin(RiskAssessment, RiskAssessment.finding_id == Finding.id)
        .order_by(RiskAssessment.score.desc().nullslast(), Finding.id.desc())
    )
    if severity is not None:
        query = query.where(Finding.severity == severity)
    if status is not None:
        query = query.where(Finding.status == status)
    if scanner is not None:
        query = query.where(Finding.scanner == scanner)

    rows = [
        FindingRow(
            finding=finding,
            score=int(score) if score is not None else None,
            cwe=cwe,
            project_name=project_name,
            repository_name=repository_name,
        )
        for finding, score, cwe, project_name, repository_name in db.execute(query).all()
    ]

    return DashboardData(
        total_findings=db.scalar(select(func.count()).select_from(Finding)) or 0,
        severity_counts=_ordered_counts(
            db, Finding.severity, [severity.value for severity in Severity]
        ),
        status_counts=_ordered_counts(
            db, Finding.status, [status.value for status in FindingStatus]
        ),
        rows=rows,
    )
