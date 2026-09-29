"""Fixtures partagées : transaction de test annulée, client HTTP."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.core.database import engine, get_db
from app.main import app


@pytest.fixture()
def db_connection() -> Iterator[Connection]:
    """Connexion ouverte dans une transaction annulée à la fin du test.

    Tout ce que le test insère disparaît au rollback : la base de
    développement n'est jamais polluée.
    """
    connection = engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()


@pytest.fixture()
def db_session(db_connection: Connection) -> Iterator[Session]:
    """Session liée à la transaction de test, pour les assertions."""
    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_connection: Connection) -> Iterator[TestClient]:
    """Client HTTP dont les requêtes partagent la transaction de test."""

    def override_get_db() -> Iterator[Session]:
        session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
