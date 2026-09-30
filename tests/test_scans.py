"""Tests d'intégration de l'endpoint POST /scans et de la normalisation."""

import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Finding,
    FindingOccurrence,
    Project,
    Repository,
    RiskAssessment,
    ScanExecution,
)
from app.services import scans as scan_service

VALID_REPORT = {
    "version": "2.1.0",
    "runs": [
        {
            "tool": {"driver": {"name": "Semgrep"}},
            "results": [
                {
                    "ruleId": "demo.rule",
                    "level": "warning",
                    "message": {"text": "Problème de démonstration"},
                    "locations": [],
                }
            ],
        }
    ],
}

BASE_FIELDS = {
    "project": "pytest-demo",
    "repository": "pytest-repo",
    "scanner": "semgrep",
    "commit_sha": "abc123",
    "branch": "main",
    "is_complete": "true",
}

DATA_DIR = Path(__file__).parent / "data"

EVAL_RULE = "python.lang.security.audit.eval-detected.eval-detected"
SUB_RULE = "python.lang.security.audit.subprocess-shell-true.subprocess-shell-true"


def sample(name: str) -> bytes:
    return (DATA_DIR / name).read_bytes()


def post_scan(client: TestClient, *, report: bytes | None = None, **fields: str):
    data = dict(BASE_FIELDS)
    data.update(fields)
    content = report if report is not None else json.dumps(VALID_REPORT).encode()
    return client.post(
        "/scans",
        data=data,
        files={"file": ("report.sarif", content, "application/json")},
    )


def _repository(db_session: Session) -> Repository:
    return db_session.scalars(
        select(Repository).where(Repository.name == BASE_FIELDS["repository"])
    ).one()


def test_ingest_valid_report(client: TestClient, db_session: Session) -> None:
    response = post_scan(client)

    assert response.status_code == 201
    body = response.json()
    assert body["scanner"] == "semgrep"
    assert body["commit_sha"] == "abc123"
    assert body["is_complete"] is True
    assert body["findings_created"] == 1

    scan = db_session.get(ScanExecution, body["id"])
    assert scan is not None
    assert scan.raw_report["version"] == "2.1.0"


def test_ingest_empty_report_is_accepted(client: TestClient) -> None:
    response = post_scan(client, report=b"{}")

    assert response.status_code == 201
    assert response.json()["findings_created"] == 0
    assert response.json()["findings_updated"] == 0


def test_reject_invalid_json(client: TestClient) -> None:
    response = post_scan(client, report=b"{pas du json")

    assert response.status_code == 400


def test_reject_non_object_report(client: TestClient) -> None:
    response = post_scan(client, report=b"[1, 2, 3]")

    assert response.status_code == 400


def test_reject_unknown_scanner(client: TestClient) -> None:
    response = post_scan(client, scanner="scanner-inconnu")

    assert response.status_code == 422


def test_reject_report_too_large(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(scan_service, "MAX_REPORT_SIZE", 16)

    response = post_scan(client, report=b'{"padding": "' + b"x" * 64 + b'"}')

    assert response.status_code == 413


def test_project_and_repository_are_reused(
    client: TestClient, db_session: Session
) -> None:
    post_scan(client, commit_sha="commit-1")
    post_scan(client, commit_sha="commit-2")

    projects = db_session.scalars(
        select(Project).where(Project.name == BASE_FIELDS["project"])
    ).all()
    repositories = db_session.scalars(
        select(Repository).where(Repository.name == BASE_FIELDS["repository"])
    ).all()
    assert len(projects) == 1
    assert len(repositories) == 1

    scan_count = db_session.scalar(
        select(func.count())
        .select_from(ScanExecution)
        .where(ScanExecution.repository_id == repositories[0].id)
    )
    assert scan_count == 2


def test_semgrep_report_creates_normalized_finding(
    client: TestClient, db_session: Session
) -> None:
    response = post_scan(client)

    assert response.status_code == 201
    assert response.json()["findings_created"] == 1

    repository = _repository(db_session)
    finding = db_session.scalars(
        select(Finding).where(Finding.repository_id == repository.id)
    ).one()
    assert finding.scanner == "semgrep"
    assert finding.rule_id == "demo.rule"
    assert finding.severity == "MEDIUM"
    assert finding.status == "OPEN"
    assert finding.title == "Problème de démonstration"

    occurrence = db_session.scalars(
        select(FindingOccurrence).where(FindingOccurrence.finding_id == finding.id)
    ).one()
    assert occurrence.scan_execution_id == response.json()["id"]


def test_reingesting_same_finding_reuses_row(
    client: TestClient, db_session: Session
) -> None:
    first = post_scan(client, commit_sha="commit-1")
    assert first.json()["findings_created"] == 1

    repository = _repository(db_session)
    finding = db_session.scalars(
        select(Finding).where(Finding.repository_id == repository.id)
    ).one()
    finding.status = "CONFIRMED"
    db_session.commit()

    second = post_scan(client, commit_sha="commit-2")
    assert second.json()["findings_created"] == 0
    assert second.json()["findings_updated"] == 1
    assert second.json()["findings_resolved"] == 0

    db_session.expire_all()
    findings = db_session.scalars(
        select(Finding).where(Finding.repository_id == repository.id)
    ).all()
    assert len(findings) == 1
    assert findings[0].status == "CONFIRMED"

    occurrences = db_session.scalars(
        select(FindingOccurrence).where(FindingOccurrence.finding_id == findings[0].id)
    ).all()
    assert len(occurrences) == 2


def test_empty_report_creates_no_finding(
    client: TestClient, db_session: Session
) -> None:
    response = post_scan(client, report=b"{}")

    assert response.status_code == 201
    repository = _repository(db_session)
    findings = db_session.scalars(
        select(Finding).where(Finding.repository_id == repository.id)
    ).all()
    assert findings == []


def test_trivy_report_creates_critical_finding(
    client: TestClient, db_session: Session
) -> None:
    response = post_scan(client, scanner="trivy", report=sample("trivy-example.sarif"))

    assert response.status_code == 201
    assert response.json()["findings_created"] == 1

    repository = _repository(db_session)
    finding = db_session.scalars(
        select(Finding).where(Finding.repository_id == repository.id)
    ).one()
    assert finding.scanner == "trivy"
    assert finding.rule_id == "CVE-2020-14343"
    assert finding.severity == "CRITICAL"
    assert finding.file_path == "requirements.txt"


def test_checkov_report_creates_finding(
    client: TestClient, db_session: Session
) -> None:
    response = post_scan(
        client, scanner="checkov", report=sample("checkov-example.sarif")
    )

    assert response.status_code == 201
    assert response.json()["findings_created"] == 1

    repository = _repository(db_session)
    finding = db_session.scalars(
        select(Finding).where(Finding.repository_id == repository.id)
    ).one()
    assert finding.scanner == "checkov"
    assert finding.rule_id == "CKV_AWS_20"
    assert finding.severity == "HIGH"
    assert finding.file_path == "main.tf"
    assert finding.location == "5"


def test_disappeared_finding_is_resolved_by_complete_scan(
    client: TestClient, db_session: Session
) -> None:
    first = post_scan(
        client, report=sample("semgrep-two-findings.sarif"), commit_sha="run-1"
    )
    assert first.json()["findings_created"] == 2

    second = post_scan(
        client, report=sample("semgrep-example.sarif"), commit_sha="run-2"
    )
    assert second.json()["findings_created"] == 0
    assert second.json()["findings_updated"] == 1
    assert second.json()["findings_resolved"] == 1

    db_session.expire_all()
    repository = _repository(db_session)
    findings = {
        finding.rule_id: finding
        for finding in db_session.scalars(
            select(Finding).where(Finding.repository_id == repository.id)
        ).all()
    }
    assert findings[SUB_RULE].status == "RESOLVED"
    assert findings[EVAL_RULE].status == "OPEN"


def test_partial_scan_does_not_resolve(client: TestClient, db_session: Session) -> None:
    post_scan(client, report=sample("semgrep-two-findings.sarif"), commit_sha="run-1")

    partial = post_scan(
        client,
        report=sample("semgrep-example.sarif"),
        commit_sha="run-2",
        is_complete="false",
    )
    assert partial.json()["findings_resolved"] == 0

    db_session.expire_all()
    repository = _repository(db_session)
    statuses = db_session.scalars(
        select(Finding.status).where(Finding.repository_id == repository.id)
    ).all()
    assert set(statuses) == {"OPEN"}


def test_report_without_sarif_runs_does_not_resolve(
    client: TestClient, db_session: Session
) -> None:
    post_scan(client, commit_sha="run-1")

    empty = post_scan(client, report=b"{}", commit_sha="run-2")
    assert empty.json()["findings_resolved"] == 0

    db_session.expire_all()
    repository = _repository(db_session)
    finding = db_session.scalars(
        select(Finding).where(Finding.repository_id == repository.id)
    ).one()
    assert finding.status == "OPEN"


def test_resolved_finding_is_not_reopened(
    client: TestClient, db_session: Session
) -> None:
    post_scan(client, report=sample("semgrep-two-findings.sarif"), commit_sha="run-1")
    post_scan(client, report=sample("semgrep-example.sarif"), commit_sha="run-2")

    db_session.expire_all()
    repository = _repository(db_session)
    resolved = db_session.scalars(
        select(Finding).where(
            Finding.repository_id == repository.id, Finding.rule_id == SUB_RULE
        )
    ).one()
    assert resolved.status == "RESOLVED"

    third = post_scan(
        client, report=sample("semgrep-two-findings.sarif"), commit_sha="run-3"
    )
    assert third.json()["findings_updated"] == 2

    db_session.expire_all()
    still_resolved = db_session.scalars(
        select(Finding).where(
            Finding.repository_id == repository.id, Finding.rule_id == SUB_RULE
        )
    ).one()
    assert still_resolved.status == "RESOLVED"  # pas de réouverture automatique


def test_risk_assessment_created_with_cvss(
    client: TestClient, db_session: Session
) -> None:
    post_scan(client, scanner="trivy", report=sample("trivy-example.sarif"))

    repository = _repository(db_session)
    finding = db_session.scalars(
        select(Finding).where(Finding.repository_id == repository.id)
    ).one()
    assessment = db_session.scalars(
        select(RiskAssessment).where(RiskAssessment.finding_id == finding.id)
    ).one()

    assert assessment.score == 94  # CRITICAL 90 moyenné avec CVSS 9.8
    assert assessment.cvss_score == 9.8
    assert assessment.confidence is None


def test_risk_assessment_is_not_duplicated(
    client: TestClient, db_session: Session
) -> None:
    post_scan(
        client, scanner="trivy", report=sample("trivy-example.sarif"), commit_sha="rev-1"
    )
    post_scan(
        client, scanner="trivy", report=sample("trivy-example.sarif"), commit_sha="rev-2"
    )

    repository = _repository(db_session)
    finding = db_session.scalars(
        select(Finding).where(Finding.repository_id == repository.id)
    ).one()
    assessments = db_session.scalars(
        select(RiskAssessment).where(RiskAssessment.finding_id == finding.id)
    ).all()

    assert len(assessments) == 1
    assert assessments[0].score == 94


def test_semgrep_assessment_stores_cwe(
    client: TestClient, db_session: Session
) -> None:
    post_scan(client, report=sample("semgrep-example.sarif"))

    repository = _repository(db_session)
    finding = db_session.scalars(
        select(Finding).where(Finding.repository_id == repository.id)
    ).one()
    assessment = db_session.scalars(
        select(RiskAssessment).where(RiskAssessment.finding_id == finding.id)
    ).one()

    assert assessment.score == 50  # MEDIUM sans CVSS
    assert assessment.cwe == "CWE-95"
