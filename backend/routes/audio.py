"""Audio transcription routes."""

from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.auth import require_api_key
from backend.config import get_settings
from backend.models import TranscriptionResponse
from backend.services.speech_to_text import get_stt

router = APIRouter(prefix="/v1/audio", tags=["audio"])


@router.post("/transcriptions", response_model=TranscriptionResponse)
async def transcribe(
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
    _: str = Depends(require_api_key),
):
    settings = get_settings()
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    dest = settings.audio_dir / f"{uuid.uuid4().hex}{suffix}"
    async with aiofiles.open(dest, "wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            await out.write(chunk)
    try:
        result = await get_stt().transcribe(str(dest), language=language)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        try:
            dest.unlink(missing_ok=True)
        except Exception:
            pass
    return TranscriptionResponse(
        text=result.get("text", ""),
        language=result.get("language"),
        duration=result.get("duration"),
    )
