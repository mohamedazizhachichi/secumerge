"""Énumérations métier partagées par les modèles et les schémas."""

from enum import StrEnum


class Severity(StrEnum):
    """Sévérité d'un finding."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class FindingStatus(StrEnum):
    """Statut d'un finding dans son cycle de vie."""

    OPEN = "OPEN"
    CONFIRMED = "CONFIRMED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    ACCEPTED_RISK = "ACCEPTED_RISK"
    RESOLVED = "RESOLVED"


class Scanner(StrEnum):
    """Scanners externes pris en charge."""

    SEMGREP = "semgrep"
    TRIVY = "trivy"
    CHECKOV = "checkov"
