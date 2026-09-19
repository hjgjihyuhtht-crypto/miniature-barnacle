"""Health endpoint tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.config import get_settings
from backend.main import create_app


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_API_KEY", "k")
    monkeypatch.setenv("NEXUS_DB_PATH", str(tmp_path / "h.db"))
    monkeypatch.setenv("NEXUS_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with app.router.lifespan_context(app):
            yield ac
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_detailed_health_no_secrets(client):
    r = await client.get("/v1/health", headers={"Authorization": "Bearer k"})
    assert r.status_code == 200
    body = r.json()
    assert body["backend"] == "ok"
    text = str(body).lower()
    assert "sk-" not in text
    assert "api_key" not in text
    assert "hf_token" not in text
