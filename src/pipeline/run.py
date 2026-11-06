"""CLI entry point.

    python -m pipeline.run all --days 30
    python -m pipeline.run extract|load|transform|quality
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime, timezone

from . import extract, load, quality, transform
from .config import DB_PATH, RAW_DIR
from .logger import get_logger
from .warehouse import connect

log = get_logger("run")


def _record_run(con, stage: str, status: str, seconds: float, detail: str = "") -> None:
    con.execute(
        """CREATE TABLE IF NOT EXISTS meta_pipeline_runs (
               run_at TEXT, stage TEXT, status TEXT, duration_s REAL, detail TEXT)"""
    )
    con.execute(
        "INSERT INTO meta_pipeline_runs VALUES (?,?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(timespec="seconds"), stage, status, round(seconds, 3), detail),
    )
    con.commit()


def _stage(con, name: str, fn):
    t0 = time.perf_counter()
    try:
        result = fn()
        _record_run(con, name, "success", time.perf_counter() - t0, str(result)[:500])
        return result
    except Exception as exc:
        _record_run(con, name, "failed", time.perf_counter() - t0, repr(exc)[:500])
        raise


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="E-commerce ELT pipeline")
    p.add_argument("command", choices=["extract", "load", "transform", "quality", "all"])
    p.add_argument("--start-date", default="2025-01-01", help="first partition date (YYYY-MM-DD)")
    p.add_argument("--days", type=int, default=30, help="number of daily partitions to generate")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)
    start = date.fromisoformat(args.start_date)

    with connect() as con:
        steps = {
            "extract": lambda: extract.generate_raw_data(start, args.days, args.seed, RAW_DIR),
            "load": lambda: load.load_raw(con, RAW_DIR),
            "transform": lambda: transform.run_models(con),
            "quality": lambda: quality.run_checks(con) and "all error-level checks passed",
        }
        order = list(steps) if args.command == "all" else [args.command]
        try:
            for name in order:
                log.info("=== %s ===", name.upper())
                _stage(con, name, steps[name])
        except quality.DataQualityError as exc:
            log.error(str(exc))
            return 1
    log.info("Done. Warehouse: %s", DB_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
