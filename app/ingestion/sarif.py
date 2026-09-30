"""Utilitaires et cœur de parsing des rapports SARIF.

Semgrep, Trivy et Checkov produisent tous du SARIF 2.1.0 : le parcours
tolérant du document (catalogue de règles, résultats, localisations) est
mutualisé ici. Chaque scanner garde son module dédié pour accueillir ses
spécificités éventuelles.
"""

from typing import Any

from app.ingestion.fingerprint import compute_fingerprint
from app.ingestion.models import NormalizedFinding
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


def map_security_severity(value: Any) -> Severity | None:
    """Traduit un score CVSS « security-severity » (0-10) en sévérité.

    Retourne None si la valeur n'est pas un score exploitable.
    """
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None

    if score >= 9.0:
        return Severity.CRITICAL
    if score >= 7.0:
        return Severity.HIGH
    if score >= 4.0:
        return Severity.MEDIUM
    if score > 0:
        return Severity.LOW
    return Severity.INFO


def map_sarif_severity(level: str | None, security_severity: Any = None) -> Severity:
    """Préfère le score CVSS de la règle ; sinon retombe sur le niveau SARIF."""
    return map_security_severity(security_severity) or map_sarif_level(level)


def as_dict(value: Any) -> dict[str, Any]:
    """Retourne la valeur si c'est un objet JSON, sinon un objet vide."""
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    """Retourne la valeur si c'est une liste JSON, sinon une liste vide."""
    return value if isinstance(value, list) else []


def has_sarif_runs(report: dict[str, Any]) -> bool:
    """Vrai si le rapport contient au moins un run SARIF exploitable.

    Garde-fou pour la résolution automatique : un rapport vide ou mal formé
    ne doit jamais être interprété comme « plus aucun finding ».
    """
    return any(isinstance(raw_run, dict) for raw_run in as_list(report.get("runs")))


def _text(value: Any) -> str | None:
    """Retourne une chaîne non vide, sinon None."""
    return value if isinstance(value, str) and value.strip() else None


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


def _rules_by_id(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Indexe le catalogue de règles du run par identifiant."""
    driver = as_dict(as_dict(run.get("tool")).get("driver"))
    rules: dict[str, dict[str, Any]] = {}
    for raw_rule in as_list(driver.get("rules")):
        rule = as_dict(raw_rule)
        rule_id = rule.get("id")
        if isinstance(rule_id, str):
            rules[rule_id] = rule
    return rules


def parse_sarif_results(report: dict[str, Any], scanner: str) -> list[NormalizedFinding]:
    """Convertit un rapport SARIF en findings normalisés, de façon tolérante.

    Les entrées malformées ou vides sont ignorées plutôt que de faire
    échouer l'ingestion : le rapport est une donnée non fiable.
    """
    findings: list[NormalizedFinding] = []

    for raw_run in as_list(report.get("runs")):
        run = as_dict(raw_run)
        rules = _rules_by_id(run)

        for raw_result in as_list(run.get("results")):
            if not isinstance(raw_result, dict):
                continue
            result = raw_result

            rule_id = result.get("ruleId")
            if not isinstance(rule_id, str) or not rule_id:
                rule_id = None

            message = _text(as_dict(result.get("message")).get("text"))
            file_path, location = extract_location(result)

            # Entrée sans rien d'exploitable : ignorée plutôt que stockée.
            if rule_id is None and message is None and file_path is None:
                continue

            rule = as_dict(rules.get(rule_id)) if rule_id else {}

            level = _text(result.get("level")) or _text(
                as_dict(rule.get("defaultConfiguration")).get("level")
            )
            security_severity = as_dict(rule.get("properties")).get("security-severity")
            severity = map_sarif_severity(level, security_severity)

            short = _text(as_dict(rule.get("shortDescription")).get("text"))
            first_line = message.splitlines()[0] if message else None
            title = short or first_line or rule_id or "Finding sans titre"
            description = message if message and message != title else None

            findings.append(
                NormalizedFinding(
                    scanner=scanner,
                    rule_id=rule_id,
                    title=title,
                    description=description,
                    severity=severity,
                    file_path=file_path,
                    location=location,
                    fingerprint=compute_fingerprint(
                        scanner=scanner,
                        rule_id=rule_id,
                        file_path=file_path,
                        location=location,
                    ),
                )
            )

    return findings
