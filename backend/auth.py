"""Authentication and security helpers."""

from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import Settings, get_settings

logger = logging.getLogger("nexus.auth")
security = HTTPBearer(auto_error=False)

_SENSITIVE_KEYS = re.compile(
    r"(authorization|api[_-]?key|hf_token|anthropic|openai|gemini|openrouter|bearer)",
    re.IGNORECASE,
)


def sanitize_for_log(value: str, max_len: int = 200) -> str:
    text = value or ""
    if _SENSITIVE_KEYS.search(text):
        return "[REDACTED]"
    return text[:max_len]


async def require_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    settings: Settings = Depends(get_settings),
) -> str:
    expected = (settings.nexus_api_key or "").strip()
    if not expected or expected == "change-me-to-a-long-random-secret":
        # Still require a matching key; warn in logs without revealing it.
        logger.warning("NEXUS_API_KEY is using the insecure default value")

    token = None
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    elif "x-api-key" in request.headers:
        token = request.headers.get("x-api-key")

    if not token or token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


def get_user_id(request: Request) -> str:
    """Single-user personal platform; optional X-User-Id for future multi-device sync."""
    return request.headers.get("x-user-id", "default").strip() or "default"
