"""Auth tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import create_app
from backend.config import get_settings


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_API_KEY", "test-secret-key")
    monkeypatch.setenv("NEXUS_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("NEXUS_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # trigger lifespan
        async with app.router.lifespan_context(app):
            yield ac
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_health_public(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["backend"] == "ok"


@pytest.mark.asyncio
async def test_models_requires_auth(client):
    r = await client.get("/v1/models")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_models_with_auth(client):
    r = await client.get("/v1/models", headers={"Authorization": "Bearer test-secret-key"})
    assert r.status_code == 200
    data = r.json()["data"]
    ids = [m["id"] for m in data]
    assert "llama-local" in ids
    assert "qwen-local" in ids
    assert not any("dola" in i.lower() for i in ids)
