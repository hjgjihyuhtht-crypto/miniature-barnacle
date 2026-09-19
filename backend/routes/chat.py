"""Chat completions with real streaming."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.auth import get_user_id, require_api_key
from backend.config import get_settings
from backend.database import get_db
from backend.memory.memory_manager import get_memory_manager
from backend.models import ChatCompletionRequest, ChatCompletionResponse, RouterChoice, UsageInfo
from backend.services.attachments import detect_kind, extract_text
from backend.services.model_manager import get_model_manager
from backend.services.model_router import get_model_router
from backend.services.streaming import chat_chunk, sse_event

logger = logging.getLogger("nexus.chat")
router = APIRouter(prefix="/v1/chat", tags=["chat"])


async def _load_attachment_context(attachment_ids: list[str], user_id: str) -> tuple[list[str], list[str]]:
    if not attachment_ids:
        return [], []
    db = get_db()
    texts: list[str] = []
    kinds: list[str] = []
    for aid in attachment_ids:
        row = await db.fetchone(
            "SELECT * FROM attachments WHERE id=? AND user_id=?",
            (aid, user_id),
        )
        if not row:
            continue
        kind = row["kind"] or detect_kind(row["filename"], row["content_type"])
        kinds.append(kind)
        text = row["extracted_text"] or await extract_text(row["path"], kind)
        if text:
            texts.append(f"[{row['filename']}]\n{text}")
    return texts, kinds


@router.post("/completions")
async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
    _: str = Depends(require_api_key),
):
    settings = get_settings()
    user_id = get_user_id(request)
    if len(body.messages) > settings.chat_max_messages:
        raise HTTPException(400, "Too many messages")
    for m in body.messages:
        if len(m.content) > settings.chat_max_content_chars:
            raise HTTPException(400, "Message content too large")

    allow_external = (
        body.allow_external_apis
        if body.allow_external_apis is not None
        else settings.allow_external_apis
    )
    memory_enabled = (
        body.memory_enabled if body.memory_enabled is not None else settings.memory_enabled
    )

    attachment_texts, attachment_kinds = await _load_attachment_context(
        body.attachment_ids, user_id
    )

    mm = get_model_manager()
    model_router = get_model_router()
    override = body.use_for_this_message
    pinned = body.model if body.pin_model else None

    try:
        decision = model_router.choose(
            model=body.model,
            messages=[m.model_dump() for m in body.messages],
            routing_mode=body.routing_mode,
            allow_external_apis=allow_external,
            attachment_kinds=attachment_kinds,
            pinned_model=pinned if body.pin_model else None,
            override_model=override,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    selected = decision.selected_model
    status = mm.status_for(selected)
    if status == "offline":
        raise HTTPException(
            status_code=503,
            detail={
                "message": f"{decision.display_name} está indisponível.",
                "selected_model": selected,
                "alternatives": [
                    m["id"]
                    for m in mm.list_models()
                    if m["status"] in ("ok", "configured") and m["id"] != selected
                ],
            },
        )
    if status == "not_configured":
        raise HTTPException(
            status_code=503,
            detail={
                "message": f"{decision.display_name} não está configurado.",
                "selected_model": selected,
                "alternatives": [
                    m["id"]
                    for m in mm.list_models()
                    if m["status"] in ("ok", "configured") and m["id"] != selected
                ],
            },
        )

    # Vision guard: no silent capability lie
    if "image" in attachment_kinds:
        from backend.config import load_model_capabilities

        caps = load_model_capabilities().get(selected, {})
        if not caps.get("vision"):
            raise HTTPException(
                status_code=409,
                detail={
                    "message": (
                        f"{decision.display_name} não possui visão. "
                        "Escolha um modelo com suporte a imagem."
                    ),
                    "selected_model": selected,
                    "alternatives": [
                        mid
                        for mid, meta in load_model_capabilities().items()
                        if meta.get("vision") and mm.status_for(mid) in ("ok", "configured")
                    ],
                },
            )

    is_local = selected in ("llama-local", "qwen-local")
    memory = get_memory_manager()
    raw_messages = [m.model_dump() for m in body.messages]

    if memory_enabled:
        built, memories_used, suggestions = await memory.build_messages(
            user_id=user_id,
            messages=raw_messages,
            conversation_id=body.conversation_id,
            attachment_texts=attachment_texts,
            for_external=not is_local,
            allow_memory_external=settings.allow_memory_in_external_apis,
        )
    else:
        built, memories_used, suggestions = raw_messages, [], []

    db = get_db()
    conversation_id = body.conversation_id
    if not conversation_id:
        conv = await db.create_conversation(
            user_id=user_id,
            title=(raw_messages[-1]["content"][:60] if raw_messages else "Nova conversa"),
            model=selected,
            routing_mode=body.routing_mode.value,
        )
        conversation_id = conv["id"]

    last_user = next((m["content"] for m in reversed(raw_messages) if m["role"] == "user"), "")
    await db.add_message(
        conversation_id,
        "user",
        last_user,
        model=selected,
        routing_mode=body.routing_mode.value,
    )

    router_payload = {
        "selected_model": decision.selected_model,
        "mode": decision.mode,
        "task_type": decision.task_type,
        "location": decision.location,
        "display_name": decision.display_name,
        "reason": decision.reason,
        "status": "ok",
        "memories_used": memories_used,
        "memory_suggestions": suggestions if settings.memory_ask_before_save else [],
        "conversation_id": conversation_id,
    }

    started = time.perf_counter()

    if body.stream:

        async def event_gen():
            yield sse_event(router_payload, event="router")
            full = []
            try:
                async for token in mm.stream(
                    selected,
                    built,
                    temperature=body.temperature,
                    max_tokens=body.max_tokens,
                    timeout=settings.request_timeout_seconds,
                ):
                    if await request.is_disconnected():
                        break
                    full.append(token)
                    yield sse_event(chat_chunk(selected, token))
                yield sse_event(chat_chunk(selected, "", finish_reason="stop"))
                yield "data: [DONE]\n\n"
            except Exception as exc:
                logger.exception("stream error")
                yield sse_event({"error": str(exc)}, event="error")
                return
            content = "".join(full)
            latency = (time.perf_counter() - started) * 1000
            await db.add_message(
                conversation_id,
                "assistant",
                content,
                model=selected,
                routing_mode=body.routing_mode.value,
                memories_used=memories_used,
            )
            await db.record_usage(
                model=selected,
                origin="local" if is_local else "api",
                is_local=is_local,
                latency_ms=latency,
            )

        return StreamingResponse(event_gen(), media_type="text/event-stream")

    try:
        result = await mm.generate(
            selected,
            built,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            timeout=settings.request_timeout_seconds,
        )
    except Exception as exc:
        logger.exception("generate error")
        raise HTTPException(502, detail=str(exc)) from exc

    content = result.get("content", "")
    usage_raw = result.get("usage") or {}
    latency = (time.perf_counter() - started) * 1000
    await db.add_message(
        conversation_id,
        "assistant",
        content,
        model=selected,
        routing_mode=body.routing_mode.value,
        memories_used=memories_used,
    )
    await db.record_usage(
        model=selected,
        origin="local" if is_local else "api",
        is_local=is_local,
        latency_ms=latency,
        input_tokens=usage_raw.get("prompt_tokens"),
        output_tokens=usage_raw.get("completion_tokens"),
        total_tokens=usage_raw.get("total_tokens"),
    )

    usage = None
    if any(usage_raw.get(k) is not None for k in ("prompt_tokens", "completion_tokens", "total_tokens")):
        usage = UsageInfo(
            prompt_tokens=usage_raw.get("prompt_tokens"),
            completion_tokens=usage_raw.get("completion_tokens"),
            total_tokens=usage_raw.get("total_tokens"),
        )

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
        created=int(time.time()),
        model=selected,
        choices=[
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        usage=usage,
        router=RouterChoice(**{k: router_payload[k] for k in (
            "selected_model", "mode", "task_type", "location", "display_name", "reason", "status"
        )}),
        memories_used=memories_used,
        memory_suggestions=suggestions if settings.memory_ask_before_save else [],
        conversation_id=conversation_id,
    )
