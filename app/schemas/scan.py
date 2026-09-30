"""Schémas Pydantic exposés par l'API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScanExecutionRead(BaseModel):
    """Exécution de scan telle que renvoyée par l'API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    scanner: str
    commit_sha: str
    branch: str | None
    is_complete: bool
    created_at: datetime
    findings_created: int = 0
    findings_updated: int = 0
