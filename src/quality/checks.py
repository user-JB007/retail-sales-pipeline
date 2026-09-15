"""Data quality checks for silver / gold layers.

Checks return a list of (check_name, passed: bool, detail: str) tuples.
Jobs can fail the pipeline when critical checks fail.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


CheckResult = tuple[str, bool, str]


def _result(name: str, passed: bool, detail: str) -> CheckResult:
    return name, passed, detail


def check_not_empty(df: pd.DataFrame, name: str = "not_empty") -> CheckResult:
    return _result(name, len(df) > 0, f"rows={len(df)}")


def check_no_nulls(df: pd.DataFrame, columns: list[str], name: str = "no_nulls") -> CheckResult:
    null_counts = {c: int(df[c].isna().sum()) for c in columns if c in df.columns}
    total = sum(null_counts.values())
    return _result(name, total == 0, f"nulls={null_counts}")


def check_unique(df: pd.DataFrame, columns: list[str], name: str = "unique_key") -> CheckResult:
    dupes = int(df.duplicated(subset=columns).sum())
    return _result(name, dupes == 0, f"duplicate_keys={dupes}")


def check_positive(df: pd.DataFrame, column: str, name: str | None = None) -> CheckResult:
    name = name or f"positive_{column}"
    if column not in df.columns:
        return _result(name, False, f"missing column {column}")
    bad = int((df[column] <= 0).sum())
    return _result(name, bad == 0, f"non_positive={bad}")


def check_referential(
    fact: pd.DataFrame,
    dim: pd.DataFrame,
    fact_key: str,
    dim_key: str,
    name: str = "referential_integrity",
) -> CheckResult:
    orphans = int((~fact[fact_key].isin(dim[dim_key])).sum())
    return _result(name, orphans == 0, f"orphans={orphans}")


def check_value_in_set(df: pd.DataFrame, column: str, allowed: set[Any], name: str | None = None) -> CheckResult:
    name = name or f"allowed_{column}"
    bad = int((~df[column].isin(allowed)).sum())
    return _result(name, bad == 0, f"invalid={bad}")


def run_checks(checks: list[CheckResult], raise_on_fail: bool = True) -> dict[str, Any]:
    summary = {
        "total": len(checks),
        "passed": sum(1 for _, ok, _ in checks if ok),
        "failed": [{"name": n, "detail": d} for n, ok, d in checks if not ok],
        "results": [{"name": n, "passed": ok, "detail": d} for n, ok, d in checks],
    }
    if raise_on_fail and summary["failed"]:
        failed_names = ", ".join(f["name"] for f in summary["failed"])
        raise ValueError(f"Data quality checks failed: {failed_names}")
    return summary


def print_check_report(summary: dict[str, Any]) -> None:
    print(f"DQ: {summary['passed']}/{summary['total']} passed")
    for r in summary["results"]:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"  [{mark}] {r['name']}: {r['detail']}")
