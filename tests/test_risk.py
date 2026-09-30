"""Tests unitaires de la formule de score de risque."""

from app.models import Severity
from app.services.risk import compute_risk_score


def test_severity_baseline() -> None:
    assert compute_risk_score(severity=Severity.CRITICAL) == 90
    assert compute_risk_score(severity=Severity.HIGH) == 70
    assert compute_risk_score(severity=Severity.MEDIUM) == 50
    assert compute_risk_score(severity=Severity.LOW) == 30
    assert compute_risk_score(severity=Severity.INFO) == 10


def test_cvss_blend() -> None:
    # (90 + 9.8 * 10) / 2 = 94
    assert compute_risk_score(severity=Severity.CRITICAL, cvss_score=9.8) == 94
    # (50 + 6.1 * 10) / 2 = 55.5 -> 56
    assert compute_risk_score(severity=Severity.MEDIUM, cvss_score=6.1) == 56


def test_confidence_factor() -> None:
    assert compute_risk_score(severity=Severity.CRITICAL, confidence="HIGH") == 90
    assert compute_risk_score(severity=Severity.CRITICAL, confidence="MEDIUM") == 81
    # 70 * 0.8 = 56
    assert compute_risk_score(severity=Severity.HIGH, confidence="LOW") == 56


def test_unknown_confidence_is_neutral() -> None:
    assert compute_risk_score(severity=Severity.CRITICAL, confidence=None) == 90
    assert compute_risk_score(severity=Severity.CRITICAL, confidence="inconnue") == 90


def test_score_is_bounded() -> None:
    assert compute_risk_score(severity=Severity.INFO, confidence="LOW") == 8
    assert compute_risk_score(severity=Severity.INFO, cvss_score=0.0) == 5
