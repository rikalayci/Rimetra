import os
import tempfile

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres@127.0.0.1:5432/rimetra_test")
os.environ["DATA_PATH"] = tempfile.mkdtemp(prefix="rimetra-test-")
os.environ["DISABLE_SCHEDULER"] = "true"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["DATA_ENCRYPTION_KEY"] = "test-data-key"

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import SessionLocal, get_engine  # noqa: E402
from app.security import login_throttle, rate_limiter  # noqa: E402

BACKEND = os.path.dirname(os.path.dirname(__file__))


@pytest.fixture(scope="session", autouse=True)
def _schema():
    eng = get_engine()
    with eng.begin() as c:
        c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    cfg = Config(os.path.join(BACKEND, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND, "alembic"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture()
def client():
    from app.main import app
    eng = get_engine()
    with eng.begin() as c:
        c.execute(text("TRUNCATE audit_log, idempotency_keys, telegram_link_codes, results, panels, reports, facilities, notes, reminders, "
                       "sessions, api_keys, users, members, test_aliases, test_definitions RESTART IDENTITY CASCADE"))
    rate_limiter.reset()
    login_throttle.reset()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def family(client):
    """Master + iki üye + API anahtarları."""
    from app.bootstrap import create_master
    with SessionLocal() as db:
        create_master(db, "burak", "supersecret1", "Burak")
    r = client.post("/api/auth/login", json={"username": "burak", "password": "supersecret1"})
    assert r.status_code == 200, r.text
    me = r.json()
    H = {"x-rimetra": "1"}
    ayse = client.post("/api/app/members", json={"display_name": "Ayşe", "full_name": "AYŞE YILMAZ", "sex": "F"}, headers=H).json()
    client.patch(f"/api/app/members/{me['member_id']}", json={"full_name": "BURAK YILMAZ"}, headers=H)
    full = client.post("/api/app/admin/api-keys", headers=H, json={
        "name": "Claude ajanı", "scopes": ["reports:read", "reports:write", "members:read", "catalog:write"]}).json()
    limited = client.post("/api/app/admin/api-keys", headers=H, json={
        "name": "Sadece Ayşe", "scopes": ["reports:read", "reports:write", "members:read"], "member_scope": [ayse["id"]]}).json()
    return {
        "burak_id": me["member_id"],
        "ayse_id": ayse["id"],
        "key": full["key"],
        "limited_key": limited["key"],
        "H": H,
    }
