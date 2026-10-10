from fastapi import HTTPException, Request

from opportunity_radar.db import row, rows, transaction
from opportunity_radar.pages.templating import templates


def list_page(request: Request, q: str = ""):
    with transaction() as connection:
        items = rows(
            connection,
            """SELECT c.*, (SELECT count(*) FROM job_posting p WHERE p.company_id = c.id AND p.closed_at IS NULL) AS open_postings,
                      (SELECT count(*) FROM signal s WHERE s.company_id = c.id AND s.expires_at > now()) AS live_signals,
                      (SELECT count(*) FROM need n WHERE n.company_id = c.id AND n.status <> 'expired') AS needs
               FROM company c WHERE (:q = '' OR c.name ILIKE '%' || :q || '%')
               ORDER BY live_signals DESC, open_postings DESC, c.name LIMIT 300""",
            {"q": q},
        )
    return templates.TemplateResponse(request, "company_list.html", {"items": items, "q": q})


def company_page(request: Request, company_id: str):
    with transaction() as connection:
        company = row(connection, "SELECT * FROM company WHERE id = :id", {"id": company_id})
        if not company:
            raise HTTPException(404, "No such company")
        context = {
            "company": company,
            "facts": rows(
                connection,
                "SELECT * FROM company_fact WHERE company_id = :c ORDER BY fact_type, observed_at DESC",
                {"c": company_id},
            ),
            "postings": rows(
                connection,
                "SELECT * FROM job_posting WHERE company_id = :c ORDER BY closed_at NULLS FIRST, posted_at DESC NULLS LAST LIMIT 100",
                {"c": company_id},
            ),
            "signals": rows(
                connection,
                "SELECT * FROM signal WHERE company_id = :c ORDER BY observed_at DESC",
                {"c": company_id},
            ),
            "needs": rows(
                connection,
                "SELECT * FROM need WHERE company_id = :c ORDER BY detected_at DESC",
                {"c": company_id},
            ),
            "opportunities": rows(
                connection,
                "SELECT * FROM opportunity WHERE company_id = :c ORDER BY score DESC",
                {"c": company_id},
            ),
        }
    return templates.TemplateResponse(request, "company.html", context)
