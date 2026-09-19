"""Pydantic request/response models for NEXUS AI."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class RoutingMode(str, Enum):
    AUTO = "auto"
    LOCAL_ONLY = "local_only"
    ECONOMY = "economy"
    MANUAL = "manual"


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str = "auto"
    messages: list[ChatMessage]
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=32768)
    stream: bool = False
    conversation_id: Optional[str] = None
    routing_mode: RoutingMode = RoutingMode.AUTO
    pin_model: bool = False
    use_for_this_message: Optional[str] = None
    memory_enabled: Optional[bool] = None
    allow_external_apis: Optional[bool] = None
    attachment_ids: list[str] = Field(default_factory=list)

    @field_validator("messages")
    @classmethod
    def non_empty_messages(cls, value: list[ChatMessage]) -> list[ChatMessage]:
        if not value:
            raise ValueError("messages must not be empty")
        return value


class UsageInfo(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class RouterChoice(BaseModel):
    selected_model: str
    mode: str
    task_type: str
    location: str
    display_name: str
    reason: str
    status: str = "ok"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[dict[str, Any]]
    usage: Optional[UsageInfo] = None
    router: Optional[RouterChoice] = None
    memories_used: list[dict[str, Any]] = Field(default_factory=list)
    memory_suggestions: list[dict[str, Any]] = Field(default_factory=list)
    conversation_id: Optional[str] = None


class RouterChooseRequest(BaseModel):
    model: str = "auto"
    messages: list[ChatMessage] = Field(default_factory=list)
    routing_mode: RoutingMode = RoutingMode.AUTO
    allow_external_apis: Optional[bool] = None
    attachment_kinds: list[str] = Field(default_factory=list)


class RouterChooseResponse(BaseModel):
    selected_model: str
    mode: str
    task_type: str
    location: str
    display_name: str
    reason: str


class MemoryCreate(BaseModel):
    type: Literal[
        "preference",
        "project",
        "fact",
        "instruction",
        "context",
        "conversation_summary",
    ]
    content: str
    source: str = "user"
    importance: float = Field(default=0.5, ge=0.0, le=1.0)


class MemoryUpdate(BaseModel):
    type: Optional[str] = None
    content: Optional[str] = None
    importance: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class MemoryOut(BaseModel):
    id: str
    user_id: str
    type: str
    content: str
    source: str
    importance: float
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime] = None


class TranscriptionResponse(BaseModel):
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None


class HealthResponse(BaseModel):
    backend: str
    llama: str
    qwen: str
    whisper: str
    openai: str
    gemini: str
    claude: str
    memory: str
    resources: dict[str, Any] = Field(default_factory=dict)
