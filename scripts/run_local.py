#!/usr/bin/env python3
"""One-command local run: generate → (optional API source) → bronze → silver → gold → (optional API sink)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description="Run full retail sales pipeline locally")
    parser.add_argument("--engine", choices=["auto", "spark", "pandas"], default="pandas",
                        help="Transform engine (default pandas for local runs)")
    parser.add_argument("--n-transactions", type=int, default=5000)
    parser.add_argument("--skip-generate", action="store_true")
    parser.add_argument(
        "--source",
        choices=["file", "api", "both"],
        default="file",
        help="file=existing raw CSVs; api=Fake Store pull; both=file then api",
    )
    parser.add_argument(
        "--sink",
        choices=["none", "api", "file"],
        default="none",
        help="api=POST gold summary to HTTP sinks; file=write landing JSON only via sink fallback",
    )
    args = parser.parse_args()

    import os
    if args.engine == "pandas":
        os.environ["FORCE_PANDAS"] = "1"

    if args.source in ("file", "both") and not args.skip_generate:
        print("=== Generate source extracts ===")
        from src.generate_source_data import main as gen
        gen(n_txns=args.n_transactions)
    elif args.skip_generate:
        print("=== Skip generate (using existing data/raw) ===")

    if args.source in ("api", "both"):
        print("=== Extract API (Fake Store) ===")
        from src.integrations.api_source import fetch_fakestore
        api_result = fetch_fakestore(use_network=True)
        print(json.dumps(api_result, indent=2, default=str))

    print("=== Bronze ingest ===")
    from src.jobs.bronze_ingest import run as bronze
    bronze(engine=args.engine)

    print("=== Silver transform + DQ ===")
    from src.jobs.silver_transform import run as silver
    silver(engine=args.engine)

    print("=== Gold marts ===")
    from src.jobs.gold_aggregates import run as gold
    result = gold(engine=args.engine)

    if args.sink == "api":
        print("=== Load API sink ===")
        from src.integrations.api_sink import push_gold_summary
        sink_result = push_gold_summary()
        print(json.dumps(sink_result, indent=2, default=str))
    elif args.sink == "file":
        print("=== Sink file fallback (no HTTP) ===")
        from src.integrations.api_sink import push_gold_summary
        sink_result = push_gold_summary(post_local=True, post_external=False)
        print(json.dumps(sink_result, indent=2, default=str))

    summary = ROOT / "data" / "gold" / "pipeline_outputs.json"
    if summary.exists():
        print("\n=== Pipeline outputs ===")
        print(summary.read_text())

    print("\nPipeline finished successfully.")
    print(f"Gold marts: {json.dumps(result.get('marts', {}), indent=2)}")


if __name__ == "__main__":
    main()
