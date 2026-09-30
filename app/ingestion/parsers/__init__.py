"""Registre des parseurs disponibles, par nom de scanner."""

from collections.abc import Callable
from typing import Any

from app.ingestion.models import NormalizedFinding
from app.ingestion.parsers.checkov import parse_checkov_report
from app.ingestion.parsers.semgrep import parse_semgrep_report
from app.ingestion.parsers.trivy import parse_trivy_report

Parser = Callable[[dict[str, Any]], list[NormalizedFinding]]

PARSERS: dict[str, Parser] = {
    "semgrep": parse_semgrep_report,
    "trivy": parse_trivy_report,
    "checkov": parse_checkov_report,
}


def get_parser(scanner: str) -> Parser | None:
    """Retourne le parseur du scanner, ou None s'il n'existe pas encore."""
    return PARSERS.get(scanner)
