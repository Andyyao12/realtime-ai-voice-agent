from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS reservations (
    reference TEXT PRIMARY KEY,
    last_name TEXT NOT NULL,
    status TEXT NOT NULL,
    room_type TEXT NOT NULL,
    check_in TEXT NOT NULL,
    check_out TEXT NOT NULL,
    breakfast_included INTEGER NOT NULL CHECK (breakfast_included IN (0, 1))
);
CREATE TABLE IF NOT EXISTS service_requests (
    request_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    summary TEXT NOT NULL,
    requested_time TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

SEED_RESERVATIONS = (
    ("DEMO-2048", "Morgan", "confirmed", "Harbor View King", "2026-09-14", "2026-09-17", 1),
    ("DEMO-7315", "Rivera", "confirmed", "Courtyard Twin", "2026-10-03", "2026-10-05", 0),
)


def database_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("Only sqlite:/// DATABASE_URL values are supported")
    raw_path = database_url.removeprefix(prefix)
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def connect(database_url: str) -> sqlite3.Connection:
    path = database_path(database_url)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(database_url: str) -> None:
    with connect(database_url) as connection:
        connection.executescript(SCHEMA)
        connection.executemany(
            """
            INSERT OR IGNORE INTO reservations
            (reference, last_name, status, room_type, check_in, check_out, breakfast_included)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            SEED_RESERVATIONS,
        )


def find_reservation(database_url: str, reference: str, last_name: str) -> dict[str, Any] | None:
    with connect(database_url) as connection:
        row = connection.execute(
            """
            SELECT reference, status, room_type, check_in, check_out, breakfast_included
            FROM reservations
            WHERE reference = ? AND lower(last_name) = lower(?)
            """,
            (reference, last_name),
        ).fetchone()
    if row is None:
        return None
    return {
        "reference": row["reference"],
        "status": row["status"],
        "room_type": row["room_type"],
        "check_in": row["check_in"],
        "check_out": row["check_out"],
        "breakfast_included": bool(row["breakfast_included"]),
    }


def create_request(
    database_url: str,
    *,
    request_id: str,
    category: str,
    summary: str,
    requested_time: str | None,
    created_at: str,
) -> dict[str, Any]:
    with connect(database_url) as connection:
        connection.execute(
            """
            INSERT INTO service_requests
            (request_id, category, summary, requested_time, status, created_at)
            VALUES (?, ?, ?, ?, 'open', ?)
            """,
            (request_id, category, summary, requested_time, created_at),
        )
    return {
        "request_id": request_id,
        "category": category,
        "status": "open",
        "requested_time": requested_time,
        "created_at": created_at,
    }
