"""App utilities."""

from __future__ import annotations


def truncate(text: str, n: int = 80) -> str:
    text = text or ""
    return text if len(text) <= n else text[: n - 1] + "…"
