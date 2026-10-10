"""Signals derived from what the sources stored: hiring patterns, AI adoption, old stacks. Each is dated and sourced."""

from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy import Connection

from opportunity_radar.db import execute, rows, transaction
from opportunity_radar.ids import new_id
from opportunity_radar.service.classify import AI_TECH, ENGINEERING_FAMILIES, OLD_STACK

HIRING_WINDOW_DAYS = 90


def add_signal(
    connection: Connection,
    company_id: str,
    cls: str,
    kind: str,
    title: str,
    detail: str,
    strength: float,
    source_key: str,
    source_url: str | None,
    observed_at: datetime,
    expires_at: datetime,
    dedupe_key: str,
) -> bool:
    inserted = execute(
        connection,
        """INSERT INTO signal (id, company_id, class, kind, title, detail, strength, source_key, source_url, observed_at, expires_at, dedupe_key)
           VALUES (:id, :c, :cls, :k, :t, :d, :s, :src, :u, :o, :e, :dk)
           ON CONFLICT (dedupe_key) DO UPDATE SET detail = EXCLUDED.detail, strength = EXCLUDED.strength, expires_at = EXCLUDED.expires_at, observed_at = EXCLUDED.observed_at""",
        {
            "id": new_id(),
            "c": company_id,
            "cls": cls,
            "k": kind,
            "t": title,
            "d": detail,
            "s": strength,
            "src": source_key,
            "u": source_url,
            "o": observed_at,
            "e": expires_at,
            "dk": dedupe_key,
        },
    )
    return inserted == 1


def derive() -> int:
    """Rebuilds the derived signal classes from open postings and technology facts. Idempotent via dedupe keys."""
    now = datetime.now(UTC)
    created = 0
    with transaction() as connection:
        companies = rows(
            connection,
            """SELECT c.id, c.name, c.is_ai_native,
                      array_agg(p.family) AS families, array_agg(p.title) AS titles, array_agg(p.url) AS urls,
                      array_agg(array_to_string(p.tech, ',')) AS techs, bool_and(p.source_key IN ('greenhouse', 'lever', 'ashby')) AS own_board, min(coalesce(p.posted_at, p.first_seen_at)) AS earliest, max(coalesce(p.posted_at, p.first_seen_at)) AS latest,
                      count(*) AS open_count
               FROM company c JOIN job_posting p ON p.company_id = c.id
               WHERE p.closed_at IS NULL AND p.is_english AND coalesce(p.posted_at, p.first_seen_at) > :since
               GROUP BY c.id""",
            {"since": now - timedelta(days=HIRING_WINDOW_DAYS)},
        )
        month = now.strftime("%Y-%m")
        for company in companies:
            engineering = [
                (family, title, url)
                for family, title, url in zip(
                    company["families"], company["titles"], company["urls"], strict=True
                )
                if family in ENGINEERING_FAMILIES
            ]
            families = {family for family, _, _ in engineering}
            core = families & {"backend", "data", "devops", "ml"}
            expires = now + timedelta(days=HIRING_WINDOW_DAYS)
            source_url = engineering[0][2] if engineering else None
            if len(engineering) >= 3:
                sample = "; ".join(title for _, title, _ in engineering[:5])
                created += add_signal(
                    connection,
                    company["id"],
                    "hiring",
                    "hiring_cluster",
                    f"{len(engineering)} open engineering roles",
                    sample,
                    min(1.0, 0.5 + 0.1 * len(engineering)),
                    "derived",
                    source_url,
                    company["latest"],
                    expires,
                    f"hiring_cluster:{company['id']}:{month}",
                )
            if len(core) >= 2:
                created += add_signal(
                    connection,
                    company["id"],
                    "hiring",
                    "multi_family_hiring",
                    f"Hiring across {', '.join(sorted(core))}",
                    "Several engineering families open at once suggests a build-out, not replacement hires",
                    0.7,
                    "derived",
                    source_url,
                    company["latest"],
                    expires,
                    f"multi_family:{company['id']}:{month}",
                )
            if len(engineering) == 1 and company["own_board"]:
                earlier = rows(
                    connection,
                    "SELECT 1 FROM job_posting WHERE company_id = :c AND (closed_at IS NOT NULL OR first_seen_at < :since) LIMIT 1",
                    {"c": company["id"], "since": now - timedelta(days=HIRING_WINDOW_DAYS)},
                )
                if not earlier:
                    family, title, url = engineering[0]
                    created += add_signal(
                        connection,
                        company["id"],
                        "hiring",
                        "first_tech_hire",
                        f"First technical hire: {title}",
                        "Only one engineering posting ever seen for this company",
                        0.6,
                        "derived",
                        url,
                        company["latest"],
                        expires,
                        f"first_tech_hire:{company['id']}",
                    )
            ai_terms = {term for tech in company["techs"] for term in tech.split(",") if term in AI_TECH}
            if ai_terms and not company["is_ai_native"]:
                created += add_signal(
                    connection,
                    company["id"],
                    "ai",
                    "ai_adoption",
                    f"AI adoption: {', '.join(sorted(ai_terms))} named in vacancies",
                    "A non-AI company naming model vendors or LLM work in job posts",
                    0.65,
                    "derived",
                    source_url,
                    company["latest"],
                    expires,
                    f"ai_adoption:{company['id']}:{month}",
                )
        old = rows(
            connection,
            """SELECT company_id, array_agg(value) AS stack, max(source_url) AS url FROM company_fact
               WHERE fact_type = 'technology' AND value = ANY(:old) AND (expires_at IS NULL OR expires_at > now()) GROUP BY company_id""",
            {"old": list(OLD_STACK)},
        )
        for record in old:
            created += add_signal(
                connection,
                record["company_id"],
                "technology",
                "old_stack",
                f"Public site runs on {', '.join(record['stack'])}",
                "Dated web stack; a rebuild or a portal is the usual next step when the business grows",
                0.4,
                "site",
                record["url"],
                now,
                now + timedelta(days=90),
                f"old_stack:{record['company_id']}",
            )
        expired = execute(
            connection, "UPDATE need SET status = 'expired' WHERE status <> 'expired' AND expires_at < now()"
        )
    logger.info(f"signals: {created} new or refreshed; {expired} needs expired")
    return created
