"""Read queries shared by the page controllers and /api."""

from typing import Any

from sqlalchemy import Connection

from opportunity_radar.db import row, rows
from opportunity_radar.service.money import latest_rates, to_inr

OPPORTUNITY_SELECT = """
    SELECT o.*, c.name AS company_name, c.region, c.industry, c.website,
           p.url AS posting_url, p.title AS posting_title, p.location, p.remote_scope, p.remote_detail, p.tech, p.posted_at, p.source_key, p.employment_type,
           n.summary AS need_summary, n.rationale, n.status AS need_status
    FROM opportunity o
    JOIN company c ON c.id = o.company_id
    LEFT JOIN job_posting p ON p.id = o.job_posting_id
    LEFT JOIN need n ON n.id = o.need_id
"""


def with_inr(connection: Connection, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rates = latest_rates(connection)
    for record in records:
        record["value_min_inr"] = to_inr(record["value_min"], record["value_currency"], rates)
        record["value_max_inr"] = to_inr(record["value_max"], record["value_currency"], rates)
    return records


def opportunities(
    connection: Connection, bucket: str | None = None, mode: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: dict[str, Any] = {"limit": limit}
    if bucket:
        clauses.append("o.bucket = :bucket")
        params["bucket"] = bucket
    else:
        clauses.append("o.bucket <> 'dropped'")
    if mode:
        clauses.append("o.mode = :mode")
        params["mode"] = mode
    sql = f"{OPPORTUNITY_SELECT} WHERE {' AND '.join(clauses)} ORDER BY o.score DESC, o.last_scored_at DESC LIMIT :limit"
    return with_inr(connection, rows(connection, sql, params))


def opportunity(connection: Connection, opportunity_id: str) -> dict[str, Any] | None:
    found = row(connection, f"{OPPORTUNITY_SELECT} WHERE o.id = :id", {"id": opportunity_id})
    if not found:
        return None
    found = with_inr(connection, [found])[0]
    found["signals"] = (
        rows(
            connection,
            "SELECT s.* FROM signal s JOIN need_signal ns ON ns.signal_id = s.id WHERE ns.need_id = :n ORDER BY s.observed_at DESC",
            {"n": found["need_id"]},
        )
        if found["need_id"]
        else []
    )
    found["feedback"] = rows(
        connection,
        "SELECT * FROM feedback WHERE opportunity_id = :o ORDER BY created_at DESC",
        {"o": opportunity_id},
    )
    found["outcomes"] = rows(
        connection,
        "SELECT * FROM outcome WHERE opportunity_id = :o ORDER BY created_at DESC",
        {"o": opportunity_id},
    )
    return found


def dropped_recent(connection: Connection) -> list[dict[str, Any]]:
    return rows(
        connection,
        f"{OPPORTUNITY_SELECT} WHERE o.bucket = 'dropped' AND o.dropped_at > now() - interval '7 days' ORDER BY o.dropped_at DESC LIMIT 20",
    )


def region_gaps(connection: Connection) -> list[dict[str, Any]]:
    return rows(
        connection,
        """SELECT g.*, c.name, c.region, c.utc_offset, c.english_ok FROM region_gap g JOIN country c ON c.code = g.country_code
           ORDER BY g.thin, g.score DESC, c.name""",
    )
