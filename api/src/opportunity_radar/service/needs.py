"""Needs: what IT work the signals suggest. Rule-based first; the LLM pass (when enabled) adds needs the rules
cannot express but must still cite signals. No signal, no need."""

from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import Connection

from opportunity_radar.config import LLM_API_KEY, LLM_ENABLED, LLM_MODEL
from opportunity_radar.db import execute, rows, transaction
from opportunity_radar.ids import new_id

# kind -> (summary, sell, engagement, buyer role, skills the need calls for)
NEED_KINDS: dict[str, tuple[str, str, str, str, tuple[str, ...]]] = {
    "platform_expansion": (
        "Backend / platform expansion",
        "Backend/API architecture and delivery capacity while the team hires",
        "3–6 months, fractional or full-time contract",
        "CTO / VP Engineering",
        ("java", "python", "microservices", "backend architecture", "postgresql", "kafka"),
    ),
    "data_platform": (
        "Data platform build-out",
        "Data pipelines, ETL and integration between systems",
        "2–4 months",
        "CTO / Head of Data",
        ("etl", "sql", "python", "airflow", "postgresql"),
    ),
    "ai_integration": (
        "AI integration",
        "LLM integration, evaluation harness and the data pipelines behind it",
        "4–10 weeks",
        "CTO / Head of Product",
        ("llm integration", "python", "etl", "backend architecture"),
    ),
    "first_tech_hire": (
        "First technical hire",
        "Fractional backend lead before, or instead of, the first hire",
        "3 months part-time",
        "Founder / COO",
        ("backend architecture", "java", "python", "aws"),
    ),
    "portal_rebuild": (
        "Customer portal / platform rebuild",
        "Backend/API and a modern customer portal replacing the dated stack",
        "6–12 weeks",
        "Founder / Head of Operations",
        ("backend architecture", "python", "react", "postgresql"),
    ),
    "post_funding_buildout": (
        "Post-funding build-out",
        "Architecture and delivery capacity for the roadmap the round was raised for",
        "3–6 months",
        "CTO / Founder",
        ("backend architecture", "java", "python", "aws"),
    ),
}


def _upsert_need(
    connection: Connection,
    company_id: str,
    kind: str,
    rationale: str,
    signal_ids: list[str],
    detected_by: str,
    strength: float,
) -> str:
    summary = NEED_KINDS[kind][0]
    status = "active" if (len(signal_ids) >= 2 or strength >= 0.7) else "emerging"
    expires = datetime.now(UTC) + timedelta(days=120)
    found = rows(
        connection, "SELECT id FROM need WHERE company_id = :c AND kind = :k", {"c": company_id, "k": kind}
    )
    need_id = found[0]["id"] if found else new_id()
    execute(
        connection,
        """INSERT INTO need (id, company_id, kind, summary, rationale, status, detected_by, expires_at)
           VALUES (:id, :c, :k, :s, :r, :st, :by, :e)
           ON CONFLICT (company_id, kind) DO UPDATE SET rationale = EXCLUDED.rationale, status = EXCLUDED.status, detected_by = EXCLUDED.detected_by,
           detected_at = now(), expires_at = EXCLUDED.expires_at""",
        {
            "id": need_id,
            "c": company_id,
            "k": kind,
            "s": summary,
            "r": rationale,
            "st": status,
            "by": detected_by,
            "e": expires,
        },
    )
    execute(connection, "DELETE FROM need_signal WHERE need_id = :n", {"n": need_id})
    for signal_id in signal_ids:
        execute(
            connection,
            "INSERT INTO need_signal (need_id, signal_id) VALUES (:n, :s) ON CONFLICT DO NOTHING",
            {"n": need_id, "s": signal_id},
        )
    return need_id


def _rules(connection: Connection, company: dict[str, Any], signals: list[dict[str, Any]]) -> int:
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for signal in signals:
        by_kind.setdefault(signal["kind"], []).append(signal)
    families = set(company["families"] or [])
    created = 0

    def ids(*kinds: str) -> list[str]:
        return [signal["id"] for kind in kinds for signal in by_kind.get(kind, [])]

    def rationale(*kinds: str) -> str:
        return " · ".join(signal["title"] for kind in kinds for signal in by_kind.get(kind, []))

    def strength(*kinds: str) -> float:
        values = [float(signal["strength"]) for kind in kinds for signal in by_kind.get(kind, [])]
        return max(values) if values else 0.0

    kinds: tuple[str, ...]
    if "hiring_cluster" in by_kind or "multi_family_hiring" in by_kind:
        kinds = ("hiring_cluster", "multi_family_hiring", "funding_round")
        _upsert_need(
            connection,
            company["id"],
            "platform_expansion",
            rationale(*kinds),
            ids(*kinds),
            "rule:hiring",
            strength(*kinds),
        )
        created += 1
    if "data" in families and ("hiring_cluster" in by_kind or "multi_family_hiring" in by_kind):
        kinds = ("multi_family_hiring", "hiring_cluster")
        _upsert_need(
            connection,
            company["id"],
            "data_platform",
            f"Data roles open · {rationale(*kinds)}",
            ids(*kinds),
            "rule:data",
            strength(*kinds),
        )
        created += 1
    if "ai_adoption" in by_kind:
        kinds = ("ai_adoption", "hiring_cluster", "funding_round")
        _upsert_need(
            connection,
            company["id"],
            "ai_integration",
            rationale(*kinds),
            ids(*kinds),
            "rule:ai",
            strength(*kinds),
        )
        created += 1
    if "first_tech_hire" in by_kind:
        kinds = ("first_tech_hire", "funding_round", "old_stack")
        _upsert_need(
            connection,
            company["id"],
            "first_tech_hire",
            rationale(*kinds),
            ids(*kinds),
            "rule:first_hire",
            strength(*kinds),
        )
        created += 1
    if "old_stack" in by_kind and (
        "hiring_cluster" in by_kind or "funding_round" in by_kind or "first_tech_hire" in by_kind
    ):
        kinds = ("old_stack", "hiring_cluster", "funding_round", "first_tech_hire")
        _upsert_need(
            connection,
            company["id"],
            "portal_rebuild",
            rationale(*kinds),
            ids(*kinds),
            "rule:old_stack",
            strength(*kinds),
        )
        created += 1
    if "funding_round" in by_kind and not (
        {"hiring_cluster", "multi_family_hiring", "ai_adoption"} & by_kind.keys()
    ):
        _upsert_need(
            connection,
            company["id"],
            "post_funding_buildout",
            rationale("funding_round"),
            ids("funding_round"),
            "rule:funding",
            0.5,
        )
        created += 1
    return created


class _LlmNeed(BaseModel):
    kind: str = Field(description=f"One of: {', '.join(NEED_KINDS)}")
    rationale: str = Field(
        description="One or two sentences built only from the listed signals and facts, quoting them"
    )
    signal_ids: list[str] = Field(description="Ids of the signals this need rests on; at least one")
    confidence: float = Field(ge=0, le=1)


class _LlmNeeds(BaseModel):
    needs: list[_LlmNeed]


_SYSTEM = (
    "You read evidence about one company and name the IT work it probably needs from an independent backend/data consultant. "
    "Use only the signals and facts given. Every need must cite signal ids. If the evidence does not support a need, return an empty list. "
    "Never invent a problem the company 'probably has'."
)


def _llm(
    connection: Connection,
    company: dict[str, Any],
    signals: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> int:
    import anthropic  # noqa: PLC0415 — optional feature; only imported when llm.enabled is true

    client = anthropic.Anthropic(api_key=LLM_API_KEY)
    evidence = "\n".join(
        f"- signal {s['id']} [{s['kind']}, {s['observed_at']:%Y-%m-%d}]: {s['title']} — {s['detail']}"
        for s in signals
    )
    dna = "\n".join(f"- {f['fact_type']}/{f['key']}: {f['value']}" for f in facts)
    response = client.messages.parse(
        model=LLM_MODEL,
        max_tokens=4000,
        system=_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Company: {company['name']}\nOpen roles: {', '.join(company['titles'] or [])}\n\nSignals:\n{evidence}\n\nFacts:\n{dna or '- none'}",
            }
        ],
        output_format=_LlmNeeds,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        logger.warning(f"llm needs: no output for {company['name']} (stop_reason={response.stop_reason})")
        return 0
    known = {signal["id"] for signal in signals}
    created = 0
    for need in response.parsed_output.needs:
        cited = [signal_id for signal_id in need.signal_ids if signal_id in known]
        if need.kind not in NEED_KINDS or not cited:
            continue
        _upsert_need(connection, company["id"], need.kind, need.rationale, cited, "llm", need.confidence)
        created += 1
    return created


def detect() -> int:
    created = 0
    with transaction() as connection:
        companies = rows(
            connection,
            """SELECT c.id, c.name, c.is_ai_native,
                      (SELECT array_agg(DISTINCT family) FROM job_posting p WHERE p.company_id = c.id AND p.closed_at IS NULL) AS families,
                      (SELECT array_agg(title) FROM job_posting p WHERE p.company_id = c.id AND p.closed_at IS NULL) AS titles
               FROM company c WHERE EXISTS (SELECT 1 FROM signal s WHERE s.company_id = c.id AND s.expires_at > now())""",
        )
        for company in companies:
            if company["is_ai_native"]:
                continue  # an AI lab hiring engineers is not a client need; its postings are contract/career opportunities instead
            signals = rows(
                connection,
                "SELECT * FROM signal WHERE company_id = :c AND expires_at > now() ORDER BY observed_at DESC",
                {"c": company["id"]},
            )
            created += _rules(connection, company, signals)
            if LLM_ENABLED:
                facts = rows(
                    connection,
                    "SELECT fact_type, key, value FROM company_fact WHERE company_id = :c AND (expires_at IS NULL OR expires_at > now())",
                    {"c": company["id"]},
                )
                created += _llm(connection, company, signals, facts)
    logger.info(f"needs: {created} upserted")
    return created
