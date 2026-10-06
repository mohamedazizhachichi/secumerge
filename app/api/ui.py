"""Interface web minimale : tableau de bord des findings."""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import FindingStatus, Scanner, Severity
from app.services.dashboard import build_dashboard_data

router = APIRouter(tags=["ui"])

templates = Jinja2Templates(directory="app/templates")


def _clean_filter(value: str | None, allowed: list[str]) -> str | None:
    """Retourne le filtre s'il est valide, sinon None (filtre ignoré).

    Les formulaires HTML envoient une chaîne vide pour les listes non
    choisies : on la traite comme « pas de filtre » plutôt qu'une erreur,
    tout comme une valeur inconnue.
    """
    return value if value in allowed else None


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard(
    request: Request,
    severity: str | None = Query(None),
    status: str | None = Query(None),
    scanner: str | None = Query(None),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Compteurs, liste des findings et filtres simples."""
    severity_values = [value.value for value in Severity]
    status_values = [value.value for value in FindingStatus]
    scanner_values = [value.value for value in Scanner]

    selected = {
        "severity": _clean_filter(severity, severity_values),
        "status": _clean_filter(status, status_values),
        "scanner": _clean_filter(scanner, scanner_values),
    }

    data = build_dashboard_data(
        db,
        severity=selected["severity"],
        status=selected["status"],
        scanner=selected["scanner"],
    )
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "data": data,
            "severities": severity_values,
            "statuses": status_values,
            "scanners": scanner_values,
            "selected": selected,
        },
    )
