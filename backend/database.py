"""SQLite database layer for NEXUS AI."""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Optional

import aiosqlite

from backend.config import Settings, get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT 'Nova conversa',
    model TEXT,
    routing_mode TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    model TEXT,
    routing_mode TEXT,
    memories_used TEXT,
    is_transcription INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attachments (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT,
    kind TEXT,
    path TEXT NOT NULL,
    extracted_text TEXT,
    size_bytes INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    importance REAL NOT NULL DEFAULT 0.5,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_used_at TEXT
);

CREATE TABLE IF NOT EXISTS memory_embeddings (
    memory_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,
    dim INTEGER NOT NULL,
    FOREIGN KEY(memory_id) REFERENCES memories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS conversation_summaries (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    up_to_message_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS usage_stats (
    id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    origin TEXT NOT NULL,
    is_local INTEGER NOT NULL,
    latency_ms REAL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


class Database:
    def __init__(self, path: str):
        self.path = path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if not self._conn:
            raise RuntimeError("Database not connected")
        return self._conn

    async def execute(self, sql: str, params: tuple | list = ()) -> aiosqlite.Cursor:
        cur = await self.conn.execute(sql, params)
        await self.conn.commit()
        return cur

    async def fetchone(self, sql: str, params: tuple | list = ()) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute(sql, params)
        return await cur.fetchone()

    async def fetchall(self, sql: str, params: tuple | list = ()) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(sql, params)
        return await cur.fetchall()

    async def create_conversation(
        self,
        user_id: str,
        title: str = "Nova conversa",
        model: Optional[str] = None,
        routing_mode: Optional[str] = None,
    ) -> dict[str, Any]:
        cid = new_id()
        now = utcnow()
        await self.execute(
            "INSERT INTO conversations (id, user_id, title, model, routing_mode, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (cid, user_id, title, model, routing_mode, now, now),
        )
        return {
            "id": cid,
            "user_id": user_id,
            "title": title,
            "model": model,
            "routing_mode": routing_mode,
            "created_at": now,
            "updated_at": now,
        }

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        model: Optional[str] = None,
        routing_mode: Optional[str] = None,
        memories_used: Optional[list] = None,
        is_transcription: bool = False,
    ) -> dict[str, Any]:
        mid = new_id()
        now = utcnow()
        await self.execute(
            """INSERT INTO messages
               (id, conversation_id, role, content, model, routing_mode, memories_used, is_transcription, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                mid,
                conversation_id,
                role,
                content,
                model,
                routing_mode,
                json.dumps(memories_used or []),
                1 if is_transcription else 0,
                now,
            ),
        )
        await self.execute(
            "UPDATE conversations SET updated_at=? WHERE id=?",
            (now, conversation_id),
        )
        return {
            "id": mid,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "model": model,
            "created_at": now,
        }

    async def list_messages(self, conversation_id: str, limit: int = 100) -> list[dict[str, Any]]:
        rows = await self.fetchall(
            "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at ASC LIMIT ?",
            (conversation_id, limit),
        )
        return [dict(r) for r in rows]

    async def record_usage(
        self,
        model: str,
        origin: str,
        is_local: bool,
        latency_ms: Optional[float] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
    ) -> None:
        await self.execute(
            """INSERT INTO usage_stats
               (id, model, origin, is_local, latency_ms, input_tokens, output_tokens, total_tokens, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                new_id(),
                model,
                origin,
                1 if is_local else 0,
                latency_ms,
                input_tokens,
                output_tokens,
                total_tokens,
                utcnow(),
            ),
        )


_db: Optional[Database] = None


async def init_db(settings: Optional[Settings] = None) -> Database:
    global _db
    settings = settings or get_settings()
    settings.ensure_dirs()
    _db = Database(str(settings.db_path))
    await _db.connect()
    return _db


async def close_db() -> None:
    global _db
    if _db:
        await _db.close()
        _db = None


def get_db() -> Database:
    if not _db:
        raise RuntimeError("Database not initialized")
    return _db


@asynccontextmanager
async def db_session() -> AsyncIterator[Database]:
    yield get_db()
