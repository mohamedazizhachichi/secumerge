"""Point d'entrée de l'application SecuMerge."""

from fastapi import FastAPI

from app.api.scans import router as scans_router

app = FastAPI(
    title="SecuMerge",
    description="Plateforme légère de gestion de findings de sécurité.",
    version="0.1.0",
)

app.include_router(scans_router)


@app.get("/")
def root() -> dict[str, str]:
    """Page d'accueil minimale de l'API."""
    return {
        "application": "SecuMerge",
        "status": "ok",
        "documentation": "/docs",
    }


@app.get("/health")
def health() -> dict[str, str]:
    """Vérifie que l'API répond."""
    return {"status": "ok"}
