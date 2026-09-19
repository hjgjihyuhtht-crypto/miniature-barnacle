"""Conversation and attachment helpers."""

from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from backend.auth import get_user_id, require_api_key
from backend.config import get_settings
from backend.database import get_db, utcnow
from backend.services.attachments import detect_kind, extract_text

router = APIRouter(prefix="/v1", tags=["conversations"])


@router.get("/conversations")
async def list_conversations(request: Request, _: str = Depends(require_api_key)):
    user_id = get_user_id(request)
    rows = await get_db().fetchall(
        "SELECT * FROM conversations WHERE user_id=? ORDER BY updated_at DESC LIMIT 200",
        (user_id,),
    )
    return {"data": [dict(r) for r in rows]}


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(conversation_id: str, _: str = Depends(require_api_key)):
    messages = await get_db().list_messages(conversation_id)
    return {"data": messages}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, _: str = Depends(require_api_key)):
    db = get_db()
    await db.execute("DELETE FROM messages WHERE conversation_id=?", (conversation_id,))
    await db.execute("DELETE FROM conversation_summaries WHERE conversation_id=?", (conversation_id,))
    await db.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
    return {"deleted": True}


@router.post("/attachments")
async def upload_attachment(
    request: Request,
    file: UploadFile = File(...),
    conversation_id: str | None = Form(default=None),
    _: str = Depends(require_api_key),
):
    settings = get_settings()
    user_id = get_user_id(request)
    aid = str(uuid.uuid4())
    filename = file.filename or "upload.bin"
    kind = detect_kind(filename, file.content_type)
    dest = settings.uploads_dir / f"{aid}_{Path(filename).name}"
    size = 0
    async with aiofiles.open(dest, "wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.max_request_bytes:
                raise HTTPException(413, "File too large")
            await out.write(chunk)
    text = await extract_text(str(dest), kind)
    now = utcnow()
    await get_db().execute(
        """INSERT INTO attachments
           (id, conversation_id, user_id, filename, content_type, kind, path, extracted_text, size_bytes, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            aid,
            conversation_id,
            user_id,
            filename,
            file.content_type,
            kind,
            str(dest),
            text,
            size,
            now,
        ),
    )
    return {
        "id": aid,
        "filename": filename,
        "kind": kind,
        "size_bytes": size,
        "has_text": bool(text),
    }
