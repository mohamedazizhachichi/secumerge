"""Point d'entrée de l'application SecuMerge."""

from fastapi import FastAPI

from app.api.gate import router as gate_router
from app.api.scans import router as scans_router
from app.api.ui import router as ui_router

app = FastAPI(
    title="SecuMerge",
    description="Plateforme légère de gestion de findings de sécurité.",
    version="0.1.0",
)

app.include_router(gate_router)
app.include_router(scans_router)
app.include_router(ui_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Vérifie que l'API répond."""
    return {"status": "ok"}
