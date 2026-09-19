"""Attachment text extraction utilities."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("nexus.attachments")

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".py", ".js", ".ts", ".html", ".css"}


def detect_kind(filename: str, content_type: Optional[str] = None) -> str:
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXTS or (content_type and content_type.startswith("image/")):
        return "image"
    if ext == ".pdf" or content_type == "application/pdf":
        return "pdf"
    if ext == ".docx":
        return "docx"
    if ext in TEXT_EXTS:
        return "txt"
    return "file"


async def extract_text(path: str, kind: str) -> str:
    p = Path(path)
    try:
        if kind == "txt":
            return p.read_text(encoding="utf-8", errors="ignore")[:50000]
        if kind == "pdf":
            from pypdf import PdfReader

            reader = PdfReader(str(p))
            parts = []
            for page in reader.pages[:50]:
                parts.append(page.extract_text() or "")
            return "\n".join(parts)[:50000]
        if kind == "docx":
            import docx

            document = docx.Document(str(p))
            return "\n".join(para.text for para in document.paragraphs)[:50000]
        if kind == "image":
            return f"[Imagem anexada: {p.name}. Modelo com visão necessário para análise visual.]"
    except Exception as exc:
        logger.warning("Failed to extract %s: %s", path, exc)
        return ""
    return ""
