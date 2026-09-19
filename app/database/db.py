"""Local SQLite cache for the NEXUS AI Flet app."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocalDB:
    def __init__(self, path: Optional[str] = None):
        base = Path.home() / ".nexus-ai"
        base.mkdir(parents=True, exist_ok=True)
        self.path = Path(path) if path else base / "client.db"
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT,
                model TEXT,
                routing_mode TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                model TEXT,
                meta TEXT,
                created_at TEXT
            );
            """
        )
        self.conn.commit()

    def get_setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)",
            (key, value),
        )
        self.conn.commit()

    def upsert_conversation(self, conv: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO conversations (id, title, model, routing_mode, updated_at)
               VALUES (?,?,?,?,?)""",
            (
                conv["id"],
                conv.get("title", "Conversa"),
                conv.get("model"),
                conv.get("routing_mode"),
                conv.get("updated_at", _utcnow()),
            ),
        )
        self.conn.commit()

    def list_conversations(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        model: Optional[str] = None,
        meta: Optional[dict] = None,
    ) -> str:
        mid = str(uuid.uuid4())
        self.conn.execute(
            """INSERT INTO messages (id, conversation_id, role, content, model, meta, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (mid, conversation_id, role, content, model, json.dumps(meta or {}), _utcnow()),
        )
        self.conn.commit()
        return mid

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at ASC",
            (conversation_id,),
        ).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            try:
                item["meta"] = json.loads(item.get("meta") or "{}")
            except Exception:
                item["meta"] = {}
            result.append(item)
        return result
