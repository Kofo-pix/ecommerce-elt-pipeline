"""Airflow DAG (optional orchestration layer).

Requires `apache-airflow>=2.8`. Mount this repo and set PYTHONPATH=/opt/airflow/project/src.
extract -> load -> transform -> quality, daily, with retries and no catch-up.
"""
from datetime import date, datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from pipeline import extract, load, quality, transform
from pipeline.warehouse import connect


def _extract(ds, **_):
    day = date.fromisoformat(ds)
    extract.generate_raw_data(day, days=1)


def _load(**_):
    with connect() as con:
        load.load_raw(con)


def _transform(**_):
    with connect() as con:
        transform.run_models(con)


def _quality(**_):
    with connect() as con:
        quality.run_checks(con)


with DAG(
    dag_id="ecommerce_elt",
    description="Daily ELT: raw files -> warehouse -> star schema -> DQ checks",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["portfolio", "elt"],
) as dag:
    t_extract = PythonOperator(task_id="extract", python_callable=_extract)
    t_load = PythonOperator(task_id="load", python_callable=_load)
    t_transform = PythonOperator(task_id="transform", python_callable=_transform)
    t_quality = PythonOperator(task_id="data_quality", python_callable=_quality)

    t_extract >> t_load >> t_transform >> t_quality
