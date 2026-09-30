"""Adaptateur Semgrep : convertit un rapport SARIF en findings normalisés.

Semgrep produit du SARIF 2.1.0. On lit les résultats et le catalogue de
règles du run pour produire un `NormalizedFinding` par résultat.

Le parseur est tolérant : une entrée malformée est ignorée plutôt que de
faire échouer toute l'ingestion (le rapport est une donnée non fiable).
"""

from typing import Any

from app.ingestion.fingerprint import compute_fingerprint
from app.ingestion.models import NormalizedFinding
from app.ingestion.sarif import as_dict, as_list, extract_location, map_sarif_level

SCANNER = "semgrep"


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


def _text(value: Any) -> str | None:
    """Retourne une chaîne non vide, sinon None."""
    return value if isinstance(value, str) and value.strip() else None


def parse_semgrep_report(report: dict[str, Any]) -> list[NormalizedFinding]:
    """Convertit un rapport SARIF Semgrep en findings normalisés."""
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
            severity = map_sarif_level(level)

            short = _text(as_dict(rule.get("shortDescription")).get("text"))
            first_line = message.splitlines()[0] if message else None
            title = short or first_line or rule_id or "Finding sans titre"
            description = message if message and message != title else None

            fingerprint = compute_fingerprint(
                scanner=SCANNER,
                rule_id=rule_id,
                file_path=file_path,
                location=location,
            )

            findings.append(
                NormalizedFinding(
                    scanner=SCANNER,
                    rule_id=rule_id,
                    title=title,
                    description=description,
                    severity=severity,
                    file_path=file_path,
                    location=location,
                    fingerprint=fingerprint,
                )
            )

    return findings
