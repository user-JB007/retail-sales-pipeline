"""Project path helpers."""

from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def raw_dir() -> Path:
    return project_root() / "data" / "raw"


def bronze_dir() -> Path:
    return project_root() / "data" / "bronze"


def silver_dir() -> Path:
    return project_root() / "data" / "silver"


def gold_dir() -> Path:
    return project_root() / "data" / "gold"


def output_dir() -> Path:
    return project_root() / "output"
