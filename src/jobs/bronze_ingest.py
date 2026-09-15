"""Bronze layer: land raw files as-is with ingest metadata.

Reads CSV/Parquet from data/raw and writes parquet to data/bronze.
Prefers PySpark; falls back to pandas when Spark is unavailable (CI / local runs).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.utils.paths import bronze_dir, project_root, raw_dir
from src.utils.spark_session import get_spark, spark_available, stop_spark


RAW_TABLES = {
    "stores": "stores.csv",
    "products": "products.csv",
    "customers": "customers.csv",
    "sales_transactions": "sales_transactions.csv",
    "service_tickets": "service_tickets.csv",
}


def _ingest_meta() -> dict:
    return {
        "_ingest_ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "_source_system": "retail_ops",
        "_pipeline_run_id": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
    }


def ingest_pandas(raw: Path, bronze: Path) -> dict:
    bronze.mkdir(parents=True, exist_ok=True)
    meta = _ingest_meta()
    results = {}
    for table, filename in RAW_TABLES.items():
        src = raw / filename
        if not src.exists():
            raise FileNotFoundError(
                f"Missing raw file: {src}. Run: python -m src.generate_source_data"
            )
        df = pd.read_csv(src)
        for k, v in meta.items():
            df[k] = v
        out = bronze / table
        out.mkdir(parents=True, exist_ok=True)
        path = out / "data.parquet"
        df.to_parquet(path, index=False)
        results[table] = {"rows": len(df), "path": str(path)}
        print(f"[bronze/pandas] {table}: {len(df)} rows -> {path}")
    return results


def ingest_spark(raw: Path, bronze: Path) -> dict:
    spark = get_spark("bronze-ingest")
    if spark is None:
        return ingest_pandas(raw, bronze)
    from pyspark.sql import functions as F

    bronze.mkdir(parents=True, exist_ok=True)
    meta = _ingest_meta()
    results = {}
    try:
        for table, filename in RAW_TABLES.items():
            src = raw / filename
            if not src.exists():
                raise FileNotFoundError(f"Missing raw file: {src}")
            df = (
                spark.read.option("header", True)
                .option("inferSchema", True)
                .csv(str(src))
            )
            for k, v in meta.items():
                df = df.withColumn(k, F.lit(v))
            out = bronze / table
            df.write.mode("overwrite").parquet(str(out))
            count = df.count()
            results[table] = {"rows": count, "path": str(out)}
            print(f"[bronze/spark] {table}: {count} rows -> {out}")
    finally:
        stop_spark(spark)
    return results


def run(engine: str = "auto") -> dict:
    raw = raw_dir()
    bronze = bronze_dir()

    if engine == "pandas" or (engine == "auto" and not spark_available()):
        results = ingest_pandas(raw, bronze)
        engine_used = "pandas"
    else:
        results = ingest_spark(raw, bronze)
        engine_used = "spark"

    manifest = {
        "layer": "bronze",
        "engine": engine_used if engine == "auto" else engine,
        "tables": results,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    out_manifest = bronze / "_manifest.json"
    out_manifest.write_text(json.dumps(manifest, indent=2))
    print(f"Bronze ingest complete. Manifest: {out_manifest}")
    return manifest


def main():
    import sys

    root = str(project_root())
    if root not in sys.path:
        sys.path.insert(0, root)
    parser = argparse.ArgumentParser(description="Bronze ingest job")
    parser.add_argument("--engine", choices=["auto", "spark", "pandas"], default="auto")
    args = parser.parse_args()
    run(args.engine)


if __name__ == "__main__":
    main()
