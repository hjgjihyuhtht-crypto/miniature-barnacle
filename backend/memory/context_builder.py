"""Build model context from short/long memory and attachments."""

from __future__ import annotations

from typing import Any, Optional


class ContextBuilder:
    def build(
        self,
        messages: list[dict[str, str]],
        memories: Optional[list[dict[str, Any]]] = None,
        summary: Optional[str] = None,
        attachment_texts: Optional[list[str]] = None,
        max_messages: int = 40,
    ) -> list[dict[str, str]]:
        system_parts: list[str] = []
        if memories:
            mem_lines = [f"- ({m.get('type')}) {m.get('content')}" for m in memories]
            system_parts.append(
                "Memórias relevantes do usuário (use quando útil, não invente):\n"
                + "\n".join(mem_lines)
            )
        if summary:
            system_parts.append(f"Resumo do histórico anterior:\n{summary}")
        if attachment_texts:
            joined = "\n\n".join(attachment_texts[:5])
            system_parts.append(f"Conteúdo de anexos:\n{joined[:12000]}")

        out: list[dict[str, str]] = []
        if system_parts:
            out.append({"role": "system", "content": "\n\n".join(system_parts)})

        # Keep existing system messages from client, then recent turns
        for m in messages:
            if m.get("role") == "system":
                out.append({"role": "system", "content": m.get("content", "")})
        non_system = [m for m in messages if m.get("role") != "system"]
        out.extend(non_system[-max_messages:])
        return out
