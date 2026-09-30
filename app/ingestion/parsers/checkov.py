"""Adaptateur Checkov.

Checkov produit du SARIF 2.1.0 standard (infrastructure as code) : le
parsing est assuré par le cœur SARIF commun.
"""

from typing import Any

from app.ingestion.models import NormalizedFinding
from app.ingestion.sarif import parse_sarif_results

SCANNER = "checkov"


def parse_checkov_report(report: dict[str, Any]) -> list[NormalizedFinding]:
    """Convertit un rapport SARIF Checkov en findings normalisés."""
    return parse_sarif_results(report, SCANNER)
