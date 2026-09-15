"""Spark session helpers with a graceful pandas-only fallback flag."""

from __future__ import annotations

import os
from typing import Optional


def spark_available() -> bool:
    if os.environ.get("FORCE_PANDAS", "").lower() in {"1", "true", "yes"}:
        return False
    try:
        import pyspark  # noqa: F401
        return True
    except ImportError:
        return False


def get_spark(app_name: str = "retail-sales-pipeline"):
    """Return a local SparkSession, or None when pandas fallback should be used."""
    if not spark_available():
        return None
    from pyspark.sql import SparkSession

    builder = (
        SparkSession.builder.appName(app_name)
        .master(os.environ.get("SPARK_MASTER", "local[*]"))
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.driver.memory", os.environ.get("SPARK_DRIVER_MEMORY", "2g"))
    )
    return builder.getOrCreate()


def stop_spark(spark: Optional[object]) -> None:
    if spark is not None:
        spark.stop()
