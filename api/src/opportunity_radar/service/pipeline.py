"""The whole run, in order: fx -> sources -> geo -> tech stack -> signals -> needs -> regions -> score -> radar run."""

import csv
from pathlib import Path
from typing import Any

import orjson
from loguru import logger

from opportunity_radar.db import execute, rows, transaction
from opportunity_radar.service import geo, needs, opportunities, regions, signals
from opportunity_radar.sources import ats, boards, fx, rss, techstack

WATCHLIST = Path(__file__).resolve().parents[4] / "resources" / "seed" / "watchlist.csv"


def _status(key: str, ok: bool, count: int | None, detail: str) -> None:
    with transaction() as connection:
        execute(
            connection,
            "UPDATE source SET last_run_at = now(), last_status = :s, last_count = :n WHERE key = :k",
            {"k": key, "s": ("ok" if ok else "error") + (f": {detail}" if detail else ""), "n": count},
        )


def run_sources(only: str | None = None) -> None:
    with transaction() as connection:
        sources = rows(
            connection,
            "SELECT key, kind, config FROM source WHERE enabled" + (" AND key = :k" if only else ""),
            {"k": only} if only else {},
        )
    for source in sources:
        config: dict[str, Any] = (
            source["config"] if isinstance(source["config"], dict) else orjson.loads(source["config"])
        )
        try:
            if source["kind"] == "fx":
                count = fx.refresh(config["url"])
            elif source["kind"] == "remotive":
                count, _ = boards.ingest_remotive(config)
            elif source["kind"] == "arbeitnow":
                count, _ = boards.ingest_arbeitnow(config)
            elif source["kind"] == "rss":
                count, _ = rss.ingest(source["key"], config)
            else:
                raise ValueError(f"unknown source kind {source['kind']} for {source['key']}")
            _status(source["key"], True, count, "")
        except Exception as failed:  # noqa: BLE001 — a source is an external boundary; log and continue with the next
            logger.exception(f"source {source['key']} failed: {failed}")
            _status(source["key"], False, None, f"{type(failed).__name__}: {failed}"[:200])


def run_watchlist(only: str | None = None) -> None:
    with WATCHLIST.open() as handle:
        companies = [record for record in csv.DictReader(line for line in handle if not line.startswith("#"))]
    for company in companies:
        if only and company["slug"] != only:
            continue
        key = f"{company['ats']}:{company['slug']}"
        try:
            seen, _ = ats.ingest_company(
                company["name"],
                company["domain"],
                company["ats"],
                company["slug"],
                company["region"],
                company["is_ai_native"].lower() == "true",
            )
            _ensure_source(
                key,
                company["ats"],
                company["region"],
                f"{company['name']} ({company['ats']})",
                True,
                seen,
                "",
            )
        except Exception as failed:  # noqa: BLE001 — same boundary as above
            logger.exception(f"watchlist {key} failed: {failed}")
            _ensure_source(
                key,
                company["ats"],
                company["region"],
                f"{company['name']} ({company['ats']})",
                False,
                None,
                f"{type(failed).__name__}: {failed}"[:200],
            )


def _ensure_source(
    key: str, kind: str, region: str, label: str, ok: bool, count: int | None, detail: str
) -> None:
    with transaction() as connection:
        execute(
            connection,
            "INSERT INTO source (key, kind, region, label) VALUES (:k, :kind, :r, :l) ON CONFLICT (key) DO NOTHING",
            {"k": key, "kind": kind, "r": region, "l": label},
        )
    _status(key, ok, count, detail)


def run_all() -> dict[str, Any]:
    run_sources()
    run_watchlist()
    geo.resolve_all()
    techstack.scan()
    signals.derive()
    needs.detect()
    regions.compute()
    opportunities.score_all()
    summary = opportunities.record_run()
    logger.info(f"radar: {summary}")
    return summary
