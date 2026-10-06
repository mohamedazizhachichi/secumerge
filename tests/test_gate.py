"""Tests d'intégration du Security Gate."""

from pathlib import Path

from fastapi.testclient import TestClient

DATA_DIR = Path(__file__).parent / "data"

BASE_FIELDS = {
    "project": "pytest-gate",
    "repository": "pytest-gate-repo",
    "scanner": "semgrep",
    "commit_sha": "commit-gate",
    "branch": "main",
    "is_complete": "true",
}


def sample(name: str) -> bytes:
    return (DATA_DIR / name).read_bytes()


def post_scan(client: TestClient, *, report: bytes | None = None, **fields: str):
    data = dict(BASE_FIELDS)
    data.update(fields)
    content = report if report is not None else b"{}"
    return client.post(
        "/scans",
        data=data,
        files={"file": ("report.sarif", content, "application/json")},
    )


def get_gate(client: TestClient, **overrides: str) -> dict:
    params = {
        "project": BASE_FIELDS["project"],
        "repository": BASE_FIELDS["repository"],
        "commit_sha": BASE_FIELDS["commit_sha"],
    }
    params.update(overrides)
    response = client.get("/gate", params=params)
    assert response.status_code == 200
    return response.json()


def test_gate_passes_when_all_scanners_have_complete_scans(
    client: TestClient,
) -> None:
    post_scan(client, scanner="semgrep", report=sample("semgrep-example.sarif"))
    post_scan(client, scanner="trivy", report=sample("trivy-example.sarif"))
    post_scan(client, scanner="checkov", report=sample("checkov-example.sarif"))

    report = get_gate(client)

    assert report["status"] == "PASS"
    assert report["missing"] == []
    assert all(item["satisfied"] for item in report["scanners"])


def test_gate_fails_when_a_scanner_is_missing(client: TestClient) -> None:
    post_scan(client, scanner="semgrep", report=sample("semgrep-example.sarif"))
    post_scan(client, scanner="trivy", report=sample("trivy-example.sarif"))

    report = get_gate(client)

    assert report["status"] == "FAIL"
    assert report["missing"] == ["checkov"]


def test_gate_fails_when_scanner_only_has_partial_scans(client: TestClient) -> None:
    post_scan(
        client,
        scanner="semgrep",
        report=sample("semgrep-example.sarif"),
        is_complete="false",
    )
    post_scan(client, scanner="trivy", report=sample("trivy-example.sarif"))
    post_scan(client, scanner="checkov", report=sample("checkov-example.sarif"))

    report = get_gate(client)

    assert report["status"] == "FAIL"
    assert report["missing"] == ["semgrep"]
    semgrep = next(item for item in report["scanners"] if item["scanner"] == "semgrep")
    assert semgrep["scans"] == 1
    assert semgrep["complete_scans"] == 0


def test_gate_fails_closed_for_unknown_repository(client: TestClient) -> None:
    report = get_gate(client, repository="depot-inconnu")

    assert report["status"] == "FAIL"
    assert report["missing"] == ["semgrep", "trivy", "checkov"]
    assert all(item["scans"] == 0 for item in report["scanners"])


def test_gate_passes_with_mixed_complete_and_partial(client: TestClient) -> None:
    post_scan(client, scanner="semgrep", report=sample("semgrep-example.sarif"))
    post_scan(
        client,
        scanner="semgrep",
        report=sample("semgrep-example.sarif"),
        is_complete="false",
    )
    post_scan(client, scanner="trivy", report=sample("trivy-example.sarif"))
    post_scan(client, scanner="checkov", report=sample("checkov-example.sarif"))

    report = get_gate(client)

    assert report["status"] == "PASS"
    semgrep = next(item for item in report["scanners"] if item["scanner"] == "semgrep")
    assert semgrep["scans"] == 2
    assert semgrep["complete_scans"] == 1
