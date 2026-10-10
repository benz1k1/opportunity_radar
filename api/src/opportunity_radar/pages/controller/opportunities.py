from fastapi import Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from opportunity_radar.db import execute, transaction
from opportunity_radar.ids import new_id
from opportunity_radar.pages import queries
from opportunity_radar.pages.templating import templates

STAGES = (
    "contacted",
    "replied",
    "call",
    "proposal",
    "won",
    "lost",
    "applied",
    "interview",
    "offer",
    "accepted",
    "rejected",
    "declined",
)


def list_page(request: Request, bucket: str | None = None, mode: str | None = None):
    with transaction() as connection:
        items = queries.opportunities(connection, bucket, mode, limit=200)
    return templates.TemplateResponse(
        request, "opportunity_list.html", {"items": items, "bucket": bucket, "mode": mode}
    )


def packet_page(request: Request, opportunity_id: str):
    with transaction() as connection:
        item = queries.opportunity(connection, opportunity_id)
    if not item:
        raise HTTPException(404, "No such opportunity")
    return templates.TemplateResponse(request, "packet.html", {"item": item, "stages": STAGES})


def feedback(request: Request, opportunity_id: str, verdict: str = Form(...), note: str = Form("")):
    if verdict not in ("relevant", "not_relevant"):
        raise HTTPException(422, "verdict must be relevant or not_relevant")
    with transaction() as connection:
        execute(
            connection,
            "INSERT INTO feedback (id, opportunity_id, verdict, note) VALUES (:id, :o, :v, :n)",
            {"id": new_id(), "o": opportunity_id, "v": verdict, "n": note},
        )
        item = queries.opportunity(connection, opportunity_id)
    return templates.TemplateResponse(request, "_packet_feedback.html", {"item": item})


def outcome(request: Request, opportunity_id: str, stage: str = Form(...), note: str = Form("")):
    if stage not in STAGES:
        raise HTTPException(422, f"stage must be one of {', '.join(STAGES)}")
    with transaction() as connection:
        execute(
            connection,
            "INSERT INTO outcome (id, opportunity_id, stage, note) VALUES (:id, :o, :s, :n)",
            {"id": new_id(), "o": opportunity_id, "s": stage, "n": note},
        )
    if request.headers.get("hx-request"):
        with transaction() as connection:
            item = queries.opportunity(connection, opportunity_id)
        return templates.TemplateResponse(request, "_packet_outcomes.html", {"item": item, "stages": STAGES})
    return RedirectResponse(f"/opportunity/{opportunity_id}", status_code=303)
