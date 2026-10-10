"""Scoring: weighted dimensions, each 0–100, with a reason per dimension. Weights vary by mode; dimensions do not."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from opportunity_radar.service.money import to_inr_per_hour

WEIGHTS: dict[str, dict[str, float]] = {
    "career": {
        "technical": 0.30,
        "seniority": 0.15,
        "remote": 0.15,
        "rate": 0.15,
        "recency": 0.10,
        "competition": 0.10,
        "payment": 0.05,
    },
    "contract": {
        "technical": 0.30,
        "seniority": 0.10,
        "remote": 0.15,
        "rate": 0.20,
        "recency": 0.10,
        "competition": 0.10,
        "payment": 0.05,
    },
    "client": {
        "technical": 0.25,
        "evidence": 0.30,
        "domain": 0.10,
        "recency": 0.10,
        "competition": 0.10,
        "payment": 0.15,
    },
}
_SENIORITY_ORDER = {"junior": 0, "mid": 1, "senior": 2, "lead": 3}
_SOURCE_PAYMENT = {
    "greenhouse": 90,
    "lever": 90,
    "ashby": 90,
    "remotive": 70,
    "arbeitnow": 65,
    "derived": 60,
    "rss": 60,
}
_INDIA_FRIENDLY = ("india", "apac", "asia", "emea", "worldwide", "anywhere", "global")
NICHE_TECH = frozenset({"java", "kafka", "scala", "spring", "etl", "airflow", "microservices"})


@dataclass
class Scored:
    score: int
    dimensions: dict[str, int]
    reasons: list[str]
    matched_skills: list[str]
    bucket: str


def _skill_index(skills: list[dict[str, Any]]) -> dict[str, tuple[str, float]]:
    index: dict[str, tuple[str, float]] = {}
    for skill in skills:
        for name in (skill["name"], *skill["aliases"]):
            index[name.lower()] = (skill["name"], float(skill["confidence"]))
    return index


def _technical(required: list[str], skills: list[dict[str, Any]]) -> tuple[int, list[str]]:
    index = _skill_index(skills)
    matched: dict[str, float] = {}
    for term in required:
        hit = index.get(term.lower())
        if hit:
            matched[hit[0]] = max(matched.get(hit[0], 0.0), hit[1])
    if not required:
        return 50, []
    coverage = sum(matched.values()) / max(len(required), 3)
    return int(min(100, round(coverage * 100 + (20 if len(matched) >= 3 else 0)))), sorted(matched)


def _rate(posting: dict[str, Any], profile: dict[str, Any], rates: dict[str, Decimal]) -> tuple[int, str]:
    hourly = to_inr_per_hour(
        posting["rate_max"] or posting["rate_min"], posting["rate_currency"], posting["rate_period"], rates
    )
    if hourly is None:
        return 60, "rate not stated"
    floor, target = Decimal(profile["rate_floor_inr_hour"]), Decimal(profile["rate_target_inr_hour"])
    if hourly >= target:
        return 100, f"≈₹{hourly:,.0f}/h, at or above target"
    if hourly >= floor:
        return int(
            70 + 30 * float((hourly - floor) / max(target - floor, Decimal(1)))
        ), f"≈₹{hourly:,.0f}/h, between floor and target"
    return int(40 * float(hourly / floor)), f"≈₹{hourly:,.0f}/h, below the ₹{floor:,.0f}/h floor"


def _recency(when: datetime | None) -> tuple[int, str]:
    if when is None:
        return 50, "date unknown"
    days = (datetime.now(UTC) - when).days
    for limit, value in ((3, 100), (7, 95), (30, 80), (60, 60), (90, 40)):
        if days <= limit:
            return value, f"{days} days old"
    return 20, f"{days} days old"


def score_posting(
    posting: dict[str, Any],
    company: dict[str, Any],
    profile: dict[str, Any],
    skills: list[dict[str, Any]],
    rates: dict[str, Decimal],
) -> Scored:
    mode = "contract" if posting["employment_type"] == "contract" else "career"
    dims: dict[str, int] = {}
    reasons: list[str] = []

    dims["technical"], matched = _technical(posting["tech"], skills)
    reasons.append(f"technical: {', '.join(matched) if matched else 'no listed tech matches the profile'}")

    gap = _SENIORITY_ORDER.get(posting["seniority"], 1) - _SENIORITY_ORDER[profile["seniority"]]
    dims["seniority"] = {0: 100, 1: 75, -1: 70, 2: 40, -2: 35}.get(gap, 20)
    if gap <= -2:
        reasons.append("seniority: over-qualified; employers skip these applicants")
    elif gap >= 2:
        reasons.append("seniority: role is well above the profile")
    else:
        reasons.append(f"seniority: {posting['seniority']} role")

    scope, detail = posting["remote_scope"], (posting["remote_detail"] or "").lower()
    if scope == "worldwide":
        dims["remote"] = 100
    elif scope in ("region", "country"):
        dims["remote"] = 100 if any(word in detail for word in _INDIA_FRIENDLY) else 25
    elif scope == "onsite":
        dims["remote"] = 0 if profile["remote_only"] else 50
    else:
        dims["remote"] = 60
    reasons.append(f"remote: {scope}{f' ({posting["remote_detail"]})' if posting['remote_detail'] else ''}")

    dims["rate"], why = _rate(posting, profile, rates)
    reasons.append(f"rate: {why}")
    dims["recency"], why = _recency(posting["posted_at"] or posting["first_seen_at"])
    reasons.append(f"recency: {why}")

    competition = 50
    if set(posting["tech"]) & NICHE_TECH:
        competition += 20
    if posting["seniority"] in ("senior", "lead"):
        competition += 15
    if scope == "worldwide":
        competition -= 20
    if dims["recency"] >= 95:
        competition -= 10
    if mode == "contract":
        competition += 10
    dims["competition"] = max(0, min(100, competition))
    reasons.append(
        f"competition: {'low' if competition >= 70 else 'medium' if competition >= 45 else 'high'} (estimated)"
    )

    dims["payment"] = _SOURCE_PAYMENT.get(posting["source_key"], 50)
    reasons.append(
        f"payment risk: {'low' if dims['payment'] >= 85 else 'medium'} ({posting['source_key']} listing)"
    )

    total = int(round(sum(dims[name] * weight for name, weight in WEIGHTS[mode].items())))
    if dims["remote"] == 0:
        total = min(total, 30)
        reasons.append("hard filter: onsite and the profile is remote-only")
    if gap <= -2:
        total = min(total, 50)
        reasons.append("hard filter: junior or intern role for a senior profile")
    bucket = "immediate" if total >= 70 else "emerging" if total >= 45 else "dropped"
    return Scored(total, dims, reasons, matched, bucket)


def score_need(
    need: dict[str, Any],
    signals: list[dict[str, Any]],
    company: dict[str, Any],
    profile: dict[str, Any],
    skills: list[dict[str, Any]],
    required: tuple[str, ...],
) -> Scored:
    dims: dict[str, int] = {}
    reasons: list[str] = []
    dims["technical"], matched = _technical(list(required), skills)
    reasons.append(f"technical: {', '.join(matched) if matched else 'weak fit'}")

    strength = max((float(signal["strength"]) for signal in signals), default=0.0)
    direct = sum(1 for signal in signals if signal["class"] in ("direct", "trigger"))
    dims["evidence"] = int(min(100, 30 * len(signals) + 40 * strength + 10 * direct))
    reasons.append(
        f"evidence: {len(signals)} signal{'s' if len(signals) != 1 else ''}, strongest {strength:.1f}"
    )

    industry = (company["industry"] or "").lower()
    dims["domain"] = 100 if industry and industry in profile["domains"] else 60 if not industry else 40
    reasons.append(f"domain: {company['industry'] or 'unknown'}")

    newest = max((signal["observed_at"] for signal in signals), default=None)
    dims["recency"], why = _recency(newest)
    reasons.append(f"recency: {why}")

    open_engineering = int(company.get("open_engineering") or 0)
    open_total = int(company.get("open_total") or 0)
    large = open_engineering >= 40 or open_total >= 80
    mid = open_engineering >= 15 or open_total >= 40
    if large:
        dims["competition"] = 15
        reasons.append(
            f"size: {open_total} open roles ({open_engineering} engineering); a large org buys through vendors, not individuals"
        )
    elif mid:
        dims["competition"] = 45
        reasons.append(
            f"size: {open_total} open roles ({open_engineering} engineering); mid-size, reachable with an introduction"
        )
    elif any(signal["kind"] == "hiring_cluster" for signal in signals):
        dims["competition"] = 65
        reasons.append("competition: the company is hiring openly for it")
    else:
        dims["competition"] = 85
        reasons.append("competition: nothing posted publicly for this need")

    dims["payment"] = 80 if any(signal["kind"] == "funding_round" for signal in signals) else 60
    reasons.append("payment: funded recently" if dims["payment"] >= 80 else "payment: funding unknown")

    total = int(round(sum(dims[name] * weight for name, weight in WEIGHTS["client"].items())))
    if large:
        total = min(total, 55)
    elif mid:
        total = min(total, 72)
    if need["status"] == "emerging":
        total = min(total, 64)
    bucket = "consulting" if total >= 65 else "emerging" if total >= 40 else "dropped"
    return Scored(total, dims, reasons, matched, bucket)
