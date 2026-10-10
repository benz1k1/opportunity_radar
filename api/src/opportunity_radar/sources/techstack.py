"""Technology archaeology: fingerprint a company's public homepage. Headers and HTML markers only."""

import re

from loguru import logger

from opportunity_radar.db import rows, transaction
from opportunity_radar.service.companies import add_fact
from opportunity_radar.sources.http import fetch

_MARKERS: dict[str, tuple[str, ...]] = {
    "wordpress": ("wp-content", "wp-includes"),
    "woocommerce": ("woocommerce",),
    "shopify": ("cdn.shopify.com", "shopify"),
    "react": ("react-dom", "__next", "data-reactroot", "_next/static"),
    "nextjs": ("_next/static",),
    "angular": ("ng-version",),
    "vue": ("data-v-", "__nuxt"),
    "webflow": ("webflow",),
    "wix": ("wix.com", "wixstatic"),
    "squarespace": ("squarespace",),
    "hubspot": ("hs-scripts", "hubspot"),
    "segment": ("cdn.segment.com",),
    "intercom": ("intercom",),
    "cloudflare": ("cf-ray", "cloudflare"),
    "google-analytics": ("googletagmanager", "google-analytics"),
    "jquery": ("jquery",),
    "bootstrap": ("bootstrap.min",),
}
_GENERATOR = re.compile(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', re.IGNORECASE)


def scan(limit: int = 20) -> int:
    with transaction() as connection:
        companies = rows(
            connection,
            """SELECT c.id, c.name, c.website FROM company c
               WHERE c.website IS NOT NULL AND NOT EXISTS (
                   SELECT 1 FROM company_fact f WHERE f.company_id = c.id AND f.fact_type = 'technology' AND f.observed_at > now() - interval '30 days')
               ORDER BY c.updated_at DESC LIMIT :n""",
            {"n": limit},
        )
    scanned = 0
    for company in companies:
        try:
            response = fetch("site", company["website"], accept="text/html")
        except Exception as failed:  # noqa: BLE001 — external site; one failure must not stop the scan
            logger.warning(f"techstack: {company['name']} ({company['website']}) failed: {failed}")
            continue
        text = response.text.lower()
        headers = " ".join(f"{k}: {v}" for k, v in response.headers.items()).lower()
        found = sorted(
            name
            for name, markers in _MARKERS.items()
            if any(marker in text or marker in headers for marker in markers)
        )
        generator = _GENERATOR.search(response.text)
        with transaction() as connection:
            for name in found:
                add_fact(
                    connection,
                    company["id"],
                    "technology",
                    "web",
                    name,
                    "site",
                    company["website"],
                    ttl_days=90,
                )
            if generator:
                add_fact(
                    connection,
                    company["id"],
                    "technology",
                    "generator",
                    generator.group(1).strip()[:80],
                    "site",
                    company["website"],
                    ttl_days=90,
                )
            for header in ("server", "x-powered-by"):
                if response.headers.get(header):
                    add_fact(
                        connection,
                        company["id"],
                        "technology",
                        header,
                        response.headers[header][:80],
                        "site",
                        company["website"],
                        ttl_days=90,
                    )
        scanned += 1
        logger.info(f"techstack: {company['name']}: {', '.join(found) or 'nothing recognised'}")
    return scanned
