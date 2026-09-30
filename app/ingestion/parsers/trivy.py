"""Adaptateur Trivy.

Trivy produit du SARIF 2.1.0 standard (vulnérabilités, mauvaises
configurations, secrets) : le parsing est assuré par le cœur SARIF
commun. La sévérité profite du score CVSS « security-severity » que
Trivy ajoute aux règles.
"""

from typing import Any

from app.ingestion.models import NormalizedFinding
from app.ingestion.sarif import parse_sarif_results

SCANNER = "trivy"


def parse_trivy_report(report: dict[str, Any]) -> list[NormalizedFinding]:
    """Convertit un rapport SARIF Trivy en findings normalisés."""
    return parse_sarif_results(report, SCANNER)
