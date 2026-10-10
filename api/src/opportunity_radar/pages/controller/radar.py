from fastapi import Request

from opportunity_radar.db import row, rows, transaction
from opportunity_radar.pages import queries
from opportunity_radar.pages.templating import templates
from opportunity_radar.service.money import as_of


def radar_page(request: Request):
    with transaction() as connection:
        context = {
            "immediate": queries.opportunities(connection, "immediate", limit=15),
            "consulting": queries.opportunities(connection, "consulting", limit=15),
            "emerging": queries.opportunities(connection, "emerging", limit=10),
            "dropped": queries.dropped_recent(connection),
            "last_run": row(connection, "SELECT * FROM radar_run ORDER BY ran_at DESC LIMIT 1"),
            "fx_as_of": as_of(connection),
            "counts": {
                r["bucket"]: r["n"]
                for r in rows(connection, "SELECT bucket, count(*) AS n FROM opportunity GROUP BY bucket")
            },
        }
    return templates.TemplateResponse(request, "radar.html", context)
