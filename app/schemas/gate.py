"""Schémas API du Security Gate."""

from enum import StrEnum

from pydantic import BaseModel


class GateStatus(StrEnum):
    """Verdict du gate pour un commit."""

    PASS = "PASS"
    FAIL = "FAIL"


class GateScannerStatus(BaseModel):
    """Situation d'un scanner attendu pour un commit."""

    scanner: str
    satisfied: bool
    scans: int
    complete_scans: int


class GateReport(BaseModel):
    """Verdict complet du Security Gate."""

    status: GateStatus
    project: str
    repository: str
    commit_sha: str
    scanners: list[GateScannerStatus]
    missing: list[str]
