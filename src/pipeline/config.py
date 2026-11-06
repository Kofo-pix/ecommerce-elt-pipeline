"""Central configuration. Every path can be overridden via environment variables."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("PIPELINE_DATA_DIR", ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
DB_PATH = Path(os.getenv("PIPELINE_DB_PATH", DATA_DIR / "warehouse.db"))
SQL_DIR = ROOT / "sql"

# Execution order matters: staging first, then dimensions, then facts, then aggregates.
STAGING_MODELS = ["stg_customers", "stg_products", "stg_orders", "stg_order_items"]
MART_MODELS = [
    "dim_date",
    "dim_customers",
    "dim_products",
    "fact_sales",
    "agg_daily_sales",
    "agg_customer_value",
]

# entity -> (file extension, columns expected in the source file)
SOURCES = {
    "customers": ("csv", ["customer_id", "name", "email", "country", "signup_date"]),
    "products": ("jsonl", ["product_id", "name", "category", "unit_price"]),
    "orders": ("csv", ["order_id", "customer_id", "order_date", "status"]),
    "order_items": (
        "csv",
        ["order_item_id", "order_id", "product_id", "quantity", "unit_price", "discount"],
    ),
}
