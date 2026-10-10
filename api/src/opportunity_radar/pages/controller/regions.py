from fastapi import HTTPException, Request

from opportunity_radar.db import row, rows, transaction
from opportunity_radar.pages import queries
from opportunity_radar.pages.templating import templates
from opportunity_radar.service.classify import ENGINEERING_FAMILIES
from opportunity_radar.service.regions import EVIDENCE_FLOOR, WEIGHTS


def list_page(request: Request):
    with transaction() as connection:
        items = queries.region_gaps(connection)
    return templates.TemplateResponse(
        request, "region_list.html", {"items": items, "weights": WEIGHTS, "evidence_floor": EVIDENCE_FLOOR}
    )


def region_page(request: Request, code: str):
    with transaction() as connection:
        gap = row(
            connection,
            "SELECT g.*, c.name, c.region, c.utc_offset, c.english_ok FROM region_gap g JOIN country c ON c.code = g.country_code WHERE g.country_code = :c",
            {"c": code.upper()},
        )
        if not gap:
            raise HTTPException(404, "No region gap computed for that country")
        postings = rows(
            connection,
            """SELECT p.*, c.name AS company_name,
                      extract(epoch FROM now() - coalesce(p.posted_at, p.first_seen_at)) / 86400 AS days_open
               FROM job_posting p JOIN company c ON c.id = p.company_id
               WHERE p.closed_at IS NULL AND p.is_english AND p.family = ANY(:families) AND :code = ANY(p.countries)
               ORDER BY days_open DESC LIMIT 150""",
            {"families": sorted(ENGINEERING_FAMILIES), "code": gap["country_code"]},
        )
        companies = rows(
            connection,
            """SELECT c.id, c.name, c.website, c.domain, count(DISTINCT p.id) AS open_postings,
                      coalesce(array_agg(DISTINCT s.title) FILTER (WHERE s.id IS NOT NULL), '{}') AS signals,
                      coalesce(array_agg(DISTINCT n.summary) FILTER (WHERE n.id IS NOT NULL), '{}') AS needs
               FROM company c
               JOIN job_posting p ON p.company_id = c.id AND p.closed_at IS NULL AND :code = ANY(p.countries)
               LEFT JOIN signal s ON s.company_id = c.id AND s.expires_at > now()
               LEFT JOIN need n ON n.company_id = c.id AND n.status <> 'expired'
               GROUP BY c.id ORDER BY count(DISTINCT s.id) DESC, open_postings ASC, c.name LIMIT 100""",
            {"code": gap["country_code"]},
        )
        opportunities = rows(
            connection,
            f"""{queries.OPPORTUNITY_SELECT}
                WHERE o.bucket <> 'dropped' AND EXISTS (
                    SELECT 1 FROM job_posting q WHERE q.company_id = o.company_id AND q.closed_at IS NULL AND :code = ANY(q.countries))
                ORDER BY o.score DESC LIMIT 50""",
            {"code": gap["country_code"]},
        )
        opportunities = queries.with_inr(connection, opportunities)
    return templates.TemplateResponse(
        request,
        "region.html",
        {
            "gap": gap,
            "postings": postings,
            "companies": companies,
            "opportunities": opportunities,
            "weights": WEIGHTS,
        },
    )
