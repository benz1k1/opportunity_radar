"""Page and /api routes, registered as a list. REST paths are singular."""

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI

from opportunity_radar.pages.controller import (
    api,
    companies,
    opportunities,
    profile,
    radar,
    regions,
    signals,
    sources,
)

ROUTES: list[tuple[str, Callable[..., Any], list[str]]] = [
    ("/", radar.radar_page, ["GET"]),
    ("/opportunity", opportunities.list_page, ["GET"]),
    ("/opportunity/{opportunity_id}", opportunities.packet_page, ["GET"]),
    ("/opportunity/{opportunity_id}/feedback", opportunities.feedback, ["POST"]),
    ("/opportunity/{opportunity_id}/outcome", opportunities.outcome, ["POST"]),
    ("/region", regions.list_page, ["GET"]),
    ("/region/{code}", regions.region_page, ["GET"]),
    ("/company", companies.list_page, ["GET"]),
    ("/company/{company_id}", companies.company_page, ["GET"]),
    ("/signal", signals.list_page, ["GET"]),
    ("/source", sources.list_page, ["GET"]),
    ("/profile", profile.profile_page, ["GET"]),
    ("/profile", profile.save_profile, ["POST"]),
    ("/profile/skill", profile.add_skill, ["POST"]),
    ("/profile/skill/{skill_id}/delete", profile.delete_skill, ["POST"]),
    ("/api/health", api.health, ["GET"]),
    ("/api/radar", api.radar, ["GET"]),
    ("/api/region", api.region, ["GET"]),
    ("/api/opportunity/{opportunity_id}", api.opportunity, ["GET"]),
]


def register_routes(app: FastAPI) -> None:
    for path, endpoint, methods in ROUTES:
        app.add_api_route(path, endpoint, methods=methods, include_in_schema=path.startswith("/api/"))
