"""
Lightweight SQLite-backed storage for snapclip3.
Handles URL shortening records and click analytics.
"""
import sqlite3
import string
import random
import threading
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "snapclip3.db"
_lock = threading.Lock()


def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock:
        conn = _get_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                code TEXT PRIMARY KEY,
                target_url TEXT NOT NULL,
                is_custom INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                click_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                clicked_at TEXT NOT NULL,
                referrer TEXT
            )
            """
        )
        conn.commit()
        conn.close()


ALPHABET = string.ascii_letters + string.digits


def _random_code(length: int = 6) -> str:
    return "".join(random.choice(ALPHABET) for _ in range(length))


def create_short_link(target_url: str, custom_alias: str | None = None) -> str:
    with _lock:
        conn = _get_conn()
        try:
            if custom_alias:
                code = custom_alias
                is_custom = 1
                existing = conn.execute(
                    "SELECT 1 FROM links WHERE code = ?", (code,)
                ).fetchone()
                if existing:
                    raise ValueError(f"Alias '{code}' is already taken.")
            else:
                is_custom = 0
                code = _random_code()
                while conn.execute(
                    "SELECT 1 FROM links WHERE code = ?", (code,)
                ).fetchone():
                    code = _random_code()

            conn.execute(
                "INSERT INTO links (code, target_url, is_custom, created_at, click_count) "
                "VALUES (?, ?, ?, ?, 0)",
                (code, target_url, is_custom, datetime.utcnow().isoformat()),
            )
            conn.commit()
            return code
        finally:
            conn.close()


def get_link(code: str):
    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM links WHERE code = ?", (code,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def register_click(code: str, referrer: str | None = None):
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                "UPDATE links SET click_count = click_count + 1 WHERE code = ?",
                (code,),
            )
            conn.execute(
                "INSERT INTO clicks (code, clicked_at, referrer) VALUES (?, ?, ?)",
                (code, datetime.utcnow().isoformat(), referrer),
            )
            conn.commit()
        finally:
            conn.close()


def get_click_history(code: str):
    with _lock:
        conn = _get_conn()
        try:
            rows = conn.execute(
                "SELECT clicked_at, referrer FROM clicks WHERE code = ? ORDER BY clicked_at DESC",
                (code,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
