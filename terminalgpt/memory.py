from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path


class MemoryStore:
    """Small local SQLite memory store used for cross-run conversation continuity."""

    def __init__(self, path: str):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS facts (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                """
            )

    def add_message(self, role: str, content: str) -> None:
        # Persist only user/assistant turns. Tool messages need tool_call_id metadata
        # to be safely replayed to an OpenAI-compatible API.
        if role not in {"user", "assistant"} or not content.strip():
            return
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO messages(role, content, created_at) VALUES (?, ?, ?)",
                (role, content, time.time()),
            )
            db.execute(
                "DELETE FROM messages WHERE id NOT IN "
                "(SELECT id FROM messages ORDER BY id DESC LIMIT 80)"
            )

    def recent_messages(self, limit: int = 24) -> list[dict[str, str]]:
        with sqlite3.connect(self.path) as db:
            rows = db.execute(
                "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?",
                (max(1, limit),),
            ).fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]

    def set_fact(self, key: str, value: str) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO facts(key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, value, time.time()),
            )

    def facts(self) -> dict[str, str]:
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT key, value FROM facts ORDER BY key").fetchall()
        return {key: value for key, value in rows}

    def clear(self) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM messages")
            db.execute("DELETE FROM facts")

    def prompt_context(self, recent_limit: int = 24) -> list[dict[str, str]]:
        facts = self.facts()
        messages = self.recent_messages(recent_limit)
        context: list[dict[str, str]] = []
        if facts:
            context.append(
                {
                    "role": "system",
                    "content": "Known local user/environment facts:\n"
                    + json.dumps(facts, ensure_ascii=False, indent=2),
                }
            )
        context.extend(messages)
        return context
