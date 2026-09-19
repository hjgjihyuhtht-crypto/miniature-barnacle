"""Router tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.config import get_settings
from backend.main import create_app
from backend.models import RoutingMode
from backend.services.intelligent_router import IntelligentRouter
from backend.services.model_manager import ModelManager


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_API_KEY", "k")
    monkeypatch.setenv("NEXUS_DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("NEXUS_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with app.router.lifespan_context(app):
            yield ac
    get_settings.cache_clear()


def test_task_analyzer_coding():
    from backend.services.intelligent_router import TaskAnalyzer

    a = TaskAnalyzer().analyze([{"role": "user", "content": "Crie um programa Python para SDR"}])
    assert a.task_type == "coding"


def test_local_only_fails_without_models(tmp_path, monkeypatch):
    monkeypatch.setenv("LLAMA_MODEL_PATH", str(tmp_path / "missing-llama"))
    monkeypatch.setenv("QWEN_MODEL_PATH", str(tmp_path / "missing-qwen"))
    get_settings.cache_clear()
    mm = ModelManager(get_settings())
    router = IntelligentRouter(mm)
    with pytest.raises(RuntimeError):
        router.choose(
            model="auto",
            messages=[{"role": "user", "content": "oi"}],
            routing_mode=RoutingMode.LOCAL_ONLY,
            allow_external_apis=False,
        )
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_router_choose_endpoint(client):
    # Without local models / keys, expect 409
    r = await client.post(
        "/v1/router/choose",
        headers={"Authorization": "Bearer k"},
        json={
            "model": "auto",
            "routing_mode": "auto",
            "messages": [{"role": "user", "content": "olá"}],
        },
    )
    assert r.status_code in (200, 409)
