"""Thin warehouse adapter. Swap this module to target DuckDB / Postgres / Snowflake."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import DB_PATH


@contextmanager
def connect(db_path: Path = DB_PATH):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def scalar(con: sqlite3.Connection, sql: str, params: tuple = ()):
    row = con.execute(sql, params).fetchone()
    return row[0] if row else None
