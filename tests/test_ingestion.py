"""Tests unitaires de la normalisation (sans base de données)."""

import json
from pathlib import Path

from app.ingestion.fingerprint import compute_fingerprint
from app.ingestion.parsers.checkov import parse_checkov_report
from app.ingestion.parsers.semgrep import parse_semgrep_report
from app.ingestion.parsers.trivy import parse_trivy_report
from app.ingestion.sarif import (
    has_sarif_runs,
    map_sarif_level,
    map_sarif_severity,
    map_security_severity,
)
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


def test_security_severity_mapping() -> None:
    assert map_security_severity("10.0") is Severity.CRITICAL
    assert map_security_severity(9.0) is Severity.CRITICAL
    assert map_security_severity("7.5") is Severity.HIGH
    assert map_security_severity("4.0") is Severity.MEDIUM
    assert map_security_severity("0.1") is Severity.LOW
    assert map_security_severity("0") is Severity.INFO
    assert map_security_severity("pas un score") is None
    assert map_security_severity(None) is None


def test_sarif_severity_prefers_cvss() -> None:
    assert map_sarif_severity("warning", "10.0") is Severity.CRITICAL
    assert map_sarif_severity("error", None) is Severity.HIGH
    assert map_sarif_severity("note", "pas un score") is Severity.LOW


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


def test_parse_trivy_example() -> None:
    report = json.loads((DATA_DIR / "trivy-example.sarif").read_text(encoding="utf-8"))

    findings = parse_trivy_report(report)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.scanner == "trivy"
    assert finding.rule_id == "CVE-2020-14343"
    assert finding.severity is Severity.CRITICAL  # CVSS 9.8, pas le niveau « error »
    assert finding.file_path == "requirements.txt"
    assert finding.location == "1:1"
    assert finding.title.startswith("CVE-2020-14343")


def test_parse_checkov_example() -> None:
    report = json.loads(
        (DATA_DIR / "checkov-example.sarif").read_text(encoding="utf-8")
    )

    findings = parse_checkov_report(report)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.scanner == "checkov"
    assert finding.rule_id == "CKV_AWS_20"
    assert finding.severity is Severity.HIGH
    assert finding.file_path == "main.tf"
    assert finding.location == "5"
    assert finding.description is None  # le message sert de titre


def test_parse_tolerates_malformed_reports() -> None:
    assert parse_semgrep_report({}) == []
    assert parse_semgrep_report({"runs": "pas une liste"}) == []
    assert parse_semgrep_report({"runs": [{"results": "pas une liste"}]}) == []
    assert parse_semgrep_report({"runs": [{"results": ["pas un objet"]}]}) == []
    assert parse_semgrep_report({"runs": [{"results": [{}]}]}) == []


def test_has_sarif_runs() -> None:
    assert has_sarif_runs({"runs": [{}]})
    assert not has_sarif_runs({})
    assert not has_sarif_runs({"runs": []})
    assert not has_sarif_runs({"runs": ["pas un objet"]})
    assert not has_sarif_runs({"runs": "pas une liste"})
