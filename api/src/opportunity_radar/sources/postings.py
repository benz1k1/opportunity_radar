"""The common shape every job source produces, and the upsert that stores it."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import orjson
from sqlalchemy import Connection

from opportunity_radar.db import execute, row
from opportunity_radar.ids import new_id
from opportunity_radar.service import classify
from opportunity_radar.service.companies import upsert_company


@dataclass
class Posting:
    external_id: str
    title: str
    url: str
    company_name: str
    company_domain: str | None = None
    company_region: str | None = None
    company_is_ai_native: bool = False
    location: str = ""
    description: str = ""
    posted_at: datetime | None = None
    employment_hint: str = ""
    remote_hint: bool | None = None
    rate_text: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


def store(connection: Connection, source_key: str, posting: Posting) -> tuple[str, bool]:
    """Upserts the posting; returns (posting_id, is_new). Non-English postings are stored flagged, never scored."""
    company_id = upsert_company(
        connection,
        posting.company_name,
        posting.company_domain,
        posting.company_region,
        posting.company_is_ai_native,
    )
    description = classify.strip_html(posting.description)
    scope, detail = classify.remote_scope_of(posting.location, description, posting.remote_hint)
    rate = classify.rate_of(posting.rate_text) or classify.rate_of(description[:3000])
    existing = row(
        connection,
        "SELECT id FROM job_posting WHERE source_key = :s AND external_id = :e",
        {"s": source_key, "e": posting.external_id},
    )
    posting_id = existing["id"] if existing else new_id()
    params: dict[str, Any] = {
        "id": posting_id,
        "company_id": company_id,
        "source_key": source_key,
        "external_id": posting.external_id,
        "title": posting.title.strip(),
        "family": classify.family_of(posting.title),
        "location": posting.location or None,
        "remote_scope": scope,
        "remote_detail": detail or None,
        "employment_type": classify.employment_type_of(posting.title, posting.employment_hint),
        "rate_min": rate.minimum if rate else None,
        "rate_max": rate.maximum if rate else None,
        "rate_currency": rate.currency if rate else None,
        "rate_period": rate.period if rate else None,
        "url": posting.url,
        "posted_at": posting.posted_at,
        "description": description[:20000],
        "tech": classify.tech_of(f"{posting.title} {description}"),
        "is_english": classify.is_english(posting.title, description),
        "raw": posting.raw,
        "now": datetime.now(UTC),
    }
    if existing:
        execute(
            connection,
            """UPDATE job_posting SET title = :title, family = :family, location = :location, remote_scope = :remote_scope,
               remote_detail = :remote_detail, employment_type = :employment_type, rate_min = :rate_min, rate_max = :rate_max,
               rate_currency = :rate_currency, rate_period = :rate_period, url = :url, posted_at = COALESCE(:posted_at, posted_at),
               description = :description, tech = :tech, is_english = :is_english, raw = CAST(:raw AS jsonb),
               last_seen_at = :now, closed_at = NULL WHERE id = :id""",
            {**params, "raw": _json(posting.raw)},
        )
        return posting_id, False
    execute(
        connection,
        """INSERT INTO job_posting (id, company_id, source_key, external_id, title, family, location, remote_scope, remote_detail,
           employment_type, rate_min, rate_max, rate_currency, rate_period, url, posted_at, description, tech, is_english, raw)
           VALUES (:id, :company_id, :source_key, :external_id, :title, :family, :location, :remote_scope, :remote_detail,
           :employment_type, :rate_min, :rate_max, :rate_currency, :rate_period, :url, :posted_at, :description, :tech, :is_english, CAST(:raw AS jsonb))""",
        {**params, "raw": _json(posting.raw)},
    )
    return posting_id, True


def close_missing(
    connection: Connection, source_key: str, seen_external_ids: set[str], company_id: str | None = None
) -> int:
    """Postings from this source (and company, for ATS boards) that were not in the latest fetch are closed."""
    sql = "UPDATE job_posting SET closed_at = now() WHERE source_key = :s AND closed_at IS NULL AND NOT (external_id = ANY(:ids))"
    params: dict[str, Any] = {"s": source_key, "ids": list(seen_external_ids)}
    if company_id:
        sql += " AND company_id = :c"
        params["c"] = company_id
    return execute(connection, sql, params)


def _json(value: dict[str, Any]) -> str:
    return orjson.dumps(value, default=str).decode()
