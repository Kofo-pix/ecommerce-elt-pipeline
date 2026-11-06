"""TRANSFORM: run versioned SQL models in dependency order inside the warehouse."""
from __future__ import annotations

import sqlite3
import time

from .config import MART_MODELS, SQL_DIR, STAGING_MODELS
from .logger import get_logger

log = get_logger("transform")


def run_models(con: sqlite3.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    plan = [("staging", m) for m in STAGING_MODELS] + [("marts", m) for m in MART_MODELS]
    for layer, model in plan:
        sql = (SQL_DIR / layer / f"{model}.sql").read_text(encoding="utf-8")
        t0 = time.perf_counter()
        con.executescript(sql)
        n = con.execute(f"SELECT COUNT(*) FROM {model}").fetchone()[0]
        counts[model] = n
        log.info("%-8s %-20s %8d rows  (%.2fs)", layer, model, n, time.perf_counter() - t0)
    con.commit()
    return counts
