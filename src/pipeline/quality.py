"""DATA QUALITY: declarative checks. Each query returns the number of violating rows (0 = pass).

severity="error" -> pipeline fails.   severity="warn" -> recorded, pipeline continues.
Results are persisted in `meta_dq_results` for trend analysis / dashboards.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from .logger import get_logger

log = get_logger("quality")


@dataclass(frozen=True)
class Check:
    name: str
    sql: str
    severity: str = "error"


CHECKS = [
    Check("raw_orders_not_empty", "SELECT CASE WHEN COUNT(*)=0 THEN 1 ELSE 0 END FROM raw_orders"),
    Check("stg_customers_pk_unique", "SELECT COUNT(*)-COUNT(DISTINCT customer_id) FROM stg_customers"),
    Check("stg_orders_pk_unique", "SELECT COUNT(*)-COUNT(DISTINCT order_id) FROM stg_orders"),
    Check("stg_order_items_pk_unique", "SELECT COUNT(*)-COUNT(DISTINCT order_item_id) FROM stg_order_items"),
    Check("dim_customers_key_unique", "SELECT COUNT(*)-COUNT(DISTINCT customer_key) FROM dim_customers"),
    Check("dim_products_key_unique", "SELECT COUNT(*)-COUNT(DISTINCT product_key) FROM dim_products"),
    Check("fact_sales_pk_unique", "SELECT COUNT(*)-COUNT(DISTINCT order_item_id) FROM fact_sales"),
    Check(
        "fact_sales_no_null_keys",
        "SELECT COUNT(*) FROM fact_sales WHERE customer_key IS NULL OR product_key IS NULL OR date_key IS NULL",
    ),
    Check("fact_sales_quantity_positive", "SELECT COUNT(*) FROM fact_sales WHERE quantity <= 0"),
    Check(
        "fact_sales_net_between_0_and_gross",
        "SELECT COUNT(*) FROM fact_sales WHERE net_amount < 0 OR net_amount > gross_amount + 0.01",
    ),
    Check(
        "fact_sales_date_in_dim_date",
        "SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_date d USING (date_key) WHERE d.date_key IS NULL",
    ),
    Check(
        "reconciliation_staging_vs_fact_rowcount",
        "SELECT ABS((SELECT COUNT(*) FROM stg_order_items) - (SELECT COUNT(*) FROM fact_sales))",
    ),
    Check(
        "orders_have_known_customer",
        """SELECT COUNT(*) FROM stg_orders o
           LEFT JOIN stg_customers c USING (customer_id) WHERE c.customer_id IS NULL""",
        "warn",
    ),
    Check("customers_missing_valid_email", "SELECT COUNT(*) FROM stg_customers WHERE email IS NULL", "warn"),
    Check(
        "rejected_items_under_5pct",
        """SELECT CASE WHEN (SELECT COUNT(*) FROM rejected_order_items) * 1.0
                         / NULLIF((SELECT COUNT(*) FROM raw_order_items), 0) > 0.05
                    THEN 1 ELSE 0 END""",
        "warn",
    ),
]


class DataQualityError(RuntimeError):
    pass


def run_checks(con: sqlite3.Connection) -> list[dict]:
    con.execute(
        """CREATE TABLE IF NOT EXISTS meta_dq_results (
               run_at TEXT, check_name TEXT, severity TEXT, violations INTEGER, passed INTEGER)"""
    )
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    results, failed = [], []
    for chk in CHECKS:
        violations = con.execute(chk.sql).fetchone()[0] or 0
        passed = violations == 0
        results.append({"check": chk.name, "severity": chk.severity, "violations": violations, "passed": passed})
        con.execute(
            "INSERT INTO meta_dq_results VALUES (?,?,?,?,?)",
            (now, chk.name, chk.severity, violations, int(passed)),
        )
        icon = "PASS" if passed else ("FAIL" if chk.severity == "error" else "WARN")
        log.info("[%s] %-45s violations=%d", icon, chk.name, violations)
        if not passed and chk.severity == "error":
            failed.append(chk.name)
    con.commit()
    if failed:
        raise DataQualityError(f"Data quality checks failed: {failed}")
    return results
