"""Modèle ScanExecution : un rapport de scan reçu pour un dépôt."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.finding_occurrence import FindingOccurrence
    from app.models.repository import Repository


class ScanExecution(Base):
    __tablename__ = "scan_executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    scanner: Mapped[str] = mapped_column(String(50))
    commit_sha: Mapped[str] = mapped_column(String(64))
    branch: Mapped[str | None] = mapped_column(String(200))
    is_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_report: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    repository: Mapped[Repository] = relationship(back_populates="scan_executions")
    occurrences: Mapped[list[FindingOccurrence]] = relationship(
        back_populates="scan_execution", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"ScanExecution(id={self.id!r}, scanner={self.scanner!r}, "
            f"commit_sha={self.commit_sha!r})"
        )
