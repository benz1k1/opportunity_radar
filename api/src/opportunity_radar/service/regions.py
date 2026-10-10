"""Region gaps: which countries show thin local IT supply, small budgets and shallow in-house engineering,
read off open English engineering postings and live signals. The place a senior consultant who is cheap
for that market sells best.

Every dimension is computed from stored, sourced rows; nothing here is a hand-written ranking of countries.
A country with fewer postings than EVIDENCE_FLOOR is listed as `thin` and capped so it cannot top the table.
"""

from decimal import Decimal
from statistics import median
from typing import Any

import orjson
from loguru import logger

from opportunity_radar.db import execute, rows, transaction
from opportunity_radar.service.classify import ENGINEERING_FAMILIES, seniority_of
from opportunity_radar.service.money import latest_rates, to_inr_per_hour

EVIDENCE_FLOOR = 5
THIN_CAP = 50
STALE_DAYS = 45
WEIGHTS: dict[str, float] = {
    "shortage": 0.25,  # roles stay open: the local market is not filling them
    "low_depth": 0.25,  # few engineering roles per company, first-hire / old-stack / AI-adoption signals
    "affordability": 0.20,  # posted rates sit between the profile floor and target: cheap for them, fine for us
    "offshore_open": 0.15,  # worldwide / regional remote or contract terms: deliverable from India
    "senior_demand": 0.10,  # senior and lead titles dominate: they want expertise, not hands
    "timezone": 0.05,  # working-hour overlap with IST
}
SHALLOW_SIGNALS = ("first_tech_hire", "old_stack", "ai_adoption")
# The draft scopes contract work from ₹400/h ($5/h) upward; a parsed "rate" below that is a stray number in
# the text (a "€1" or "2 €" in a description), not a price, and is left out of the median.
MIN_PLAUSIBLE_INR_HOUR = Decimal(400)
IST_OFFSET = Decimal("5.5")


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _hourly_inr(posting: dict[str, Any], rates: dict[str, Decimal]) -> Decimal | None:
    amount = posting["rate_max"] if posting["rate_max"] is not None else posting["rate_min"]
    return to_inr_per_hour(amount, posting["rate_currency"], posting["rate_period"], rates)


def _affordability(rates_inr: list[Decimal], floor: Decimal, target: Decimal) -> tuple[int, str]:
    if not rates_inr:
        return 50, "affordability: no posted rates in this country"
    mid = median(rates_inr)
    if mid < floor:
        return 0, f"affordability: median posted rate ₹{mid:,.0f}/h is below the profile floor"
    if mid <= target:
        return 100, f"affordability: median posted rate ₹{mid:,.0f}/h sits between floor and target"
    if mid <= target * 3:
        score = 100 - int(70 * float((mid - target) / (target * 2)))
        return (
            score,
            f"affordability: median posted rate ₹{mid:,.0f}/h is above target; price is not the lever",
        )
    return 30, f"affordability: median posted rate ₹{mid:,.0f}/h; they can afford local seniors"


def compute() -> int:
    """Rebuilds region_gap for every country with at least one open English engineering posting."""
    with transaction() as connection:
        profile = rows(
            connection,
            "SELECT rate_floor_inr_hour, rate_target_inr_hour FROM user_profile ORDER BY created_at LIMIT 1",
        )
        if not profile:
            raise RuntimeError("No user_profile row. Run: python load_data.py")
        floor, target = (
            Decimal(profile[0]["rate_floor_inr_hour"]),
            Decimal(profile[0]["rate_target_inr_hour"]),
        )
        countries = {record["code"]: record for record in rows(connection, "SELECT * FROM country")}
        fx = latest_rates(connection)
        postings = rows(
            connection,
            """SELECT p.id, p.company_id, p.title, p.remote_scope, p.employment_type,
                      p.rate_min, p.rate_max, p.rate_currency, p.rate_period,
                      extract(epoch FROM now() - coalesce(p.posted_at, p.first_seen_at)) / 86400 AS days_open,
                      code
               FROM job_posting p, unnest(p.countries) AS code
               WHERE p.closed_at IS NULL AND p.is_english AND p.family = ANY(:families)""",
            {"families": sorted(ENGINEERING_FAMILIES)},
        )
        shallow = {
            record["company_id"]: record["kinds"]
            for record in rows(
                connection,
                "SELECT company_id, array_agg(DISTINCT kind) AS kinds FROM signal WHERE expires_at > now() AND kind = ANY(:kinds) GROUP BY company_id",
                {"kinds": list(SHALLOW_SIGNALS)},
            )
        }
        by_country: dict[str, list[dict[str, Any]]] = {}
        for posting in postings:
            by_country.setdefault(posting["code"], []).append(posting)

        written = 0
        for code, items in by_country.items():
            country = countries.get(code)
            if country is None:
                logger.warning(f"regions: {code} resolved from postings but is missing from the country seed")
                continue
            companies = {item["company_id"] for item in items}
            days = [float(item["days_open"]) for item in items]
            median_days = median(days)
            stale_share = sum(1 for day in days if day >= STALE_DAYS) / len(days)
            per_company = len(items) / len(companies)
            shallow_companies = sum(1 for company in companies if company in shallow)
            shallow_share = shallow_companies / len(companies)
            offshore_share = sum(
                1
                for item in items
                if item["remote_scope"] in ("worldwide", "region") or item["employment_type"] == "contract"
            ) / len(items)
            senior_share = sum(
                1 for item in items if seniority_of(item["title"]) in ("senior", "lead")
            ) / len(items)
            hourly = [
                rate
                for rate in (_hourly_inr(item, fx) for item in items)
                if rate is not None and rate >= MIN_PLAUSIBLE_INR_HOUR
            ]
            offset = Decimal(country["utc_offset"])
            tz_gap = abs(offset - IST_OFFSET)

            dims: dict[str, int] = {}
            reasons: list[str] = []
            dims["shortage"] = int(100 * (0.6 * _clamp((median_days - 14) / 76) + 0.4 * stale_share))
            reasons.append(
                f"shortage: roles open a median {median_days:.0f} days, {stale_share:.0%} open {STALE_DAYS}+ days"
            )
            dims["low_depth"] = int(100 * (0.5 * _clamp((8 - per_company) / 6.5) + 0.5 * shallow_share))
            reasons.append(
                f"low depth: {per_company:.1f} engineering roles per company, {shallow_companies} of {len(companies)} companies with first-hire / old-stack / AI-adoption signals"
            )
            dims["affordability"], why = _affordability(hourly, floor, target)
            reasons.append(why + (f" ({len(hourly)} rated postings)" if hourly else ""))
            dims["offshore_open"] = int(100 * offshore_share)
            reasons.append(
                f"offshore-open: {offshore_share:.0%} of roles are worldwide/regional remote or contract"
            )
            dims["senior_demand"] = int(100 * senior_share)
            reasons.append(f"senior demand: {senior_share:.0%} of titles are senior or lead")
            dims["timezone"] = int(100 * _clamp(float((10 - tz_gap) / 7)))
            reasons.append(f"timezone: {tz_gap:g}h from IST")
            if not country["english_ok"]:
                reasons.append(
                    "note: English is not the usual working language; only the English postings are counted"
                )

            score = int(round(sum(dims[name] * weight for name, weight in WEIGHTS.items())))
            thin = len(items) < EVIDENCE_FLOOR
            if thin:
                score = min(score, THIN_CAP)
                reasons.insert(
                    0,
                    f"thin evidence: only {len(items)} postings (floor {EVIDENCE_FLOOR}); score capped at {THIN_CAP}",
                )
            metrics = {
                "postings": len(items),
                "companies": len(companies),
                "median_days_open": round(median_days, 1),
                "stale_share": round(stale_share, 3),
                "per_company": round(per_company, 2),
                "shallow_companies": shallow_companies,
                "rated_postings": len(hourly),
                "median_rate_inr_hour": float(round(median(hourly))) if hourly else None,
                "offshore_share": round(offshore_share, 3),
                "senior_share": round(senior_share, 3),
                "utc_offset": float(offset),
            }
            written += execute(
                connection,
                """INSERT INTO region_gap (country_code, score, thin, dimensions, metrics, reasons, computed_at)
                   VALUES (:c, :s, :t, CAST(:d AS jsonb), CAST(:m AS jsonb), CAST(:r AS jsonb), now())
                   ON CONFLICT (country_code) DO UPDATE SET score = EXCLUDED.score, thin = EXCLUDED.thin, dimensions = EXCLUDED.dimensions,
                       metrics = EXCLUDED.metrics, reasons = EXCLUDED.reasons, computed_at = now()""",
                {
                    "c": code,
                    "s": score,
                    "t": thin,
                    "d": orjson.dumps(dims).decode(),
                    "m": orjson.dumps(metrics).decode(),
                    "r": orjson.dumps(reasons).decode(),
                },
            )
        removed = execute(
            connection,
            "DELETE FROM region_gap WHERE country_code <> ALL(:codes)",
            {"codes": list(by_country)},
        )
    logger.info(f"regions: {written} countries scored, {removed} dropped for lack of open postings")
    return written
