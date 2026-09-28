"""Point d'entrée de l'application SecuMerge.

Étape 0 : squelette FastAPI avec un endpoint de santé.
Les modèles, migrations et endpoints métier arriveront aux étapes suivantes.
"""

from fastapi import FastAPI

app = FastAPI(
    title="SecuMerge",
    description="Plateforme légère de gestion de findings de sécurité.",
    version="0.1.0",
)


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
