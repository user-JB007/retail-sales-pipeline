"""
Airflow DAG: Retail Sales Medallion Pipeline

Orchestrates bronze → silver → gold with clear task dependencies.
Designed to run locally with Astro / MWAA / Composer / standalone Airflow.

Usage (local run without full Airflow):
  The same jobs are invoked by scripts/run_local.py.
  This DAG mirrors that sequence for production orchestration.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

# Resolve project root when DAG is deployed (set RETAIL_PIPELINE_HOME in env)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def _run_generate():
    from src.generate_source_data import main as gen
    gen()


def _run_bronze():
    from src.jobs.bronze_ingest import run
    run(engine="auto")


def _run_silver():
    from src.jobs.silver_transform import run
    run(engine="auto")


def _run_gold():
    from src.jobs.gold_aggregates import run
    run(engine="auto")


with DAG(
    dag_id="retail_sales_medallion_pipeline",
    description="Bronze → Silver → Gold retail sales pipeline with DQ gates",
    default_args=DEFAULT_ARGS,
    schedule="0 6 * * *",  # daily 06:00 UTC
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["retail", "medallion", "pyspark", "analytics"],
    max_active_runs=1,
) as dag:

    generate_raw = PythonOperator(
        task_id="generate_or_refresh_raw",
        python_callable=_run_generate,
        doc_md="Refresh source extracts (replace with S3/ADLS ingest in prod).",
    )

    bronze = PythonOperator(
        task_id="bronze_ingest",
        python_callable=_run_bronze,
        doc_md="Land raw CSV/Parquet into bronze with ingest metadata.",
    )

    silver = PythonOperator(
        task_id="silver_transform_and_dq",
        python_callable=_run_silver,
        doc_md="Clean, conform, quarantine bad rows, enforce DQ checks.",
    )

    gold = PythonOperator(
        task_id="gold_build_marts",
        python_callable=_run_gold,
        doc_md="Build analytics marts: store daily, category, CLV, product, channel.",
    )

    # Optional: load gold into Snowflake-style warehouse (SQL files as reference)
    warehouse_hint = BashOperator(
        task_id="warehouse_load_hint",
        bash_command=(
            'echo "Apply sql/*.sql in Snowflake (or compatible warehouse). '
            'See docs/architecture.md for ADF/Databricks/Fabric mapping."'
        ),
    )

    generate_raw >> bronze >> silver >> gold >> warehouse_hint
