"""Local llama facade tests (offline / structure)."""

from pathlib import Path

from backend.local_models.llama import LlamaLocalModel


def test_llama_health_without_files(tmp_path, monkeypatch):
    monkeypatch.setenv("LLAMA_MODEL_PATH", str(tmp_path / "empty"))
    monkeypatch.setenv("NEXUS_DATA_DIR", str(tmp_path))
    from backend.config import get_settings

    get_settings.cache_clear()
    s = get_settings()
    Path(s.llama_model_path).mkdir(parents=True, exist_ok=True)
    model = LlamaLocalModel(s)
    assert model.model_key == "llama-local"
    assert model.display_name == "Llama 3.1 8B"
    get_settings.cache_clear()
