"""Utilitaires partagés pour les rapports SARIF (Semgrep, Trivy, Checkov)."""

from typing import Any

from app.models import Severity

SARIF_LEVEL_TO_SEVERITY: dict[str, Severity] = {
    "error": Severity.HIGH,
    "warning": Severity.MEDIUM,
    "note": Severity.LOW,
    "none": Severity.INFO,
}


def map_sarif_level(level: str | None) -> Severity:
    """Traduit un niveau SARIF en sévérité SecuMerge (INFO si inconnu)."""
    if level is None:
        return Severity.INFO
    return SARIF_LEVEL_TO_SEVERITY.get(level.lower(), Severity.INFO)


def as_dict(value: Any) -> dict[str, Any]:
    """Retourne la valeur si c'est un objet JSON, sinon un objet vide."""
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    """Retourne la valeur si c'est une liste JSON, sinon une liste vide."""
    return value if isinstance(value, list) else []


def extract_location(result: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extrait (chemin de fichier, « ligne:colonne ») du premier emplacement.

    Les entrées malformées sont ignorées : le rapport est une donnée non
    fiable, on ne veut pas qu'une forme inattendue fasse échouer l'ingestion.
    """
    locations = as_list(result.get("locations"))
    if not locations:
        return None, None

    physical = as_dict(as_dict(locations[0]).get("physicalLocation"))
    artifact = as_dict(physical.get("artifactLocation"))
    region = as_dict(physical.get("region"))

    file_path = artifact.get("uri")
    if isinstance(file_path, str) and file_path:
        file_path = file_path.replace("\\", "/")
    else:
        file_path = None

    line = region.get("startLine")
    column = region.get("startColumn")
    location = None
    if isinstance(line, int):
        location = f"{line}:{column}" if isinstance(column, int) else str(line)

    return file_path, location
