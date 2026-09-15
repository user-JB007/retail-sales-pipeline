#!/usr/bin/env python3
"""One-command local run: generate source data → bronze → silver → gold."""

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
    args = parser.parse_args()

    # Force pandas path unless user explicitly asks for spark
    import os
    if args.engine == "pandas":
        os.environ["FORCE_PANDAS"] = "1"

    if not args.skip_generate:
        print("=== 1/4 Generate source extracts ===")
        from src.generate_source_data import main as gen
        gen(n_txns=args.n_transactions)
    else:
        print("=== 1/4 Skip generate (using existing data/raw) ===")

    print("=== 2/4 Bronze ingest ===")
    from src.jobs.bronze_ingest import run as bronze
    bronze(engine=args.engine)

    print("=== 3/4 Silver transform + DQ ===")
    from src.jobs.silver_transform import run as silver
    silver(engine=args.engine)

    print("=== 4/4 Gold marts ===")
    from src.jobs.gold_aggregates import run as gold
    result = gold(engine=args.engine)

    summary = ROOT / "data" / "gold" / "pipeline_outputs.json"
    if summary.exists():
        print("\n=== Pipeline outputs ===")
        print(summary.read_text())

    print("\nPipeline finished successfully.")
    print(f"Gold marts: {json.dumps(result.get('marts', {}), indent=2)}")


if __name__ == "__main__":
    main()
