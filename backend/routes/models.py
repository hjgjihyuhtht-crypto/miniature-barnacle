"""Models and providers listing."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.auth import require_api_key
from backend.services.model_manager import get_model_manager

router = APIRouter(prefix="/v1", tags=["models"])


@router.get("/models")
async def list_models(_: str = Depends(require_api_key)):
    mm = get_model_manager()
    return {"object": "list", "data": mm.list_models()}


@router.get("/providers")
async def list_providers(_: str = Depends(require_api_key)):
    mm = get_model_manager()
    return {
        "providers": [
            {"id": "llama-local", "type": "local", "status": "ok" if mm.local_available("llama-local") else "offline"},
            {"id": "qwen-local", "type": "local", "status": "ok" if mm.local_available("qwen-local") else "offline"},
            {"id": "openai", "type": "api", "status": "configured" if mm.openai.configured else "not_configured"},
            {"id": "gemini", "type": "api", "status": "configured" if mm.gemini.configured else "not_configured"},
            {"id": "claude", "type": "api", "status": "configured" if mm.claude.configured else "not_configured"},
        ]
    }
