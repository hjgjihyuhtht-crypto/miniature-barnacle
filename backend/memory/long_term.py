"""Long-term persistent memory (SQLite)."""

from __future__ import annotations

from typing import Any, Optional

from backend.database import Database, new_id, utcnow
from backend.memory.embeddings import EmbeddingProvider, pack_embedding


class LongTermMemory:
    def __init__(self, db: Database, embeddings: EmbeddingProvider):
        self.db = db
        self.embeddings = embeddings

    async def create(
        self,
        user_id: str,
        type: str,
        content: str,
        source: str = "user",
        importance: float = 0.5,
    ) -> dict[str, Any]:
        mid = new_id()
        now = utcnow()
        await self.db.execute(
            """INSERT INTO memories
               (id, user_id, type, content, source, importance, created_at, updated_at, last_used_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (mid, user_id, type, content, source, importance, now, now, None),
        )
        vec = await self.embeddings.embed(content)
        await self.db.execute(
            "INSERT OR REPLACE INTO memory_embeddings (memory_id, embedding, dim) VALUES (?,?,?)",
            (mid, pack_embedding(vec), len(vec)),
        )
        return {
            "id": mid,
            "user_id": user_id,
            "type": type,
            "content": content,
            "source": source,
            "importance": importance,
            "created_at": now,
            "updated_at": now,
            "last_used_at": None,
        }

    async def update(self, memory_id: str, **fields: Any) -> Optional[dict[str, Any]]:
        row = await self.db.fetchone("SELECT * FROM memories WHERE id=?", (memory_id,))
        if not row:
            return None
        type_ = fields.get("type", row["type"])
        content = fields.get("content", row["content"])
        importance = fields.get("importance", row["importance"])
        now = utcnow()
        await self.db.execute(
            "UPDATE memories SET type=?, content=?, importance=?, updated_at=? WHERE id=?",
            (type_, content, importance, now, memory_id),
        )
        if content != row["content"]:
            vec = await self.embeddings.embed(content)
            await self.db.execute(
                "INSERT OR REPLACE INTO memory_embeddings (memory_id, embedding, dim) VALUES (?,?,?)",
                (memory_id, pack_embedding(vec), len(vec)),
            )
        return await self.get(memory_id)

    async def get(self, memory_id: str) -> Optional[dict[str, Any]]:
        row = await self.db.fetchone("SELECT * FROM memories WHERE id=?", (memory_id,))
        return dict(row) if row else None

    async def list(self, user_id: str, query: Optional[str] = None, limit: int = 100) -> list[dict[str, Any]]:
        if query:
            rows = await self.db.fetchall(
                "SELECT * FROM memories WHERE user_id=? AND content LIKE ? ORDER BY updated_at DESC LIMIT ?",
                (user_id, f"%{query}%", limit),
            )
        else:
            rows = await self.db.fetchall(
                "SELECT * FROM memories WHERE user_id=? ORDER BY updated_at DESC LIMIT ?",
                (user_id, limit),
            )
        return [dict(r) for r in rows]

    async def delete(self, memory_id: str) -> bool:
        await self.db.execute("DELETE FROM memory_embeddings WHERE memory_id=?", (memory_id,))
        cur = await self.db.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        return cur.rowcount > 0

    async def delete_all(self, user_id: str) -> int:
        rows = await self.db.fetchall("SELECT id FROM memories WHERE user_id=?", (user_id,))
        ids = [r["id"] for r in rows]
        for mid in ids:
            await self.db.execute("DELETE FROM memory_embeddings WHERE memory_id=?", (mid,))
        await self.db.execute("DELETE FROM memories WHERE user_id=?", (user_id,))
        return len(ids)

    async def touch(self, memory_id: str) -> None:
        await self.db.execute(
            "UPDATE memories SET last_used_at=? WHERE id=?",
            (utcnow(), memory_id),
        )
