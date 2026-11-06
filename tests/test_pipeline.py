from datetime import date

import pytest

from pipeline import extract, load, quality, transform
from pipeline.warehouse import connect, scalar

START = date(2025, 1, 1)


@pytest.fixture()
def env(tmp_path):
    raw = tmp_path / "raw"
    extract.generate_raw_data(START, days=7, seed=1, raw_dir=raw)
    db = tmp_path / "wh.db"
    return raw, db


def test_extract_is_deterministic(tmp_path):
    a = extract.generate_raw_data(START, 3, seed=7, raw_dir=tmp_path / "a")
    b = extract.generate_raw_data(START, 3, seed=7, raw_dir=tmp_path / "b")
    assert a == b
    fa = (tmp_path / "a/orders/dt=2025-01-01/orders.csv").read_text()
    fb = (tmp_path / "b/orders/dt=2025-01-01/orders.csv").read_text()
    assert fa == fb


def test_load_is_idempotent_and_incremental(env, tmp_path):
    raw, db = env
    with connect(db) as con:
        first = load.load_raw(con, raw)
        again = load.load_raw(con, raw)
        assert sum(first.values()) > 0
        assert sum(again.values()) == 0  # nothing new -> nothing loaded

        extract.generate_raw_data(START, days=9, seed=1, raw_dir=raw)  # 2 extra days
        incr = load.load_raw(con, raw)
        assert incr["orders"] > 0
        files = scalar(con, "SELECT COUNT(*) FROM meta_load_log WHERE entity='orders'")
        assert files == 9


def test_transform_cleans_dirty_data(env):
    raw, db = env
    with connect(db) as con:
        load.load_raw(con, raw)
        transform.run_models(con)
        # duplicates removed
        assert scalar(con, "SELECT COUNT(*)-COUNT(DISTINCT order_id) FROM stg_orders") == 0
        # countries standardised to ISO-2
        codes = {r[0] for r in con.execute("SELECT DISTINCT country_code FROM stg_customers")}
        assert codes <= {"US", "NG", "GB", "DE", "IN"}
        # statuses normalised
        statuses = {r[0] for r in con.execute("SELECT DISTINCT status FROM stg_orders")}
        assert all(s == s.lower() for s in statuses)
        # bad rows quarantined, not silently dropped
        reasons = {r[0] for r in con.execute("SELECT DISTINCT reject_reason FROM rejected_order_items")}
        assert reasons <= {"non_positive_quantity", "unknown_product", "unknown_order"}
        assert scalar(con, "SELECT COUNT(*) FROM fact_sales WHERE quantity <= 0") == 0


def test_quality_checks_pass_on_clean_run(env):
    raw, db = env
    with connect(db) as con:
        load.load_raw(con, raw)
        transform.run_models(con)
        results = quality.run_checks(con)
        assert all(r["passed"] for r in results if r["severity"] == "error")


def test_quality_checks_fail_on_corruption(env):
    raw, db = env
    with connect(db) as con:
        load.load_raw(con, raw)
        transform.run_models(con)
        con.execute("UPDATE fact_sales SET quantity = -1 WHERE rowid = 1")
        with pytest.raises(quality.DataQualityError):
            quality.run_checks(con)


def test_fact_revenue_reconciles(env):
    raw, db = env
    with connect(db) as con:
        load.load_raw(con, raw)
        transform.run_models(con)
        fact = scalar(con, "SELECT ROUND(SUM(net_amount),2) FROM fact_sales")
        stg = scalar(
            con,
            "SELECT ROUND(SUM(ROUND(quantity*unit_price*(1-discount),2)),2) FROM stg_order_items",
        )
        assert fact == pytest.approx(stg, abs=0.01)
