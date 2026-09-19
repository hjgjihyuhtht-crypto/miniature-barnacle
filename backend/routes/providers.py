"""Provider status routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.auth import require_api_key
from backend.services.model_manager import get_model_manager

router = APIRouter(prefix="/v1/providers", tags=["providers"])


@router.get("/status")
async def providers_status(_: str = Depends(require_api_key)):
    mm = get_model_manager()
    return {
        "openai": await mm.openai.health(),
        "gemini": await mm.gemini.health(),
        "claude": await mm.claude.health(),
        "llama": await mm.llama.health(),
        "qwen": await mm.qwen.health(),
    }
