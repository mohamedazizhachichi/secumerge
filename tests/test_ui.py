"""Tests d'intégration de l'interface web minimale."""

import json

from fastapi.testclient import TestClient

BASE_FIELDS = {
    "project": "pytest-ui",
    "repository": "pytest-ui-repo",
    "scanner": "semgrep",
    "commit_sha": "commit-ui",
    "branch": "main",
    "is_complete": "true",
}

CRIT_RULE = "ui-test.crit"
LOW_RULE = "ui-test.low"
CRIT_TITLE = "Problème critique de test UI"
LOW_TITLE = "Problème mineur de test UI"


def post_scan(client: TestClient, *, report: bytes, **fields: str):
    data = dict(BASE_FIELDS)
    data.update(fields)
    return client.post(
        "/scans",
        data=data,
        files={"file": ("report.sarif", report, "application/json")},
    )


def ui_report(*, include_crit: bool = True, include_low: bool = True) -> bytes:
    """Rapport SARIF avec des règles uniques aux tests de l'UI."""
    rules = []
    results = []
    if include_crit:
        rules.append({"id": CRIT_RULE, "properties": {"security-severity": "10.0"}})
        results.append(
            {
                "ruleId": CRIT_RULE,
                "level": "error",
                "message": {"text": CRIT_TITLE},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": "app/test.py"},
                            "region": {"startLine": 1},
                        }
                    }
                ],
            }
        )
    if include_low:
        rules.append({"id": LOW_RULE})
        results.append(
            {
                "ruleId": LOW_RULE,
                "level": "note",
                "message": {"text": LOW_TITLE},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": "app/test.py"},
                            "region": {"startLine": 9},
                        }
                    }
                ],
            }
        )
    return json.dumps(
        {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "Semgrep", "rules": rules}},
                    "results": results,
                }
            ],
        }
    ).encode()


def test_dashboard_renders_findings_and_counters(client: TestClient) -> None:
    post_scan(client, report=ui_report())

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert CRIT_TITLE in body
    assert LOW_TITLE in body
    assert 'data-testid="severity-count-CRITICAL"' in body
    assert 'data-testid="finding-row"' in body


def test_dashboard_filters_by_severity(client: TestClient) -> None:
    post_scan(client, report=ui_report())

    body = client.get("/", params={"severity": "CRITICAL"}).text

    assert CRIT_TITLE in body
    assert LOW_TITLE not in body


def test_dashboard_filters_by_scanner(client: TestClient) -> None:
    post_scan(client, report=ui_report())

    body = client.get("/", params={"scanner": "trivy"}).text

    assert CRIT_TITLE not in body


def test_dashboard_ignores_empty_and_unknown_filters(client: TestClient) -> None:
    post_scan(client, report=ui_report())

    # Un formulaire HTML envoie des chaînes vides pour les listes non choisies.
    response = client.get("/", params={"severity": "", "status": "", "scanner": ""})
    assert response.status_code == 200
    assert CRIT_TITLE in response.text

    # Une valeur inconnue est ignorée, pas une erreur.
    response = client.get("/", params={"severity": "BOGUS"})
    assert response.status_code == 200
    assert CRIT_TITLE in response.text


def test_dashboard_filters_by_status(client: TestClient) -> None:
    post_scan(client, report=ui_report())
    post_scan(client, report=ui_report(include_low=False), commit_sha="commit-ui-2")

    resolved = client.get("/", params={"status": "RESOLVED"}).text
    assert LOW_TITLE in resolved
    assert CRIT_TITLE not in resolved

    opened = client.get("/", params={"status": "OPEN"}).text
    assert CRIT_TITLE in opened
    assert LOW_TITLE not in opened
