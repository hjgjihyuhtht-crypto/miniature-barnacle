"""Voice recording helpers (platform-dependent)."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Optional


class VoiceRecorder:
    """Records audio to a temporary wav/webm file when platform APIs allow it.

    On Android via Flet, prefer using AudioRecorder control when available.
    This class keeps a simple file-path contract for the UI layer.
    """

    def __init__(self) -> None:
        self.path: Optional[str] = None
        self.started_at: Optional[float] = None
        self.recording = False

    def start(self, path: Optional[str] = None) -> str:
        if not path:
            fd, path = tempfile.mkstemp(suffix=".wav", prefix="nexus_voice_")
            Path(path).write_bytes(b"")
            import os

            os.close(fd)
        self.path = path
        self.started_at = time.time()
        self.recording = True
        return path

    def elapsed(self) -> float:
        if not self.started_at:
            return 0.0
        return time.time() - self.started_at

    def stop(self) -> Optional[str]:
        self.recording = False
        return self.path
