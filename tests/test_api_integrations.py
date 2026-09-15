"""Smoke tests for API source/sink (live network when available; mocks otherwise)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.integrations.api_source import fetch_fakestore, _map_products
from src.integrations.api_sink import push_gold_summary
from src.integrations.http_client import get_json, post_json


SAMPLE_PRODUCTS = [
    {
        "id": 1,
        "title": "Widget",
        "price": 9.99,
        "description": "A widget",
        "category": "gadgets",
        "image": "http://example.com/w.png",
        "rating": {"rate": 4.5, "count": 10},
    }
]


def test_map_products():
    df = _map_products(SAMPLE_PRODUCTS)
    assert len(df) == 1
    assert df.iloc[0]["product_name"] == "Widget"
    assert df.iloc[0]["api_product_id"] == 1


def test_fetch_fakestore_mocked(tmp_path, monkeypatch):
    import src.integrations.api_source as mod

    monkeypatch.setattr(mod, "bronze_dir", lambda: tmp_path / "bronze")
    monkeypatch.setattr(mod, "raw_dir", lambda: tmp_path / "raw")
    monkeypatch.setattr(mod, "project_root", lambda: tmp_path)
    (tmp_path / "bronze").mkdir()
    (tmp_path / "raw").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "pipeline.yaml").write_text(
        "api_source:\n  base_url: https://fakestoreapi.com\n  fetch_carts: true\n  fetch_users: true\n"
    )

    with patch.object(mod, "get_json", side_effect=[SAMPLE_PRODUCTS, [], []]):
        result = fetch_fakestore(use_network=True)
    assert result["api_products"]["rows"] == 1
    assert (tmp_path / "bronze" / "api_products" / "data.parquet").exists()


def test_push_sink_external_mocked(tmp_path, monkeypatch):
    import src.integrations.api_sink as sink_mod

    monkeypatch.setattr(sink_mod, "gold_dir", lambda: tmp_path / "gold")
    monkeypatch.setattr(sink_mod, "project_root", lambda: tmp_path)
    (tmp_path / "gold").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "pipeline.yaml").write_text(
        "api_sink:\n  post_local: false\n  post_external: true\n"
        "  external_url: https://jsonplaceholder.typicode.com/posts\n"
    )

    with patch.object(sink_mod, "post_json", return_value={"id": 101}):
        result = push_gold_summary(post_local=False, post_external=True, payload={"hello": "world"})
    assert result["deliveries"]["external"]["ok"] is True


@pytest.mark.network
def test_live_fakestore_optional():
    try:
        data = get_json("https://fakestoreapi.com/products", timeout=10, retries=1)
    except Exception as exc:
        pytest.skip(f"network unavailable: {exc}")
    assert isinstance(data, list) and len(data) > 0


@pytest.mark.network
def test_live_jsonplaceholder_post_optional():
    try:
        resp = post_json(
            "https://jsonplaceholder.typicode.com/posts",
            {"title": "t", "body": "b", "userId": 1},
            timeout=10,
            retries=1,
        )
    except Exception as exc:
        pytest.skip(f"network unavailable: {exc}")
    assert resp.get("id") is not None
