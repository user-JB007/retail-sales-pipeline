"""Unit tests for DQ helpers and a smoke path through silver checks."""

from __future__ import annotations

import pandas as pd
import pytest

from src.quality.checks import (
    check_no_nulls,
    check_not_empty,
    check_positive,
    check_unique,
    run_checks,
)


def test_check_not_empty_pass():
    name, ok, _ = check_not_empty(pd.DataFrame({"a": [1]}))
    assert ok is True
    assert name == "not_empty"


def test_check_not_empty_fail():
    _, ok, _ = check_not_empty(pd.DataFrame({"a": []}))
    assert ok is False


def test_check_unique():
    df = pd.DataFrame({"id": [1, 2, 3]})
    _, ok, _ = check_unique(df, ["id"])
    assert ok is True
    dup = pd.DataFrame({"id": [1, 1]})
    _, ok2, detail = check_unique(dup, ["id"])
    assert ok2 is False
    assert "duplicate_keys=1" in detail


def test_check_positive():
    df = pd.DataFrame({"qty": [1, 2, 3]})
    _, ok, _ = check_positive(df, "qty")
    assert ok is True
    bad = pd.DataFrame({"qty": [1, -1]})
    _, ok2, _ = check_positive(bad, "qty")
    assert ok2 is False


def test_run_checks_raises():
    checks = [check_not_empty(pd.DataFrame())]
    with pytest.raises(ValueError, match="failed"):
        run_checks(checks, raise_on_fail=True)


def test_run_checks_summary():
    df = pd.DataFrame({"id": [1], "amt": [10.0]})
    checks = [
        check_not_empty(df),
        check_no_nulls(df, ["id", "amt"]),
        check_unique(df, ["id"]),
    ]
    summary = run_checks(checks, raise_on_fail=True)
    assert summary["passed"] == 3
    assert summary["failed"] == []
