"""Remote job boards with public JSON APIs: Remotive and Arbeitnow. English-only filtering happens at store time."""

from datetime import UTC, datetime
from typing import Any

from loguru import logger

from opportunity_radar.db import transaction
from opportunity_radar.sources.http import fetch
from opportunity_radar.sources.postings import Posting, store


def ingest_remotive(config: dict[str, Any]) -> tuple[int, int]:
    seen = new = 0
    for category in config["categories"]:
        body = fetch("remotive", config["url"], {"category": category, "limit": 200}).json()
        with transaction() as connection:
            for job in body["jobs"]:
                posting = Posting(
                    external_id=str(job["id"]),
                    title=job["title"],
                    url=job["url"],
                    company_name=job["company_name"],
                    location=job.get("candidate_required_location", ""),
                    description=job.get("description", ""),
                    posted_at=datetime.fromisoformat(job["publication_date"]).replace(tzinfo=UTC),
                    employment_hint=job.get("job_type", ""),
                    remote_hint=True,
                    rate_text=job.get("salary", ""),
                    raw={"category": job.get("category"), "tags": job.get("tags")},
                )
                _, is_new = store(connection, "remotive", posting)
                seen += 1
                new += int(is_new)
    logger.info(f"remotive: {seen} postings, {new} new")
    return seen, new


def ingest_arbeitnow(config: dict[str, Any], pages: int = 3) -> tuple[int, int]:
    seen = new = 0
    for page in range(1, pages + 1):
        body = fetch("arbeitnow", config["url"], {"page": page}).json()
        with transaction() as connection:
            for job in body["data"]:
                posting = Posting(
                    external_id=job["slug"],
                    title=job["title"],
                    url=job["url"],
                    company_name=job["company_name"],
                    company_region="eu",
                    location=job.get("location", ""),
                    description=job.get("description", ""),
                    posted_at=datetime.fromtimestamp(job["created_at"], tz=UTC),
                    employment_hint=" ".join(job.get("job_types") or []),
                    remote_hint=bool(job.get("remote")),
                    raw={"tags": job.get("tags")},
                )
                _, is_new = store(connection, "arbeitnow", posting)
                seen += 1
                new += int(is_new)
    logger.info(f"arbeitnow: {seen} postings, {new} new")
    return seen, new
