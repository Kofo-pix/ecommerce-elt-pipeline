"""LOAD: land source files into the warehouse *as-is* (all TEXT) with lineage columns.

ELT principle: no business logic here. Cleaning/typing happens in SQL in the transform step.

Idempotency: `meta_load_log` remembers every file already loaded, so re-running the
pipeline only ingests new partitions (incremental load) and never double-loads.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import RAW_DIR, SOURCES
from .logger import get_logger
from .warehouse import scalar

log = get_logger("load")


def _init(con: sqlite3.Connection) -> None:
    con.execute(
        """CREATE TABLE IF NOT EXISTS meta_load_log (
               file_path TEXT PRIMARY KEY, entity TEXT, row_count INTEGER, loaded_at TEXT)"""
    )
    for entity, (_, cols) in SOURCES.items():
        col_defs = ", ".join(f'"{c}" TEXT' for c in cols)
        con.execute(
            f"""CREATE TABLE IF NOT EXISTS raw_{entity} (
                    {col_defs}, _source_file TEXT, _loaded_at TEXT)"""
        )


def _read_rows(path: Path, columns: list[str]):
    if path.suffix == ".csv":
        with path.open(newline="", encoding="utf-8") as fh:
            for rec in csv.DictReader(fh):
                yield tuple(rec.get(c) for c in columns)
    else:  # jsonl
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                yield tuple(None if rec.get(c) is None else str(rec[c]) for c in columns)


def load_raw(con: sqlite3.Connection, raw_dir: Path = RAW_DIR) -> dict[str, int]:
    _init(con)
    loaded = {e: 0 for e in SOURCES}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for entity, (ext, cols) in SOURCES.items():
        placeholders = ", ".join("?" * (len(cols) + 2))
        for path in sorted((raw_dir / entity).glob(f"dt=*/{entity}.{ext}")):
            rel = str(path.relative_to(raw_dir))
            if scalar(con, "SELECT 1 FROM meta_load_log WHERE file_path = ?", (rel,)):
                continue  # already loaded
            rows = [r + (rel, now) for r in _read_rows(path, cols)]
            con.executemany(f"INSERT INTO raw_{entity} VALUES ({placeholders})", rows)
            con.execute(
                "INSERT INTO meta_load_log VALUES (?, ?, ?, ?)", (rel, entity, len(rows), now)
            )
            loaded[entity] += len(rows)
    con.commit()
    log.info("Loaded rows this run: %s", loaded)
    return loaded
