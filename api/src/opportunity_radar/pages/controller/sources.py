from fastapi import Request

from opportunity_radar.db import rows, transaction
from opportunity_radar.pages.templating import templates


def list_page(request: Request):
    with transaction() as connection:
        items = rows(connection, "SELECT * FROM source ORDER BY enabled DESC, region, key")
        recent = rows(connection, "SELECT * FROM fetch_log ORDER BY fetched_at DESC LIMIT 50")
        runs = rows(connection, "SELECT * FROM radar_run ORDER BY ran_at DESC LIMIT 10")
    return templates.TemplateResponse(
        request, "source_list.html", {"items": items, "recent": recent, "runs": runs}
    )
