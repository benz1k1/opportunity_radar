"""Funding news from RSS feeds: a 'raises' headline becomes a funding_round signal on the named company."""

import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any

from loguru import logger

from opportunity_radar.db import transaction
from opportunity_radar.service.companies import add_fact, upsert_company
from opportunity_radar.service.signals import add_signal
from opportunity_radar.sources.http import fetch

_RAISES = re.compile(
    r"^(?P<name>[A-Z][\w.&' -]{1,40}?)\s+(?:raises|secures|lands|closes|bags|nets)\s+(?P<amount>[$€£₹]\s?\d[\d.,]*\s?(?:million|billion|m|b|k|crore|cr)?)",
    re.IGNORECASE,
)


def ingest(source_key: str, config: dict[str, Any]) -> tuple[int, int]:
    response = fetch(source_key, config["url"], accept="application/rss+xml, application/xml, text/xml")
    root = ET.fromstring(response.content)
    seen = new = 0
    with transaction() as connection:
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            published = item.findtext("pubDate")
            found = _RAISES.search(title)
            seen += 1
            if not found:
                continue
            observed = parsedate_to_datetime(published) if published else datetime.now(UTC)
            company_id = upsert_company(connection, found.group("name"), None, config.get("region"))
            add_fact(
                connection,
                company_id,
                "funding",
                "round",
                f"{found.group('amount')} ({observed:%b %Y})",
                source_key,
                link,
                ttl_days=365,
            )
            created = add_signal(
                connection,
                company_id,
                "trigger",
                "funding_round",
                f"Raised {found.group('amount')}",
                title,
                0.7,
                source_key,
                link,
                observed,
                observed + timedelta(days=180),
                dedupe_key=f"funding:{link}",
            )
            new += int(created)
    logger.info(f"{source_key}: {seen} items, {new} funding signals")
    return seen, new
