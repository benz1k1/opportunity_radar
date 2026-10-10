from fastapi import Request

from opportunity_radar.db import rows, transaction
from opportunity_radar.pages.templating import templates


def list_page(request: Request, cls: str | None = None):
    with transaction() as connection:
        items = rows(
            connection,
            """SELECT s.*, c.name AS company_name FROM signal s JOIN company c ON c.id = s.company_id
               WHERE s.expires_at > now() AND (CAST(:cls AS text) IS NULL OR s.class = :cls) ORDER BY s.observed_at DESC LIMIT 300""",
            {"cls": cls},
        )
    return templates.TemplateResponse(request, "signal_list.html", {"items": items, "cls": cls})
