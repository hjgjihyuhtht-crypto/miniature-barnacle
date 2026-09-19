"""Speech-to-text providers (faster-whisper local)."""

from __future__ import annotations

import abc
import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Optional

from backend.config import Settings, get_settings

logger = logging.getLogger("nexus.stt")


class SpeechToTextProvider(abc.ABC):
    @abc.abstractmethod
    async def transcribe(self, audio_path: str, **kwargs: Any) -> dict[str, Any]: ...

    @abc.abstractmethod
    async def health(self) -> dict[str, Any]: ...


class FasterWhisperProvider(SpeechToTextProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None

    def _pick_device(self) -> str:
        if self.settings.whisper_device != "auto":
            return self.settings.whisper_device
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    def _pick_compute(self, device: str) -> str:
        if self.settings.whisper_compute_type != "auto":
            return self.settings.whisper_compute_type
        return "float16" if device == "cuda" else "int8"

    async def _ensure(self) -> None:
        if self._model is not None:
            return

        def _load() -> None:
            from faster_whisper import WhisperModel

            device = self._pick_device()
            compute = self._pick_compute(device)
            self._model = WhisperModel(
                self.settings.whisper_model,
                device=device,
                compute_type=compute,
            )

        await asyncio.to_thread(_load)

    async def transcribe(self, audio_path: str, **kwargs: Any) -> dict[str, Any]:
        await self._ensure()
        language = kwargs.get("language")

        def _run() -> dict[str, Any]:
            assert self._model is not None
            segments, info = self._model.transcribe(audio_path, language=language)
            texts = []
            for seg in segments:
                texts.append(seg.text.strip())
            return {
                "text": " ".join(t for t in texts if t).strip(),
                "language": getattr(info, "language", None),
                "duration": getattr(info, "duration", None),
            }

        return await asyncio.to_thread(_run)

    async def health(self) -> dict[str, Any]:
        try:
            import faster_whisper  # noqa: F401

            return {"status": "ok", "provider": "faster_whisper", "model": self.settings.whisper_model}
        except Exception:
            return {"status": "offline", "provider": "faster_whisper"}


class NullSTTProvider(SpeechToTextProvider):
    async def transcribe(self, audio_path: str, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("Speech-to-text provider not available. Install faster-whisper.")

    async def health(self) -> dict[str, Any]:
        return {"status": "not_configured", "provider": "none"}


def create_stt_provider(settings: Optional[Settings] = None) -> SpeechToTextProvider:
    settings = settings or get_settings()
    preferred = (settings.stt_provider or "auto").lower()
    if preferred == "none":
        return NullSTTProvider()
    try:
        import faster_whisper  # noqa: F401

        if preferred in ("auto", "faster_whisper"):
            return FasterWhisperProvider(settings)
    except Exception:
        logger.info("faster-whisper not installed")
    return NullSTTProvider()


_stt: Optional[SpeechToTextProvider] = None


def get_stt() -> SpeechToTextProvider:
    global _stt
    if _stt is None:
        _stt = create_stt_provider()
    return _stt
