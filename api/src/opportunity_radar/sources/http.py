"""Paced HTTP fetching with a raw copy on disk and a row in fetch_log for every request."""

import hashlib
import time
from datetime import UTC, datetime
from typing import Any

import httpx
from loguru import logger

from opportunity_radar.config import (
    FETCH_MIN_INTERVAL_SECONDS,
    FETCH_TIMEOUT_SECONDS,
    FETCH_USER_AGENT,
    RAW_DIR,
)
from opportunity_radar.db import execute, transaction
from opportunity_radar.ids import new_id

_last_request_at: dict[str, float] = {}


def _pace(host: str) -> None:
    waited = time.monotonic() - _last_request_at.get(host, 0.0)
    if waited < FETCH_MIN_INTERVAL_SECONDS:
        time.sleep(FETCH_MIN_INTERVAL_SECONDS - waited)
    _last_request_at[host] = time.monotonic()


def _log(source_key: str, url: str, status: int | None, ok: bool, detail: str) -> None:
    with transaction() as connection:
        execute(
            connection,
            "INSERT INTO fetch_log (id, source_key, url, status, ok, detail) VALUES (:id, :s, :u, :st, :ok, :d)",
            {"id": new_id(), "s": source_key, "u": url, "st": status, "ok": ok, "d": detail[:500]},
        )


def fetch(
    source_key: str, url: str, params: dict[str, Any] | None = None, accept: str = "application/json"
) -> httpx.Response:
    """GET with pacing per host. Raises on transport errors and non-2xx; the caller is a system boundary."""
    host = httpx.URL(url).host
    _pace(host)
    headers = {"User-Agent": FETCH_USER_AGENT, "Accept": accept}
    try:
        response = httpx.get(
            url, params=params, headers=headers, timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=True
        )
    except httpx.HTTPError as failed:
        _log(source_key, url, None, False, f"{type(failed).__name__}: {failed}")
        raise
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    digest = hashlib.sha1(str(response.url).encode()).hexdigest()[:12]
    target = RAW_DIR / source_key / day / f"{digest}.body"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(response.content)
    _log(
        source_key,
        str(response.url),
        response.status_code,
        response.is_success,
        f"{len(response.content)} bytes -> {target}",
    )
    if not response.is_success:
        logger.warning(f"{source_key}: {response.status_code} for {response.url}")
        response.raise_for_status()
    return response
