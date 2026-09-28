from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "Kharazmi_Server"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

from .seed import seed_database  # noqa: E402


@pytest.fixture(scope="session")
def audit_context(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("route-audit") / "demo.db"
    os.environ["JWT_SECRET_KEY"] = "route-audit-pytest-secret-" + "x" * 40
    manifest = seed_database(db_path)
    yield {"path": db_path, "manifest": manifest}


@pytest.fixture(scope="session")
def audit_app(audit_context):
    # Import only after seed selected the temporary DATABASE_URL.
    import main  # type: ignore
    return main.app


@pytest.fixture(scope="session")
def client(audit_app):
    with TestClient(audit_app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(audit_context):
    return {role: {"Authorization": f"Bearer {token}"} for role, token in audit_context["manifest"]["roles"].items()}


@pytest.fixture
def db(audit_context):
    import models  # type: ignore
    session = models.SessionLocal()
    try:
        yield session
    finally:
        session.close()
