"""Local qwen facade tests."""

from pathlib import Path

from backend.local_models.qwen import QwenLocalModel


def test_qwen_identity(tmp_path, monkeypatch):
    monkeypatch.setenv("QWEN_MODEL_PATH", str(tmp_path / "empty"))
    monkeypatch.setenv("NEXUS_DATA_DIR", str(tmp_path))
    from backend.config import get_settings

    get_settings.cache_clear()
    s = get_settings()
    Path(s.qwen_model_path).mkdir(parents=True, exist_ok=True)
    model = QwenLocalModel(s)
    assert model.model_key == "qwen-local"
    assert "Qwen" in model.display_name
    get_settings.cache_clear()
