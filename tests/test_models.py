"""Tests unitaires du schéma de base de données (sans connexion)."""

import app.models  # noqa: F401 — enregistre toutes les tables dans les métadonnées
from app.core.database import Base

EXPECTED_TABLES = {
    "finding_occurrences",
    "findings",
    "projects",
    "repositories",
    "risk_assessments",
    "scan_executions",
}


def test_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES
