"""Minimal HTTP client with timeouts and simple retries."""

from __future__ import annotations

import time
from typing import Any

import requests

DEFAULT_TIMEOUT = 20
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 0.8


def request_json(
    method: str,
    url: str,
    *,
    json_body: Any | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
) -> Any:
    """Perform an HTTP request and return parsed JSON.

    Raises the last requests exception or HTTPError after retries are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.request(
                method.upper(),
                url,
                json=json_body,
                headers=headers or {"Accept": "application/json"},
                timeout=timeout,
            )
            if resp.status_code >= 500 and attempt < retries:
                time.sleep(backoff * attempt)
                continue
            resp.raise_for_status()
            if not resp.content:
                return None
            return resp.json()
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            last_exc = exc
            if attempt >= retries:
                break
            time.sleep(backoff * attempt)
    assert last_exc is not None
    raise last_exc


def get_json(url: str, **kwargs: Any) -> Any:
    return request_json("GET", url, **kwargs)


def post_json(url: str, json_body: Any, **kwargs: Any) -> Any:
    return request_json("POST", url, json_body=json_body, **kwargs)
