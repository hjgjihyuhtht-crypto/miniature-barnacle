"""NEXUS AI backend configuration."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BACKEND_DIR / "config"


def _cpu_count() -> int:
    try:
        return max(1, os.cpu_count() or 1)
    except Exception:
        return 1


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    nexus_api_key: str = Field(default="change-me-to-a-long-random-secret", alias="NEXUS_API_KEY")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    hf_token: str = Field(default="", alias="HF_TOKEN")

    llama_model_path: str = Field(default="/opt/nexus-ai/models/llama", alias="LLAMA_MODEL_PATH")
    qwen_model_path: str = Field(default="/opt/nexus-ai/models/qwen", alias="QWEN_MODEL_PATH")
    nexus_data_dir: str = Field(default=str(ROOT_DIR / "data"), alias="NEXUS_DATA_DIR")
    nexus_db_path: str = Field(default="", alias="NEXUS_DB_PATH")

    llama_model_id: str = Field(default="meta-llama/Llama-3.1-8B-Instruct", alias="LLAMA_MODEL_ID")
    qwen_model_id: str = Field(default="Qwen/Qwen2.5-7B-Instruct", alias="QWEN_MODEL_ID")

    local_runtime: str = Field(default="auto", alias="LOCAL_RUNTIME")
    model_max_loaded: int = Field(default=1, alias="MODEL_MAX_LOADED")
    model_keep_alive: bool = Field(default=False, alias="MODEL_KEEP_ALIVE")

    llama_context: int = Field(default=8192, alias="LLAMA_CONTEXT")
    qwen_context: int = Field(default=8192, alias="QWEN_CONTEXT")
    llama_threads: str = Field(default="auto", alias="LLAMA_THREADS")
    qwen_threads: str = Field(default="auto", alias="QWEN_THREADS")
    llama_gpu_layers: int = Field(default=0, alias="LLAMA_GPU_LAYERS")
    qwen_gpu_layers: int = Field(default=0, alias="QWEN_GPU_LAYERS")

    stt_provider: str = Field(default="auto", alias="STT_PROVIDER")
    whisper_model: str = Field(default="small", alias="WHISPER_MODEL")
    whisper_device: str = Field(default="auto", alias="WHISPER_DEVICE")
    whisper_compute_type: str = Field(default="auto", alias="WHISPER_COMPUTE_TYPE")

    embedding_provider: str = Field(default="local", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL",
    )

    host: str = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    max_request_bytes: int = Field(default=20 * 1024 * 1024, alias="MAX_REQUEST_BYTES")
    request_timeout_seconds: int = Field(default=300, alias="REQUEST_TIMEOUT_SECONDS")
    chat_max_messages: int = Field(default=100, alias="CHAT_MAX_MESSAGES")
    chat_max_content_chars: int = Field(default=100_000, alias="CHAT_MAX_CONTENT_CHARS")

    memory_enabled: bool = Field(default=True, alias="MEMORY_ENABLED")
    memory_ask_before_save: bool = Field(default=True, alias="MEMORY_ASK_BEFORE_SAVE")
    allow_external_apis: bool = Field(default=True, alias="ALLOW_EXTERNAL_APIS")
    allow_memory_in_external_apis: bool = Field(default=False, alias="ALLOW_MEMORY_IN_EXTERNAL_APIS")
    prefer_local_transcription: bool = Field(default=True, alias="PREFER_LOCAL_TRANSCRIPTION")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def db_path(self) -> Path:
        if self.nexus_db_path:
            return Path(self.nexus_db_path)
        return Path(self.nexus_data_dir) / "db" / "nexus.db"

    @property
    def uploads_dir(self) -> Path:
        return Path(self.nexus_data_dir) / "uploads"

    @property
    def audio_dir(self) -> Path:
        return Path(self.nexus_data_dir) / "audio"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def resolve_threads(self, value: str) -> int:
        if not value or value.lower() == "auto":
            return _cpu_count()
        return max(1, int(value))

    def ensure_dirs(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings


def load_json_config(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_model_capabilities() -> dict[str, Any]:
    return load_json_config("model_capabilities.json")


def load_task_patterns() -> dict[str, Any]:
    return load_json_config("task_patterns.json")
