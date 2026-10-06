"""Verdict du Security Gate pour un commit.

Règle : chaque scanner attendu doit avoir au moins un scan COMPLET pour le
commit. Un scan partiel seul ne suffit pas, et l'absence de preuve est un
FAIL (fail-closed), jamais un PASS.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Project, Repository, Scanner, ScanExecution
from app.schemas.gate import GateReport, GateScannerStatus, GateStatus

EXPECTED_SCANNERS: tuple[str, ...] = (
    Scanner.SEMGREP.value,
    Scanner.TRIVY.value,
    Scanner.CHECKOV.value,
)


def build_gate_report(
    db: Session,
    *,
    project_name: str,
    repository_name: str,
    commit_sha: str,
) -> GateReport:
    """Construit le verdict PASS/FAIL pour un commit donné."""
    repository = db.scalar(
        select(Repository)
        .join(Project)
        .where(Project.name == project_name, Repository.name == repository_name)
    )

    executions: list[ScanExecution] = []
    if repository is not None:
        executions = list(
            db.scalars(
                select(ScanExecution).where(
                    ScanExecution.repository_id == repository.id,
                    ScanExecution.commit_sha == commit_sha,
                )
            )
        )

    scanner_statuses: list[GateScannerStatus] = []
    missing: list[str] = []
    for scanner in EXPECTED_SCANNERS:
        scans = [execution for execution in executions if execution.scanner == scanner]
        complete = [execution for execution in scans if execution.is_complete]
        satisfied = bool(complete)
        if not satisfied:
            missing.append(scanner)
        scanner_statuses.append(
            GateScannerStatus(
                scanner=scanner,
                satisfied=satisfied,
                scans=len(scans),
                complete_scans=len(complete),
            )
        )

    return GateReport(
        status=GateStatus.FAIL if missing else GateStatus.PASS,
        project=project_name,
        repository=repository_name,
        commit_sha=commit_sha,
        scanners=scanner_statuses,
        missing=missing,
    )
