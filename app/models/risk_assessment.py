"""Modèle RiskAssessment : le score de priorité calculé pour un finding.

La formule complète arrive à l'Étape 6 ; la table stocke le score et ses
ingrédients (CVSS, CWE, confiance) pour rester explicable.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.finding import Finding


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), index=True
    )
    score: Mapped[float] = mapped_column(Float)
    cvss_score: Mapped[float | None] = mapped_column(Float)
    cwe: Mapped[str | None] = mapped_column(String(50))
    confidence: Mapped[str | None] = mapped_column(String(20))
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    finding: Mapped[Finding] = relationship(back_populates="risk_assessments")

    def __repr__(self) -> str:
        return f"RiskAssessment(id={self.id!r}, finding_id={self.finding_id!r}, score={self.score!r})"
