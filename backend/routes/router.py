"""Router choose endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import require_api_key
from backend.config import get_settings
from backend.models import RouterChooseRequest, RouterChooseResponse
from backend.services.model_router import get_model_router

router = APIRouter(prefix="/v1/router", tags=["router"])


@router.post("/choose", response_model=RouterChooseResponse)
async def choose_model(body: RouterChooseRequest, _: str = Depends(require_api_key)):
    settings = get_settings()
    allow = body.allow_external_apis
    if allow is None:
        allow = settings.allow_external_apis
    try:
        decision = get_model_router().choose(
            model=body.model,
            messages=[m.model_dump() for m in body.messages],
            routing_mode=body.routing_mode,
            allow_external_apis=allow,
            attachment_kinds=body.attachment_kinds,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RouterChooseResponse(
        selected_model=decision.selected_model,
        mode=decision.mode,
        task_type=decision.task_type,
        location=decision.location,
        display_name=decision.display_name,
        reason=decision.reason,
    )
