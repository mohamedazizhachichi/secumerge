"""Modèle FindingOccurrence : un finding vu dans un scan précis.

Une occurrence relie un finding à une exécution de scan, avec la
localisation telle qu'elle apparaissait dans ce rapport.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.finding import Finding
    from app.models.scan_execution import ScanExecution


class FindingOccurrence(Base):
    __tablename__ = "finding_occurrences"

    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), index=True
    )
    scan_execution_id: Mapped[int] = mapped_column(
        ForeignKey("scan_executions.id", ondelete="CASCADE"), index=True
    )
    file_path: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    finding: Mapped[Finding] = relationship(back_populates="occurrences")
    scan_execution: Mapped[ScanExecution] = relationship(back_populates="occurrences")

    def __repr__(self) -> str:
        return (
            f"FindingOccurrence(id={self.id!r}, finding_id={self.finding_id!r}, "
            f"scan_execution_id={self.scan_execution_id!r})"
        )
