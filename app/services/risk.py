"""Calcul du score de risque, simple et explicable.

Le score (0-100) part de la sévérité, la moyenne avec le CVSS ×10 quand le
scanner le fournit, puis applique un facteur de confiance. Le CWE est
conservé comme information mais ne modifie pas le score.
"""

from app.models import Severity

SEVERITY_SCORES: dict[Severity, int] = {
    Severity.CRITICAL: 90,
    Severity.HIGH: 70,
    Severity.MEDIUM: 50,
    Severity.LOW: 30,
    Severity.INFO: 10,
}

CONFIDENCE_FACTORS: dict[str, float] = {
    "HIGH": 1.0,
    "MEDIUM": 0.9,
    "LOW": 0.8,
}


def compute_risk_score(
    *,
    severity: Severity,
    cvss_score: float | None = None,
    confidence: str | None = None,
) -> int:
    """Score de priorité 0-100, reproductible et explicable."""
    base = float(SEVERITY_SCORES[severity])
    if cvss_score is not None:
        base = (base + cvss_score * 10) / 2

    factor = CONFIDENCE_FACTORS.get((confidence or "").upper(), 1.0)
    return max(0, min(100, round(base * factor)))
