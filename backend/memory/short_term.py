"""Short-term conversational memory."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ShortTermState:
    conversation_id: Optional[str] = None
    topic: Optional[str] = None
    recent_messages: list[dict[str, str]] = field(default_factory=list)
    attachments: list[dict[str, Any]] = field(default_factory=list)
    model: Optional[str] = None
    routing_mode: Optional[str] = None
    temp_preferences: dict[str, Any] = field(default_factory=dict)


class ShortTermMemory:
    def __init__(self, max_messages: int = 40):
        self.max_messages = max_messages
        self._states: dict[str, ShortTermState] = {}

    def get(self, conversation_id: str) -> ShortTermState:
        if conversation_id not in self._states:
            self._states[conversation_id] = ShortTermState(conversation_id=conversation_id)
        return self._states[conversation_id]

    def update_messages(self, conversation_id: str, messages: list[dict[str, str]]) -> ShortTermState:
        state = self.get(conversation_id)
        state.recent_messages = messages[-self.max_messages :]
        return state

    def set_model(self, conversation_id: str, model: str, routing_mode: str) -> None:
        state = self.get(conversation_id)
        state.model = model
        state.routing_mode = routing_mode

    def clear(self, conversation_id: str) -> None:
        self._states.pop(conversation_id, None)
