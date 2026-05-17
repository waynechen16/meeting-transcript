"""Unit tests for db.py — all use an in-memory SQLite database."""

import pytest_asyncio

from db import Database


@pytest_asyncio.fixture
async def db():
    database = Database(":memory:")
    await database.init()
    yield database
    await database.close()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


async def test_init_creates_sessions_table(db: Database) -> None:
    async with db._db.execute(  # type: ignore[union-attr]
        "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
    ) as cur:
        assert await cur.fetchone() is not None


async def test_init_creates_segments_table(db: Database) -> None:
    async with db._db.execute(  # type: ignore[union-attr]
        "SELECT name FROM sqlite_master WHERE type='table' AND name='segments'"
    ) as cur:
        assert await cur.fetchone() is not None


async def test_init_creates_fts_table(db: Database) -> None:
    async with db._db.execute(  # type: ignore[union-attr]
        "SELECT name FROM sqlite_master WHERE type='table' AND name='segments_fts'"
    ) as cur:
        assert await cur.fetchone() is not None


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


async def test_create_session(db: Database) -> None:
    await db.create_session("sess-1", 1000.0)
    async with db._db.execute(  # type: ignore[union-attr]
        "SELECT started_at, ended_at FROM sessions WHERE id = 'sess-1'"
    ) as cur:
        row = await cur.fetchone()
    assert row is not None
    assert row[0] == 1000.0
    assert row[1] is None  # not ended yet


async def test_end_session(db: Database) -> None:
    await db.create_session("sess-1", 1000.0)
    await db.end_session("sess-1", 1060.0)
    async with db._db.execute(  # type: ignore[union-attr]
        "SELECT ended_at FROM sessions WHERE id = 'sess-1'"
    ) as cur:
        row = await cur.fetchone()
    assert row is not None
    assert row[0] == 1060.0


# ---------------------------------------------------------------------------
# Segments
# ---------------------------------------------------------------------------


async def test_save_segment(db: Database) -> None:
    await db.create_session("sess-1", 0.0)
    await db.save_segment(
        session_id="sess-1",
        segment_id="seg-uuid",
        started_at=1.5,
        ended_at=3.2,
        text="你好世界",
    )
    async with db._db.execute(  # type: ignore[union-attr]
        "SELECT session_id, started_at, ended_at, text FROM segments WHERE segment_id = 'seg-uuid'"
    ) as cur:
        row = await cur.fetchone()
    assert row is not None
    assert row[0] == "sess-1"
    assert row[1] == 1.5
    assert row[2] == 3.2
    assert row[3] == "你好世界"


async def test_save_segment_null_ended_at(db: Database) -> None:
    await db.create_session("sess-1", 0.0)
    await db.save_segment(
        session_id="sess-1",
        segment_id="seg-2",
        started_at=5.0,
        ended_at=None,
        text="測試",
    )
    async with db._db.execute(  # type: ignore[union-attr]
        "SELECT ended_at FROM segments WHERE segment_id = 'seg-2'"
    ) as cur:
        row = await cur.fetchone()
    assert row is not None
    assert row[0] is None


async def test_multiple_segments_accumulate(db: Database) -> None:
    await db.create_session("sess-1", 0.0)
    for i in range(3):
        await db.save_segment(
            session_id="sess-1",
            segment_id=f"seg-{i}",
            started_at=float(i),
            ended_at=float(i + 1),
            text=f"line {i}",
        )
    async with db._db.execute(  # type: ignore[union-attr]
        "SELECT COUNT(*) FROM segments WHERE session_id = 'sess-1'"
    ) as cur:
        row = await cur.fetchone()
    assert row is not None
    assert row[0] == 3


# ---------------------------------------------------------------------------
# FTS5
# ---------------------------------------------------------------------------


async def test_fts_trigger_populates_index(db: Database) -> None:
    """INSERT into segments should auto-populate segments_fts via trigger."""
    await db.create_session("sess-1", 0.0)
    await db.save_segment(
        session_id="sess-1",
        segment_id="seg-fts",
        started_at=0.0,
        ended_at=2.0,
        text="今天天氣很好",
    )
    # Verify the trigger fired — FTS index should have exactly one row.
    # (Full-text search of Chinese requires a trigram tokenizer which is
    #  not guaranteed to be available; we only assert the row was inserted.)
    async with db._db.execute("SELECT COUNT(*) FROM segments_fts") as cur:  # type: ignore[union-attr]
        row = await cur.fetchone()
    assert row is not None
    assert row[0] == 1
