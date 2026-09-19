"""Privacy filter before sending context to external APIs."""

from __future__ import annotations

from typing import Any


class PrivacyFilter:
    def filter_for_external(
        self,
        messages: list[dict[str, str]],
        memories: list[dict[str, Any]],
        allow_memory: bool,
    ) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
        """Never send the full memory base. Only allow filtered, necessary context."""
        if not allow_memory:
            # Strip memory-injected system blocks that start with our marker
            filtered = []
            for m in messages:
                content = m.get("content", "")
                if m.get("role") == "system" and content.startswith("Memórias relevantes"):
                    continue
                filtered.append(m)
            return filtered, []
        # Cap memories to top few already retrieved
        return messages, memories[:3]

    def sanitize_log_content(self, text: str, max_len: int = 120) -> str:
        return (text or "")[:max_len]
