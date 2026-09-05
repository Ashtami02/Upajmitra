"""
Day 3: Lightweight persistence for farm profiles using SQLite (stdlib --
zero extra dependencies). Swap for Postgres later by changing only this
file's connection logic; the API in main.py doesn't need to change.
"""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "upajmitra.db"


@contextmanager
def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS farm_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                profile_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_profile(name: str, profile: dict) -> int:
    with _get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO farm_profiles (name, profile_json) VALUES (?, ?)",
            (name, json.dumps(profile)),
        )
        return cur.lastrowid


def list_profiles() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, created_at FROM farm_profiles ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_profile(profile_id: int) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, profile_json, created_at FROM farm_profiles WHERE id = ?",
            (profile_id,),
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["profile"] = json.loads(result.pop("profile_json"))
        return result


def delete_profile(profile_id: int) -> bool:
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM farm_profiles WHERE id = ?", (profile_id,))
        return cur.rowcount > 0
