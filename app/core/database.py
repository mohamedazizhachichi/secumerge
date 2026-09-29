"""Connexion à la base de données : moteur, sessions et classe de base.

Les noms des contraintes (index, clés étrangères, contraintes uniques et
clés primaires) suivent une convention de nommage stable : les migrations
Alembic et les modèles restent ainsi synchronisés.
"""

from collections.abc import Iterator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Classe de base de tous les modèles SQLAlchemy."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def get_db() -> Iterator[Session]:
    """Dépendance FastAPI : fournit une session de base par requête."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
