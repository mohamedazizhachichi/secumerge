"""Modèle Finding : un problème de sécurité unique pour un dépôt.

Un finding est identifié par son empreinte (`fingerprint`) : deux rapports
successifs signalant le même problème réutilisent la même ligne.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import FindingStatus, Severity

if TYPE_CHECKING:
    from app.models.finding_occurrence import FindingOccurrence
    from app.models.repository import Repository
    from app.models.risk_assessment import RiskAssessment

_SEVERITIES = ", ".join(f"'{value.value}'" for value in Severity)
_STATUSES = ", ".join(f"'{value.value}'" for value in FindingStatus)


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint(
            "repository_id", "fingerprint", name="uq_findings_repository_fingerprint"
        ),
        CheckConstraint(f"severity IN ({_SEVERITIES})", name="ck_findings_severity"),
        CheckConstraint(f"status IN ({_STATUSES})", name="ck_findings_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=FindingStatus.OPEN,
        server_default=text("'OPEN'"),
    )
    scanner: Mapped[str] = mapped_column(String(50))
    rule_id: Mapped[str | None] = mapped_column(String(200))
    file_path: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(200))
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    status_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    repository: Mapped[Repository] = relationship(back_populates="findings")
    occurrences: Mapped[list[FindingOccurrence]] = relationship(
        back_populates="finding", cascade="all, delete-orphan"
    )
    risk_assessments: Mapped[list[RiskAssessment]] = relationship(
        back_populates="finding", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"Finding(id={self.id!r}, severity={self.severity!r}, "
            f"title={self.title!r})"
        )
