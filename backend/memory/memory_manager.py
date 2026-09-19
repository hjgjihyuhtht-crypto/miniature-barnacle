"""Memory manager — orchestration of short/long memory and suggestions."""

from __future__ import annotations

import re
from typing import Any, Optional

from backend.config import Settings, get_settings
from backend.database import Database, get_db
from backend.memory.context_builder import ContextBuilder
from backend.memory.embeddings import create_embedding_provider
from backend.memory.long_term import LongTermMemory
from backend.memory.privacy import PrivacyFilter
from backend.memory.retrieval import MemoryRetrieval
from backend.memory.short_term import ShortTermMemory


_PREFERENCE_RE = re.compile(
    r"(prefiro|prefer[oê]|sempre responda|me chame|meu nome é|meu projeto|trabalho com)",
    re.IGNORECASE,
)
_FACT_RE = re.compile(
    r"(meu projeto se chama|eu moro|minha empresa|uso |trabalho no)",
    re.IGNORECASE,
)
_SKIP_RE = re.compile(
    r"^(qual|o que|como|when|what|who|where|capital|obrigado|oi|olá)\b",
    re.IGNORECASE,
)


class MemoryManager:
    def __init__(self, db: Optional[Database] = None, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.db = db or get_db()
        self.embeddings = create_embedding_provider(self.settings)
        self.short = ShortTermMemory()
        self.long = LongTermMemory(self.db, self.embeddings)
        self.retrieval = MemoryRetrieval(self.db, self.embeddings)
        self.context_builder = ContextBuilder()
        self.privacy = PrivacyFilter()

    async def relevant_memories(self, user_id: str, query: str) -> list[dict[str, Any]]:
        if not self.settings.memory_enabled:
            return []
        items = await self.retrieval.retrieve(user_id, query)
        for item in items:
            await self.long.touch(item["id"])
        return items

    def suggest_memories(self, user_message: str) -> list[dict[str, Any]]:
        text = (user_message or "").strip()
        if not text or len(text) < 12:
            return []
        if _SKIP_RE.search(text) and not _PREFERENCE_RE.search(text):
            return []
        suggestions = []
        if _PREFERENCE_RE.search(text):
            suggestions.append(
                {
                    "type": "preference",
                    "content": text,
                    "prompt": "🧠 Lembrar disso?",
                }
            )
        elif _FACT_RE.search(text):
            suggestions.append(
                {
                    "type": "fact",
                    "content": text,
                    "prompt": "🧠 Lembrar disso?",
                }
            )
        return suggestions

    async def build_messages(
        self,
        user_id: str,
        messages: list[dict[str, str]],
        conversation_id: Optional[str] = None,
        attachment_texts: Optional[list[str]] = None,
        for_external: bool = False,
        allow_memory_external: bool = False,
    ) -> tuple[list[dict[str, str]], list[dict[str, Any]], list[dict[str, Any]]]:
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = m.get("content", "")
                break
        memories = await self.relevant_memories(user_id, last_user) if self.settings.memory_enabled else []
        summary = None
        if conversation_id:
            row = await self.db.fetchone(
                "SELECT summary FROM conversation_summaries WHERE conversation_id=? ORDER BY created_at DESC LIMIT 1",
                (conversation_id,),
            )
            if row:
                summary = row["summary"]
        built = self.context_builder.build(
            messages,
            memories=memories,
            summary=summary,
            attachment_texts=attachment_texts,
        )
        if for_external:
            built, memories = self.privacy.filter_for_external(
                built, memories, allow_memory=allow_memory_external
            )
        suggestions = self.suggest_memories(last_user)
        return built, memories, suggestions


_memory: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    global _memory
    if _memory is None:
        _memory = MemoryManager()
    return _memory


def reset_memory_manager() -> None:
    global _memory
    _memory = None
