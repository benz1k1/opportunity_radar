from typing import Any

import orjson
from fastapi import HTTPException
from fastapi.responses import Response

from opportunity_radar.db import row, scalar, transaction
from opportunity_radar.pages import queries


class ORJSONResponse(Response):
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return orjson.dumps(content, default=str)


def health():
    with transaction() as connection:
        return ORJSONResponse(
            {
                "success": True,
                "opportunities": scalar(connection, "SELECT count(*) FROM opportunity"),
                "last_run": row(connection, "SELECT ran_at FROM radar_run ORDER BY ran_at DESC LIMIT 1"),
            }
        )


def radar(bucket: str | None = None, mode: str | None = None):
    with transaction() as connection:
        return ORJSONResponse({"success": True, "items": queries.opportunities(connection, bucket, mode)})


def opportunity(opportunity_id: str):
    with transaction() as connection:
        item = queries.opportunity(connection, opportunity_id)
    if not item:
        raise HTTPException(404, "No such opportunity")
    return ORJSONResponse({"success": True, "item": item})


def region():
    with transaction() as connection:
        return ORJSONResponse({"success": True, "items": queries.region_gaps(connection)})
