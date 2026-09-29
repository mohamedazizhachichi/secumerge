"""Configuration de l'application, lue depuis les variables d'environnement."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres de l'application.

    En conteneur, les valeurs viennent de docker-compose.yml.
    En dehors, un fichier .env local est lu s'il existe.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Valeur par défaut : environnement de développement local (docker compose).
    database_url: str = "postgresql+psycopg://secumerge:change-moi@db:5432/secumerge"


settings = Settings()
