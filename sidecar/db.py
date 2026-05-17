"""SQLite persistence for meeting transcripts (Phase 1).

Uses aiosqlite for non-blocking async I/O.  Writes to ``segments`` are
fire-and-forget via ``asyncio.create_task()`` in main.py so they never block
the STT pipeline.

Schema
------
sessions     – one row per WebSocket connection (one recording session)
segments     – one row per ``is_final=True`` transcript event
segments_fts – FTS5 virtual table for full-text search (V2 readiness)
"""

from __future__ import annotations

from pathlib import Path

import aiosqlite

_DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    started_at  REAL NOT NULL,
    ended_at    REAL
);

CREATE TABLE IF NOT EXISTS segments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT    NOT NULL REFERENCES sessions(id),
    segment_id  TEXT    NOT NULL,
    started_at  REAL    NOT NULL,
    ended_at    REAL,
    text        TEXT    NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS segments_fts
    USING fts5(text, content=segments, content_rowid=id);

CREATE TRIGGER IF NOT EXISTS segments_ai
    AFTER INSERT ON segments BEGIN
        INSERT INTO segments_fts(rowid, text) VALUES (new.id, new.text);
    END;
"""

_MEMORY = ":memory:"


class Database:
    """Async SQLite wrapper.  Call ``await db.init()`` before use."""

    def __init__(self, path: str | Path = "data/transcripts.db") -> None:
        self._path: str | Path = path if str(path) == _MEMORY else Path(path)
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        if str(self._path) != _MEMORY:
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        await self._db.executescript(_DDL)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    async def create_session(self, session_id: str, started_at: float) -> None:
        assert self._db is not None
        await self._db.execute(
            "INSERT INTO sessions (id, started_at) VALUES (?, ?)",
            (session_id, started_at),
        )
        await self._db.commit()

    async def end_session(self, session_id: str, ended_at: float) -> None:
        assert self._db is not None
        await self._db.execute(
            "UPDATE sessions SET ended_at = ? WHERE id = ?",
            (ended_at, session_id),
        )
        await self._db.commit()

    async def save_segment(
        self,
        *,
        session_id: str,
        segment_id: str,
        started_at: float,
        ended_at: float | None,
        text: str,
    ) -> None:
        assert self._db is not None
        await self._db.execute(
            """INSERT INTO segments (session_id, segment_id, started_at, ended_at, text)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, segment_id, started_at, ended_at, text),
        )
        await self._db.commit()
