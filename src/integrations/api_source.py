"""API source: pull products (and optional carts/users) from Fake Store API.

Primary path: Fake Store HTTP API → data/bronze/api_products (+ optional tables).
Fallback: if network fails and a prior bronze landing exists, reuse it; otherwise
re-raise so the file-based raw path remains the offline default for the rest of
the medallion pipeline.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.integrations.http_client import get_json
from src.utils.paths import bronze_dir, project_root, raw_dir


def _load_cfg() -> dict[str, Any]:
    path = project_root() / "config" / "pipeline.yaml"
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _source_cfg() -> dict[str, Any]:
    cfg = _load_cfg().get("api_source", {})
    base = os.getenv("API_SOURCE_BASE_URL", cfg.get("base_url", "https://fakestoreapi.com"))
    return {
        "base_url": base.rstrip("/"),
        "products_path": cfg.get("products_path", "/products"),
        "carts_path": cfg.get("carts_path", "/carts"),
        "users_path": cfg.get("users_path", "/users"),
        "timeout": float(os.getenv("API_HTTP_TIMEOUT", cfg.get("timeout", 20))),
        "retries": int(os.getenv("API_HTTP_RETRIES", cfg.get("retries", 3))),
        "fetch_carts": bool(cfg.get("fetch_carts", True)),
        "fetch_users": bool(cfg.get("fetch_users", True)),
    }


def _ingest_meta(source_system: str = "fakestore_api") -> dict[str, str]:
    now = datetime.now(timezone.utc)
    return {
        "_ingest_ts": now.strftime("%Y-%m-%d %H:%M:%S"),
        "_source_system": source_system,
        "_pipeline_run_id": now.strftime("%Y%m%d%H%M%S"),
    }


def _map_products(rows: list[dict[str, Any]]) -> pd.DataFrame:
    mapped = []
    for r in rows:
        rating = r.get("rating") or {}
        mapped.append(
            {
                "api_product_id": r.get("id"),
                "product_name": r.get("title"),
                "category": r.get("category"),
                "unit_price": r.get("price"),
                "description": r.get("description"),
                "image_url": r.get("image"),
                "rating_rate": rating.get("rate"),
                "rating_count": rating.get("count"),
            }
        )
    return pd.DataFrame(mapped)


def _write_table(name: str, df: pd.DataFrame, meta: dict[str, str]) -> dict[str, Any]:
    out_dir = bronze_dir() / name
    out_dir.mkdir(parents=True, exist_ok=True)
    for k, v in meta.items():
        df[k] = v
    parquet_path = out_dir / "data.parquet"
    csv_path = out_dir / "data.csv"
    df.to_parquet(parquet_path, index=False)
    df.to_csv(csv_path, index=False)
    # Also land a raw JSON snapshot for audit
    raw_api = raw_dir() / "api"
    raw_api.mkdir(parents=True, exist_ok=True)
    snap = raw_api / f"{name}.json"
    # Drop meta cols for raw snapshot
    meta_cols = list(meta.keys())
    df.drop(columns=meta_cols, errors="ignore").to_json(snap, orient="records", indent=2)
    print(f"[api_source] {name}: {len(df)} rows -> {parquet_path}")
    return {"rows": len(df), "path": str(parquet_path), "csv": str(csv_path)}


def fetch_fakestore(*, use_network: bool = True) -> dict[str, Any]:
    """Fetch Fake Store resources into bronze api_* tables."""
    scfg = _source_cfg()
    meta = _ingest_meta()
    results: dict[str, Any] = {"source": "fakestoreapi", "base_url": scfg["base_url"]}

    try:
        if not use_network:
            raise ConnectionError("network disabled")
        products = get_json(
            f"{scfg['base_url']}{scfg['products_path']}",
            timeout=scfg["timeout"],
            retries=scfg["retries"],
        )
        if not isinstance(products, list):
            raise ValueError("Unexpected Fake Store products payload")
        results["api_products"] = _write_table("api_products", _map_products(products), meta)

        if scfg["fetch_carts"]:
            carts = get_json(
                f"{scfg['base_url']}{scfg['carts_path']}",
                timeout=scfg["timeout"],
                retries=scfg["retries"],
            )
            carts_df = pd.json_normalize(carts)
            results["api_carts"] = _write_table("api_carts", carts_df, meta)

        if scfg["fetch_users"]:
            users = get_json(
                f"{scfg['base_url']}{scfg['users_path']}",
                timeout=scfg["timeout"],
                retries=scfg["retries"],
            )
            users_df = pd.json_normalize(users)
            results["api_users"] = _write_table("api_users", users_df, meta)

        manifest = bronze_dir() / "api_source_manifest.json"
        bronze_dir().mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(results, indent=2), encoding="utf-8")
        results["manifest"] = str(manifest)
        return results
    except Exception as exc:
        # Offline fallback: keep existing bronze api_products if present
        existing = bronze_dir() / "api_products" / "data.parquet"
        if existing.exists():
            print(f"[api_source] network failed ({exc}); reusing {existing}")
            return {
                "source": "fakestoreapi",
                "fallback": True,
                "error": str(exc),
                "api_products": {"rows": len(pd.read_parquet(existing)), "path": str(existing)},
            }
        raise RuntimeError(
            f"API source failed and no bronze fallback at {existing}: {exc}"
        ) from exc


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Extract products from Fake Store API")
    parser.add_argument("--offline", action="store_true", help="Skip network; require existing bronze")
    args = parser.parse_args(argv)
    result = fetch_fakestore(use_network=not args.offline)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
