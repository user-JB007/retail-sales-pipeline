"""API sink: POST gold mart summary JSON to local landing API and/or JSONPlaceholder."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.integrations.http_client import post_json
from src.utils.paths import gold_dir, project_root


def _load_cfg() -> dict[str, Any]:
    path = project_root() / "config" / "pipeline.yaml"
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _sink_cfg() -> dict[str, Any]:
    cfg = _load_cfg().get("api_sink", {})
    return {
        "local_url": os.getenv(
            "SINK_API_URL",
            cfg.get("local_url", "http://127.0.0.1:8089/ingest"),
        ),
        "external_url": os.getenv(
            "EXTERNAL_SINK_URL",
            cfg.get("external_url", "https://jsonplaceholder.typicode.com/posts"),
        ),
        "timeout": float(os.getenv("API_HTTP_TIMEOUT", cfg.get("timeout", 20))),
        "retries": int(os.getenv("API_HTTP_RETRIES", cfg.get("retries", 3))),
        "post_external": bool(cfg.get("post_external", True)),
        "post_local": bool(cfg.get("post_local", True)),
    }


def build_gold_summary() -> dict[str, Any]:
    """Build a compact gold summary payload from mart CSVs / pipeline_outputs."""
    root = gold_dir()
    summary: dict[str, Any] = {
        "pipeline": "retail-sales-pipeline",
        "layer": "gold",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "marts": {},
    }
    outputs = root / "pipeline_outputs.json"
    if outputs.exists():
        try:
            summary["pipeline_outputs"] = json.loads(outputs.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    store_mart = root / "mart_daily_sales_by_store" / "data.csv"
    if store_mart.exists():
        df = pd.read_csv(store_mart)
        summary["marts"]["daily_sales_by_store"] = {
            "rows": len(df),
            "net_revenue_sum": float(df["net_revenue"].sum()) if "net_revenue" in df.columns else None,
            "top_stores": (
                df.groupby("store_name", as_index=False)["net_revenue"]
                .sum()
                .sort_values("net_revenue", ascending=False)
                .head(5)
                .to_dict(orient="records")
                if "store_name" in df.columns and "net_revenue" in df.columns
                else []
            ),
        }

    channel = root / "mart_channel_mix" / "data.csv"
    if channel.exists():
        df = pd.read_csv(channel)
        summary["marts"]["channel_mix"] = {
            "rows": len(df),
            "preview": df.head(10).to_dict(orient="records"),
        }

    # Include API products enrichment stats if present
    api_prod = project_root() / "data" / "bronze" / "api_products" / "data.csv"
    if api_prod.exists():
        ap = pd.read_csv(api_prod)
        summary["api_products_landed"] = len(ap)

    return summary


def _write_receipt(name: str, payload: dict[str, Any], response: Any) -> Path:
    receipts = project_root() / "data" / "sink_receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = receipts / f"{ts}_{name}.json"
    path.write_text(
        json.dumps({"request": payload, "response": response}, indent=2, default=str),
        encoding="utf-8",
    )
    return path


def push_gold_summary(
    *,
    post_local: bool | None = None,
    post_external: bool | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scfg = _sink_cfg()
    body = payload or build_gold_summary()
    do_local = scfg["post_local"] if post_local is None else post_local
    do_ext = scfg["post_external"] if post_external is None else post_external
    result: dict[str, Any] = {"payload_keys": list(body.keys()), "deliveries": {}}

    if do_local:
        try:
            resp = post_json(
                scfg["local_url"],
                body,
                timeout=scfg["timeout"],
                retries=scfg["retries"],
            )
            receipt = _write_receipt("local", body, resp)
            result["deliveries"]["local"] = {"ok": True, "url": scfg["local_url"], "receipt": str(receipt), "response": resp}
        except Exception as exc:
            # File fallback: write payload under data/landing when local sink is down
            landing = project_root() / "data" / "landing"
            landing.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            fallback = landing / f"gold_summary_{ts}.json"
            fallback.write_text(json.dumps(body, indent=2, default=str), encoding="utf-8")
            result["deliveries"]["local"] = {
                "ok": False,
                "error": str(exc),
                "fallback_file": str(fallback),
            }

    if do_ext:
        try:
            # JSONPlaceholder expects title/body/userId style; wrap our summary
            ext_body = {
                "title": "retail-sales-pipeline gold summary",
                "body": json.dumps(body, default=str)[:5000],
                "userId": 1,
            }
            resp = post_json(
                scfg["external_url"],
                ext_body,
                timeout=scfg["timeout"],
                retries=scfg["retries"],
            )
            receipt = _write_receipt("external_jsonplaceholder", ext_body, resp)
            result["deliveries"]["external"] = {
                "ok": True,
                "url": scfg["external_url"],
                "receipt": str(receipt),
                "response": resp,
            }
        except Exception as exc:
            result["deliveries"]["external"] = {"ok": False, "error": str(exc)}

    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Push gold summary to HTTP sinks")
    parser.add_argument("--no-local", action="store_true")
    parser.add_argument("--no-external", action="store_true")
    args = parser.parse_args(argv)
    result = push_gold_summary(post_local=not args.no_local, post_external=not args.no_external)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
