"""EXTRACT: simulate source systems landing files in a date-partitioned raw zone.

Layout:  data/raw/<entity>/dt=YYYY-MM-DD/<entity>.<ext>

The generator deliberately injects realistic data problems (duplicates, bad emails,
inconsistent country spellings, negative quantities, orphan keys, mixed-case status)
so the downstream cleaning and data-quality layers have real work to do.
"""
from __future__ import annotations

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

from .config import RAW_DIR, SOURCES
from .logger import get_logger

log = get_logger("extract")

COUNTRY_VARIANTS = {
    "US": ["United States", "USA", "us", "US "],
    "NG": ["Nigeria", "NG", "nigeria"],
    "GB": ["United Kingdom", "UK", "gb"],
    "DE": ["Germany", "DE", "germany"],
    "IN": ["India", "IN", "india"],
}
CATEGORIES = {
    "Electronics": (15, 600),
    "Home": (8, 250),
    "Books": (5, 40),
    "Fashion": (10, 180),
    "Sports": (10, 300),
}
STATUSES = ["completed"] * 8 + ["shipped", "pending", "cancelled", "returned"]
FIRST = ["Ada", "Tunde", "Maria", "John", "Priya", "Liam", "Chioma", "Emma", "Omar", "Sofia"]
LAST = ["Okafor", "Smith", "Garcia", "Patel", "Müller", "Brown", "Adeyemi", "Khan", "Lopez"]


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _partition(raw_dir: Path, entity: str, day: date) -> Path:
    ext, _ = SOURCES[entity]
    return raw_dir / entity / f"dt={day.isoformat()}" / f"{entity}.{ext}"


def generate_raw_data(
    start: date,
    days: int = 30,
    seed: int = 42,
    raw_dir: Path = RAW_DIR,
    n_products: int = 60,
    daily_signups: int = 15,
    daily_orders: tuple[int, int] = (40, 120),
) -> dict[str, int]:
    """Write `days` daily partitions of synthetic source data. Deterministic for a given seed."""
    rng = random.Random(seed)
    stats = {k: 0 for k in SOURCES}

    # --- products: one snapshot on day 0 -----------------------------------------------
    products = []
    for i in range(1, n_products + 1):
        cat = rng.choice(list(CATEGORIES))
        lo, hi = CATEGORIES[cat]
        products.append(
            {
                "product_id": f"P{i:04d}",
                "name": f"{cat} Item {i}",
                "category": cat,
                "unit_price": round(rng.uniform(lo, hi), 2),
            }
        )
    _write_jsonl(_partition(raw_dir, "products", start), products)
    stats["products"] = len(products)

    known_customers: list[str] = []
    cust_seq = order_seq = item_seq = 0

    for d in range(days):
        day = start + timedelta(days=d)

        # --- customers: new sign-ups that day ------------------------------------------
        customers = []
        for _ in range(daily_signups):
            cust_seq += 1
            cid = f"C{cust_seq:06d}"
            name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
            email = f"{name.lower().replace(' ', '.')}{cust_seq}@example.com"
            r = rng.random()
            if r < 0.03:
                email = ""  # missing
            elif r < 0.05:
                email = email.replace("@", "")  # malformed
            elif r < 0.08:
                email = email.upper()  # casing
            iso = rng.choice(list(COUNTRY_VARIANTS))
            customers.append(
                {
                    "customer_id": cid,
                    "name": name,
                    "email": email,
                    "country": rng.choice(COUNTRY_VARIANTS[iso]),
                    "signup_date": day.isoformat(),
                }
            )
            known_customers.append(cid)
        if customers and rng.random() < 0.5:
            customers.append(dict(customers[0]))  # duplicate row
        _write_csv(_partition(raw_dir, "customers", day), SOURCES["customers"][1], customers)
        stats["customers"] += len(customers)

        # --- orders + items -------------------------------------------------------------
        orders, items = [], []
        for _ in range(rng.randint(*daily_orders)):
            order_seq += 1
            oid = f"O{order_seq:07d}"
            status = rng.choice(STATUSES)
            if rng.random() < 0.05:
                status = status.upper()
            orders.append(
                {
                    "order_id": oid,
                    "customer_id": rng.choice(known_customers),
                    "order_date": day.isoformat(),
                    "status": status,
                }
            )
            for _ in range(rng.randint(1, 4)):
                item_seq += 1
                prod = rng.choice(products)
                qty = rng.randint(1, 5)
                pid = prod["product_id"]
                r = rng.random()
                if r < 0.01:
                    qty = -qty  # invalid quantity
                elif r < 0.02:
                    pid = "P9999"  # orphan product
                items.append(
                    {
                        "order_item_id": f"I{item_seq:08d}",
                        "order_id": oid,
                        "product_id": pid,
                        "quantity": qty,
                        "unit_price": prod["unit_price"],
                        "discount": rng.choice([0, 0, 0, 0.05, 0.1, 0.2]),
                    }
                )
        if orders and rng.random() < 0.7:  # late-arriving duplicate rows
            orders.append(dict(orders[0]))
            items.append(dict(items[0]))
        _write_csv(_partition(raw_dir, "orders", day), SOURCES["orders"][1], orders)
        _write_csv(_partition(raw_dir, "order_items", day), SOURCES["order_items"][1], items)
        stats["orders"] += len(orders)
        stats["order_items"] += len(items)

    log.info("Extracted %s", stats)
    return stats
