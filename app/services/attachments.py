"""Attachment picking helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

ALLOWED_EXTS = {".txt", ".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp"}


def is_allowed(path: str) -> bool:
    return Path(path).suffix.lower() in ALLOWED_EXTS


def basename(path: str) -> str:
    return Path(path).name
