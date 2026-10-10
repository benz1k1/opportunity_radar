"""Turns scored postings and needs into opportunity rows (the packet), and keeps buckets current."""

from decimal import Decimal
from typing import Any

import orjson
from loguru import logger

from opportunity_radar.db import execute, rows, transaction
from opportunity_radar.ids import new_id
from opportunity_radar.service import scoring
from opportunity_radar.service.classify import seniority_of
from opportunity_radar.service.money import latest_rates
from opportunity_radar.service.needs import NEED_KINDS

# Engagement value ranges per need kind, in INR per hour equivalents applied to a typical hour count.
_NEED_HOURS = {
    "platform_expansion": (300, 700),
    "data_platform": (200, 450),
    "ai_integration": (150, 350),
    "first_tech_hire": (150, 300),
    "portal_rebuild": (250, 500),
    "post_funding_buildout": (300, 600),
}


def _profile(connection: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    profile = rows(connection, "SELECT * FROM user_profile ORDER BY created_at LIMIT 1")
    if not profile:
        raise RuntimeError("No user_profile row. Run: python load_data.py")
    skills = rows(
        connection,
        "SELECT name, confidence, aliases FROM skill WHERE profile_id = :p",
        {"p": profile[0]["id"]},
    )
    return profile[0], skills


def _upsert(
    connection: Any,
    mode: str,
    company_id: str,
    need_id: str | None,
    posting_id: str | None,
    title: str,
    scored: scoring.Scored,
    **fields: Any,
) -> None:
    found = rows(
        connection,
        "SELECT id FROM opportunity WHERE mode = :m AND company_id = :c AND need_id IS NOT DISTINCT FROM :n AND job_posting_id IS NOT DISTINCT FROM :p",
        {"m": mode, "c": company_id, "n": need_id, "p": posting_id},
    )
    params = {
        "id": found[0]["id"] if found else new_id(),
        "mode": mode,
        "company_id": company_id,
        "need_id": need_id,
        "posting_id": posting_id,
        "title": title,
        "score": scored.score,
        "dimensions": orjson.dumps(scored.dimensions).decode(),
        "reasons": orjson.dumps(scored.reasons).decode(),
        "sell": fields.get("sell", ""),
        "engagement": fields.get("engagement", ""),
        "value_min": fields.get("value_min"),
        "value_max": fields.get("value_max"),
        "value_currency": fields.get("value_currency"),
        "value_period": fields.get("value_period"),
        "buyer_role": fields.get("buyer_role", ""),
        "why_you": ", ".join(scored.matched_skills) or "profile fit only",
        "action": fields.get("action", ""),
        "bucket": scored.bucket,
    }
    if found:
        execute(
            connection,
            """UPDATE opportunity SET title = :title, score = :score, dimensions = CAST(:dimensions AS jsonb), reasons = CAST(:reasons AS jsonb), sell = :sell,
               engagement = :engagement, value_min = :value_min, value_max = :value_max, value_currency = :value_currency, value_period = :value_period,
               buyer_role = :buyer_role, why_you = :why_you, action = :action, bucket = :bucket, last_scored_at = now(),
               dropped_at = CASE WHEN :bucket = 'dropped' THEN coalesce(dropped_at, now()) ELSE NULL END,
               drop_reason = CASE WHEN :bucket = 'dropped' THEN 'score below threshold' ELSE NULL END
               WHERE id = :id""",
            params,
        )
    else:
        execute(
            connection,
            """INSERT INTO opportunity (id, mode, company_id, need_id, job_posting_id, title, score, dimensions, reasons, sell, engagement, value_min, value_max,
               value_currency, value_period, buyer_role, why_you, action, bucket, dropped_at, drop_reason)
               VALUES (:id, :mode, :company_id, :need_id, :posting_id, :title, :score, CAST(:dimensions AS jsonb), CAST(:reasons AS jsonb), :sell, :engagement,
               :value_min, :value_max, :value_currency, :value_period, :buyer_role, :why_you, :action, :bucket,
               CASE WHEN :bucket = 'dropped' THEN now() END, CASE WHEN :bucket = 'dropped' THEN 'score below threshold' END)""",
            params,
        )


def score_all() -> dict[str, int]:
    counts = {"postings": 0, "needs": 0, "closed": 0}
    with transaction() as connection:
        profile, skills = _profile(connection)
        rates = latest_rates(connection)
        postings = rows(
            connection,
            """SELECT p.*, c.name AS company_name, c.industry FROM job_posting p JOIN company c ON c.id = p.company_id
               WHERE p.closed_at IS NULL AND p.is_english AND p.family IN ('backend', 'data', 'devops', 'ml')""",
        )
        for posting in postings:
            posting["seniority"] = seniority_of(posting["title"])
            scored = scoring.score_posting(posting, {"industry": posting["industry"]}, profile, skills, rates)
            mode = "contract" if posting["employment_type"] == "contract" else "career"
            _upsert(
                connection,
                mode,
                posting["company_id"],
                None,
                posting["id"],
                f"{posting['company_name']} · {posting['title']}",
                scored,
                sell="",
                engagement="contract" if mode == "contract" else "full-time",
                value_min=posting["rate_min"],
                value_max=posting["rate_max"],
                value_currency=posting["rate_currency"],
                value_period=posting["rate_period"],
                buyer_role="Hiring manager",
                action="Apply with a note that quotes the listed stack"
                if scored.bucket == "immediate"
                else "Watch",
            )
            counts["postings"] += 1
        needs = rows(
            connection,
            """SELECT n.*, c.name AS company_name, c.industry,
                      (SELECT count(*) FROM job_posting p WHERE p.company_id = n.company_id AND p.closed_at IS NULL
                       AND p.family IN ('backend', 'data', 'devops', 'ml', 'frontend', 'mobile')) AS open_engineering,
                      (SELECT count(*) FROM job_posting p WHERE p.company_id = n.company_id AND p.closed_at IS NULL) AS open_total
               FROM need n JOIN company c ON c.id = n.company_id WHERE n.status <> 'expired'""",
        )
        for need in needs:
            signals = rows(
                connection,
                "SELECT s.* FROM signal s JOIN need_signal ns ON ns.signal_id = s.id WHERE ns.need_id = :n",
                {"n": need["id"]},
            )
            summary, sell, engagement, buyer, required = NEED_KINDS[need["kind"]]
            scored = scoring.score_need(
                need,
                signals,
                {
                    "industry": need["industry"],
                    "open_engineering": need["open_engineering"],
                    "open_total": need["open_total"],
                },
                profile,
                skills,
                required,
            )
            low, high = _NEED_HOURS[need["kind"]]
            target = Decimal(profile["rate_target_inr_hour"])
            _upsert(
                connection,
                "client",
                need["company_id"],
                need["id"],
                None,
                f"{need['company_name']} · {summary}",
                scored,
                sell=sell,
                engagement=engagement,
                value_min=target * low,
                value_max=target * high,
                value_currency="INR",
                value_period="project",
                buyer_role=buyer,
                action=f"Get an introduction to the {buyer.split(' / ')[0]}; lead with: {signals[0]['title'] if signals else summary}",
            )
            counts["needs"] += 1
        counts["closed"] = execute(
            connection,
            """UPDATE opportunity o SET bucket = 'dropped', dropped_at = now(), drop_reason = 'posting closed'
               FROM job_posting p WHERE o.job_posting_id = p.id AND p.closed_at IS NOT NULL AND o.bucket <> 'dropped'""",
        )
        counts["closed"] += execute(
            connection,
            """UPDATE opportunity o SET bucket = 'dropped', dropped_at = now(), drop_reason = 'need expired'
               FROM need n WHERE o.need_id = n.id AND n.status = 'expired' AND o.bucket <> 'dropped'""",
        )
    logger.info(
        f"scored {counts['postings']} postings and {counts['needs']} needs; {counts['closed']} dropped"
    )
    return counts


def record_run() -> dict[str, Any]:
    with transaction() as connection:
        counts = rows(
            connection,
            "SELECT bucket, count(*) AS n FROM opportunity WHERE bucket <> 'dropped' OR dropped_at > now() - interval '7 days' GROUP BY bucket",
        )
        by_bucket = {record["bucket"]: record["n"] for record in counts}
        summary = {
            "immediate": by_bucket.get("immediate", 0),
            "emerging": by_bucket.get("emerging", 0),
            "consulting": by_bucket.get("consulting", 0),
            "dropped": by_bucket.get("dropped", 0),
        }
        execute(
            connection,
            "INSERT INTO radar_run (id, immediate, emerging, consulting, dropped) VALUES (:id, :i, :e, :c, :d)",
            {
                "id": new_id(),
                "i": summary["immediate"],
                "e": summary["emerging"],
                "c": summary["consulting"],
                "d": summary["dropped"],
            },
        )
    return summary
