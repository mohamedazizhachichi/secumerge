"""Tests unitaires de la normalisation (sans base de données)."""

import json
from pathlib import Path

from app.ingestion.fingerprint import compute_fingerprint
from app.ingestion.parsers.semgrep import parse_semgrep_report
from app.ingestion.sarif import map_sarif_level
from app.models import Severity

DATA_DIR = Path(__file__).parent / "data"


def test_fingerprint_normalizes_path_separators() -> None:
    windows = compute_fingerprint(
        scanner="semgrep", rule_id="r", file_path="app\\a.py", location="12:5"
    )
    posix = compute_fingerprint(
        scanner="semgrep", rule_id="r", file_path="app/a.py", location="12:5"
    )

    assert windows == posix


def test_fingerprint_changes_with_location() -> None:
    first = compute_fingerprint(
        scanner="semgrep", rule_id="r", file_path="app/a.py", location="10:1"
    )
    second = compute_fingerprint(
        scanner="semgrep", rule_id="r", file_path="app/a.py", location="11:1"
    )

    assert first != second


def test_fingerprint_changes_with_rule() -> None:
    first = compute_fingerprint(
        scanner="semgrep", rule_id="regle-a", file_path="app/a.py", location="10:1"
    )
    second = compute_fingerprint(
        scanner="semgrep", rule_id="regle-b", file_path="app/a.py", location="10:1"
    )

    assert first != second


def test_severity_mapping() -> None:
    assert map_sarif_level("error") is Severity.HIGH
    assert map_sarif_level("warning") is Severity.MEDIUM
    assert map_sarif_level("note") is Severity.LOW
    assert map_sarif_level("none") is Severity.INFO
    assert map_sarif_level(None) is Severity.INFO
    assert map_sarif_level("niveau-inconnu") is Severity.INFO


def test_parse_semgrep_example() -> None:
    report = json.loads(
        (DATA_DIR / "semgrep-example.sarif").read_text(encoding="utf-8")
    )

    findings = parse_semgrep_report(report)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.scanner == "semgrep"
    assert finding.rule_id == "python.lang.security.audit.eval-detected.eval-detected"
    assert finding.severity is Severity.MEDIUM
    assert finding.file_path == "app/vulnerable.py"
    assert finding.location == "12:5"
    assert finding.title == "Détection d'un appel à eval()"
    assert finding.description == "Éviter eval() avec des données utilisateur."
    assert finding.fingerprint


def test_parse_tolerates_malformed_reports() -> None:
    assert parse_semgrep_report({}) == []
    assert parse_semgrep_report({"runs": "pas une liste"}) == []
    assert parse_semgrep_report({"runs": [{"results": "pas une liste"}]}) == []
    assert parse_semgrep_report({"runs": [{"results": ["pas un objet"]}]}) == []
    assert parse_semgrep_report({"runs": [{"results": [{}]}]}) == []
