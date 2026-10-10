"""Company rows and Company DNA facts."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import Connection

from opportunity_radar.db import execute, row
from opportunity_radar.ids import new_id


def upsert_company(
    connection: Connection, name: str, domain: str | None, region: str | None, is_ai_native: bool = False
) -> str:
    name = name.strip()
    domain = (domain or "").strip().lower() or None
    found = None
    if domain:
        found = row(connection, "SELECT id FROM company WHERE domain = :d", {"d": domain})
    if not found:
        found = row(connection, "SELECT id FROM company WHERE lower(name) = lower(:n)", {"n": name})
    if found:
        execute(
            connection,
            "UPDATE company SET domain = COALESCE(domain, :d), region = COALESCE(region, :r), is_ai_native = is_ai_native OR :ai, updated_at = now() WHERE id = :id",
            {"id": found["id"], "d": domain, "r": region, "ai": is_ai_native},
        )
        return found["id"]
    company_id = new_id()
    execute(
        connection,
        "INSERT INTO company (id, name, domain, website, region, is_ai_native) VALUES (:id, :n, :d, :w, :r, :ai)",
        {
            "id": company_id,
            "n": name,
            "d": domain,
            "w": f"https://{domain}" if domain else None,
            "r": region,
            "ai": is_ai_native,
        },
    )
    return company_id


def add_fact(
    connection: Connection,
    company_id: str,
    fact_type: str,
    key: str,
    value: str,
    source_key: str,
    source_url: str | None = None,
    ttl_days: int | None = 365,
) -> None:
    expires = datetime.now(UTC) + timedelta(days=ttl_days) if ttl_days else None
    execute(
        connection,
        """INSERT INTO company_fact (id, company_id, fact_type, key, value, source_key, source_url, expires_at)
           VALUES (:id, :c, :t, :k, :v, :s, :u, :e)
           ON CONFLICT (company_id, fact_type, key, value) DO UPDATE SET observed_at = now(), expires_at = EXCLUDED.expires_at, source_url = EXCLUDED.source_url""",
        {
            "id": new_id(),
            "c": company_id,
            "t": fact_type,
            "k": key,
            "v": value,
            "s": source_key,
            "u": source_url,
            "e": expires,
        },
    )
