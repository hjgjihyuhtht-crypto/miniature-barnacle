"""Retrieve relevant memories for a query."""

from __future__ import annotations

from typing import Any, Optional

from backend.database import Database
from backend.memory.embeddings import EmbeddingProvider, cosine, unpack_embedding


class MemoryRetrieval:
    def __init__(self, db: Database, embeddings: EmbeddingProvider):
        self.db = db
        self.embeddings = embeddings

    async def retrieve(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.25,
    ) -> list[dict[str, Any]]:
        qvec = await self.embeddings.embed(query)
        rows = await self.db.fetchall(
            """SELECT m.*, e.embedding FROM memories m
               JOIN memory_embeddings e ON e.memory_id = m.id
               WHERE m.user_id=?""",
            (user_id,),
        )
        scored: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            vec = unpack_embedding(row["embedding"])
            score = cosine(qvec, vec) + (0.1 * float(row["importance"]))
            if score >= min_score:
                item = {
                    "id": row["id"],
                    "type": row["type"],
                    "content": row["content"],
                    "importance": row["importance"],
                    "score": round(score, 4),
                }
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:top_k]]
