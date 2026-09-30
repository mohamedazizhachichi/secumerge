"""Adaptateur Semgrep.

Semgrep produit du SARIF 2.1.0 standard : le parsing est assuré par le
cœur SARIF commun. Ce module isole le scanner et accueillera ses
spécificités éventuelles.
"""

from typing import Any

from app.ingestion.models import NormalizedFinding
from app.ingestion.sarif import parse_sarif_results

SCANNER = "semgrep"


def parse_semgrep_report(report: dict[str, Any]) -> list[NormalizedFinding]:
    """Convertit un rapport SARIF Semgrep en findings normalisés."""
    return parse_sarif_results(report, SCANNER)
