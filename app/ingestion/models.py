"""Modèle commun interne : le finding normalisé.

Chaque parseur de scanner produit des `NormalizedFinding` ; le reste de
l'application ne connaît que ce format, jamais le format d'un scanner.
"""

from dataclasses import dataclass

from app.models import Severity


@dataclass(frozen=True)
class NormalizedFinding:
    """Finding issu d'un parseur, prêt à être stocké."""

    scanner: str
    rule_id: str | None
    title: str
    description: str | None
    severity: Severity
    file_path: str | None
    location: str | None
    fingerprint: str
    cvss_score: float | None = None
    cwe: str | None = None
    confidence: str | None = None
