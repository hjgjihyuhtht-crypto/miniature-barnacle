"""Local data models / helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AppSettings:
    server_url: str = "https://seu-dominio.com"
    api_key: str = ""
    routing_mode: str = "auto"
    selected_model: str = "auto"
    memory_enabled: bool = True
    learn_preferences: bool = True
    ask_before_save: bool = True
    allow_external_apis: bool = True
    allow_memory_in_external: bool = False
    prefer_local_transcription: bool = True
    theme: str = "dark"


@dataclass
class ChatBubble:
    role: str
    content: str
    model: Optional[str] = None
    router_info: Optional[dict[str, Any]] = None
    memories_used: list[dict[str, Any]] = field(default_factory=list)
