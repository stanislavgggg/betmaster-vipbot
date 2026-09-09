"""SQLite storage. Request state lives in the DB so a restart never loses a pending upload."""

from __future__ import annotations

import time
from dataclasses import dataclass

import aiosqlite

AWAITING = "awaiting_screenshot"
PENDING = "pending_review"
APPROVED = "approved"
REJECTED = "rejected"
CANCELLED = "cancelled"

OPEN_STATUSES = (AWAITING, PENDING)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    first_name  TEXT,
    source      TEXT,
    region      TEXT,
    created_at  INTEGER NOT NULL,
    vip_until   INTEGER,
    vip_active  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS requests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    region        TEXT NOT NULL,
    brand_code    TEXT NOT NULL,
    status        TEXT NOT NULL,
    photo_file_id TEXT,
    admin_chat_id INTEGER,
    admin_msg_id  INTEGER,
    created_at    INTEGER NOT NULL,
    decided_at    INTEGER,
    decided_by    INTEGER
);

CREATE INDEX IF NOT EXISTS idx_requests_user   ON requests(user_id, status);
CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status);
"""


@dataclass
class Request:
    id: int
    user_id: int
    region: str
    brand_code: str
    status: str
    photo_file_id: str | None
    admin_chat_id: int | None
    admin_msg_id: int | None
    created_at: int
    decided_at: int | None
    decided_by: int | None


def now() -> int:
    return int(time.time())


class Database:
    def __init__(self, path: str):
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        return self._conn

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    # ---------- users ----------

    async def upsert_user(self, user_id: int, username: str | None,
                          first_name: str | None, source: str | None) -> None:
        await self.conn.execute(
            """
            INSERT INTO users (user_id, username, first_name, source, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name,
                source     = COALESCE(users.source, excluded.source)
            """,
            (user_id, username, first_name, source, now()),
        )
        await self.conn.commit()

    async def get_user(self, user_id: int) -> aiosqlite.Row | None:
        cur = await self.conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cur.fetchone()

    async def set_region(self, user_id: int, region: str) -> None:
        await self.conn.execute("UPDATE users SET region = ? WHERE user_id = ?", (region, user_id))
        await self.conn.commit()

    async def grant_vip(self, user_id: int, days: int) -> int:
        row = await self.get_user(user_id)
        base = now()
        if row and row["vip_until"] and row["vip_until"] > base:
            base = row["vip_until"]  # extend instead of overwriting
        until = base + days * 86400
        await self.conn.execute(
            "UPDATE users SET vip_until = ?, vip_active = 1 WHERE user_id = ?", (until, user_id)
        )
        await self.conn.commit()
        return until

    async def expired_vips(self) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT * FROM users WHERE vip_active = 1 AND vip_until IS NOT NULL AND vip_until < ?",
            (now(),),
        )
        return list(await cur.fetchall())

    async def deactivate_vip(self, user_id: int) -> None:
        await self.conn.execute("UPDATE users SET vip_active = 0 WHERE user_id = ?", (user_id,))
        await self.conn.commit()

    async def all_user_ids(self) -> list[int]:
        cur = await self.conn.execute("SELECT user_id FROM users")
        return [r["user_id"] for r in await cur.fetchall()]

    # ---------- requests ----------

    async def create_request(self, user_id: int, region: str, brand_code: str) -> int:
        cur = await self.conn.execute(
            """
            INSERT INTO requests (user_id, region, brand_code, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, region, brand_code, AWAITING, now()),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def get_request(self, request_id: int) -> Request | None:
        cur = await self.conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,))
        row = await cur.fetchone()
        return Request(**dict(row)) if row else None

    async def open_requests(self, user_id: int) -> list[Request]:
        cur = await self.conn.execute(
            "SELECT * FROM requests WHERE user_id = ? AND status IN (?, ?) ORDER BY id",
            (user_id, AWAITING, PENDING),
        )
        return [Request(**dict(r)) for r in await cur.fetchall()]

    async def next_awaiting(self, user_id: int) -> Request | None:
        cur = await self.conn.execute(
            "SELECT * FROM requests WHERE user_id = ? AND status = ? ORDER BY id LIMIT 1",
            (user_id, AWAITING),
        )
        row = await cur.fetchone()
        return Request(**dict(row)) if row else None

    async def brand_request(self, user_id: int, region: str, brand_code: str,
                            statuses: tuple[str, ...]) -> Request | None:
        placeholders = ",".join("?" * len(statuses))
        cur = await self.conn.execute(
            f"""SELECT * FROM requests
                WHERE user_id = ? AND region = ? AND brand_code = ? AND status IN ({placeholders})
                ORDER BY id DESC LIMIT 1""",
            (user_id, region, brand_code, *statuses),
        )
        row = await cur.fetchone()
        return Request(**dict(row)) if row else None

    async def attach_photo(self, request_id: int, file_id: str) -> None:
        await self.conn.execute(
            "UPDATE requests SET photo_file_id = ?, status = ? WHERE id = ?",
            (file_id, PENDING, request_id),
        )
        await self.conn.commit()

    async def set_admin_message(self, request_id: int, chat_id: int, msg_id: int) -> None:
        await self.conn.execute(
            "UPDATE requests SET admin_chat_id = ?, admin_msg_id = ? WHERE id = ?",
            (chat_id, msg_id, request_id),
        )
        await self.conn.commit()

    async def decide(self, request_id: int, status: str, admin_id: int) -> None:
        await self.conn.execute(
            "UPDATE requests SET status = ?, decided_at = ?, decided_by = ? WHERE id = ?",
            (status, now(), admin_id, request_id),
        )
        await self.conn.commit()

    async def cancel_open(self, user_id: int) -> int:
        cur = await self.conn.execute(
            "UPDATE requests SET status = ?, decided_at = ? WHERE user_id = ? AND status = ?",
            (CANCELLED, now(), user_id, AWAITING),
        )
        await self.conn.commit()
        return cur.rowcount or 0

    async def stats(self) -> dict[str, int]:
        out: dict[str, int] = {}
        cur = await self.conn.execute("SELECT COUNT(*) AS c FROM users")
        out["users"] = (await cur.fetchone())["c"]
        cur = await self.conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE created_at > ?", (now() - 86400,)
        )
        out["users_24h"] = (await cur.fetchone())["c"]
        cur = await self.conn.execute("SELECT COUNT(*) AS c FROM users WHERE vip_active = 1")
        out["vip_active"] = (await cur.fetchone())["c"]
        cur = await self.conn.execute("SELECT status, COUNT(*) AS c FROM requests GROUP BY status")
        for row in await cur.fetchall():
            out[row["status"]] = row["c"]
        return out

    async def brand_breakdown(self) -> list[tuple[str, str, int, int]]:
        cur = await self.conn.execute(
            """
            SELECT region, brand_code,
                   COUNT(*) AS total,
                   SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved
            FROM requests
            GROUP BY region, brand_code
            ORDER BY total DESC
            """
        )
        return [(r["region"], r["brand_code"], r["total"], r["approved"] or 0)
                for r in await cur.fetchall()]
