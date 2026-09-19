"""Health and diagnostics routes."""

from __future__ import annotations

import os
import shutil
from typing import Any

from fastapi import APIRouter, Depends

from backend.auth import require_api_key
from backend.config import get_settings
from backend.memory.memory_manager import get_memory_manager
from backend.services.model_manager import get_model_manager
from backend.services.speech_to_text import get_stt

router = APIRouter(tags=["health"])


def _resources() -> dict[str, Any]:
    info: dict[str, Any] = {}
    try:
        import psutil  # optional

        vm = psutil.virtual_memory()
        info["ram"] = {
            "total_gb": round(vm.total / (1024**3), 2),
            "available_gb": round(vm.available / (1024**3), 2),
            "percent": vm.percent,
        }
        info["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        info["cpu_count"] = psutil.cpu_count()
    except Exception:
        info["ram"] = {"note": "psutil not installed"}
        info["cpu_count"] = os.cpu_count()
    try:
        usage = shutil.disk_usage("/")
        info["disk"] = {
            "total_gb": round(usage.total / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
        }
    except Exception:
        pass
    try:
        import torch

        info["gpu"] = {
            "available": torch.cuda.is_available(),
            "count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        }
    except Exception:
        info["gpu"] = {"available": False}
    return info


@router.get("/health")
async def health_public() -> dict[str, Any]:
    return {"backend": "ok", "service": "nexus-ai"}


@router.get("/v1/health")
async def health_detailed(_: str = Depends(require_api_key)) -> dict[str, Any]:
    settings = get_settings()
    mm = get_model_manager()
    stt = get_stt()
    stt_health = await stt.health()
    try:
        mem = get_memory_manager()
        emb = await mem.embeddings.health()
        memory_status = "ok" if emb.get("status") == "ok" else emb.get("status", "ok")
    except Exception:
        memory_status = "error"

    openai_status = "configured" if mm.openai.configured else "not_configured"
    gemini_status = "configured" if mm.gemini.configured else "not_configured"
    claude_status = "configured" if mm.claude.configured else "not_configured"

    return {
        "backend": "ok",
        "llama": "ok" if mm.local_available("llama-local") else "offline",
        "qwen": "ok" if mm.local_available("qwen-local") else "offline",
        "whisper": stt_health.get("status", "offline"),
        "openai": openai_status,
        "gemini": gemini_status,
        "claude": claude_status,
        "memory": memory_status,
        "resources": _resources(),
        "runtime_preference": settings.local_runtime,
        "loaded_models": list(mm._loaded),
    }
