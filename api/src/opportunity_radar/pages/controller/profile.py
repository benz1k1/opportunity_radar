from decimal import Decimal

from fastapi import Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from opportunity_radar.db import execute, row, rows, transaction
from opportunity_radar.ids import new_id
from opportunity_radar.pages.templating import templates


def _load(connection):
    profile = row(connection, "SELECT * FROM user_profile ORDER BY created_at LIMIT 1")
    if profile is None:
        raise HTTPException(500, "No user profile; run load_data.py")
    skills = rows(
        connection,
        "SELECT s.*, p.name AS parent_name FROM skill s LEFT JOIN skill p ON p.id = s.parent_id WHERE s.profile_id = :p ORDER BY coalesce(p.name, s.name), s.parent_id NULLS FIRST, s.name",
        {"p": profile["id"]},
    )
    return profile, skills


def profile_page(request: Request):
    with transaction() as connection:
        profile, skills = _load(connection)
    return templates.TemplateResponse(request, "profile.html", {"profile": profile, "skills": skills})


def save_profile(
    request: Request,
    rate_floor: Decimal = Form(...),
    rate_target: Decimal = Form(...),
    seniority: str = Form(...),
    remote_only: bool = Form(False),
    open_to_fulltime: bool = Form(False),
    domains: str = Form(""),
):
    with transaction() as connection:
        execute(
            connection,
            """UPDATE user_profile SET rate_floor_inr_hour = :f, rate_target_inr_hour = :t, seniority = :s, remote_only = :r, open_to_fulltime = :o,
               domains = :d, updated_at = now()""",
            {
                "f": rate_floor,
                "t": rate_target,
                "s": seniority,
                "r": remote_only,
                "o": open_to_fulltime,
                "d": [part.strip().lower() for part in domains.split(",") if part.strip()],
            },
        )
    return RedirectResponse("/profile", status_code=303)


def add_skill(
    request: Request,
    name: str = Form(...),
    confidence: Decimal = Form(...),
    years: Decimal = Form(0),
    parent: str = Form(""),
    aliases: str = Form(""),
):
    with transaction() as connection:
        profile = row(connection, "SELECT id FROM user_profile ORDER BY created_at LIMIT 1")
        if profile is None:
            raise HTTPException(500, "No user profile; run load_data.py")
        parent_row = (
            row(
                connection,
                "SELECT id FROM skill WHERE profile_id = :p AND lower(name) = lower(:n)",
                {"p": profile["id"], "n": parent},
            )
            if parent.strip()
            else None
        )
        parent_id = parent_row["id"] if parent_row else None
        execute(
            connection,
            """INSERT INTO skill (id, profile_id, name, parent_id, confidence, years, aliases) VALUES (:id, :p, :n, :parent, :c, :y, :a)
               ON CONFLICT (profile_id, name) DO UPDATE SET confidence = EXCLUDED.confidence, years = EXCLUDED.years, parent_id = EXCLUDED.parent_id, aliases = EXCLUDED.aliases""",
            {
                "id": new_id(),
                "p": profile["id"],
                "n": name.strip(),
                "parent": parent_id,
                "c": confidence,
                "y": years,
                "a": [part.strip().lower() for part in aliases.split(",") if part.strip()],
            },
        )
    return RedirectResponse("/profile", status_code=303)


def delete_skill(request: Request, skill_id: str):
    with transaction() as connection:
        execute(connection, "DELETE FROM skill WHERE id = :id", {"id": skill_id})
    return RedirectResponse("/profile", status_code=303)
