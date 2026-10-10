"""Public ATS job-board APIs: Greenhouse, Lever, Ashby. No login, documented endpoints, one request per company."""

from datetime import UTC, datetime
from typing import Any

from loguru import logger

from opportunity_radar.db import scalar, transaction
from opportunity_radar.sources.http import fetch
from opportunity_radar.sources.postings import Posting, close_missing, store

GREENHOUSE = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
LEVER = "https://api.lever.co/v0/postings/{slug}"
ASHBY = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


def _ts(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _greenhouse(slug: str) -> list[dict[str, Any]]:
    body = fetch("greenhouse", GREENHOUSE.format(slug=slug), {"content": "true"}).json()
    return [
        {
            "external_id": str(job["id"]),
            "title": job["title"],
            "url": job["absolute_url"],
            "location": (job.get("location") or {}).get("name", ""),
            "description": job.get("content", ""),
            "posted_at": _ts(job.get("updated_at")),
            "employment_hint": "",
            "remote_hint": None,
            "rate_text": "",
            "raw": job,
        }
        for job in body["jobs"]
    ]


def _lever(slug: str) -> list[dict[str, Any]]:
    body = fetch("lever", LEVER.format(slug=slug), {"mode": "json"}).json()
    result = []
    for job in body:
        categories = job.get("categories") or {}
        salary = job.get("salaryRange") or {}
        rate_text = (
            f"{salary.get('currency', '')} {salary.get('min', '')}-{salary.get('max', '')} per {salary.get('interval', '')}"
            if salary
            else ""
        )
        result.append(
            {
                "external_id": job["id"],
                "title": job["text"],
                "url": job["hostedUrl"],
                "location": categories.get("location", ""),
                "description": job.get("descriptionPlain", "")
                + " "
                + " ".join(item.get("content", "") for item in job.get("lists", [])),
                "posted_at": _ts(job.get("createdAt")),
                "employment_hint": categories.get("commitment", ""),
                "remote_hint": (job.get("workplaceType") == "remote") if job.get("workplaceType") else None,
                "rate_text": rate_text,
                "raw": job,
            }
        )
    return result


def _ashby(slug: str) -> list[dict[str, Any]]:
    body = fetch("ashby", ASHBY.format(slug=slug), {"includeCompensation": "true"}).json()
    return [
        {
            "external_id": job["id"],
            "title": job["title"],
            "url": job["jobUrl"],
            "location": job.get("location", ""),
            "description": job.get("descriptionPlain", ""),
            "posted_at": _ts(job.get("publishedAt")),
            "employment_hint": job.get("employmentType", ""),
            "remote_hint": job.get("isRemote"),
            "rate_text": ((job.get("compensation") or {}).get("compensationTierSummary") or ""),
            "raw": job,
        }
        for job in body["jobs"]
    ]


_FETCHERS = {"greenhouse": _greenhouse, "lever": _lever, "ashby": _ashby}


def ingest_company(
    name: str, domain: str, ats: str, slug: str, region: str, is_ai_native: bool
) -> tuple[int, int]:
    """Returns (seen, new). Raises on a failed fetch so the caller can record the source status."""
    jobs = _FETCHERS[ats](slug)
    seen: set[str] = set()
    new = 0
    company_id = None
    with transaction() as connection:
        for job in jobs:
            posting = Posting(
                company_name=name,
                company_domain=domain,
                company_region=region,
                company_is_ai_native=is_ai_native,
                **job,
            )
            posting_id, is_new = store(connection, ats, posting)
            new += int(is_new)
            seen.add(posting.external_id)
            if company_id is None:
                company_id = scalar(
                    connection, "SELECT company_id FROM job_posting WHERE id = :id", {"id": posting_id}
                )
        if company_id:
            closed = close_missing(connection, ats, seen, company_id)
            if closed:
                logger.info(f"{ats}/{slug}: closed {closed} postings no longer listed")
    logger.info(f"{ats}/{slug}: {len(seen)} postings, {new} new")
    return len(seen), new
