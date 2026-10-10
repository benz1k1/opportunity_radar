"""The Jinja environment and the filters every template may use. Money shows ₹ first, original beside it."""

import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi.templating import Jinja2Templates

from opportunity_radar.pages.nav import nav_items
from opportunity_radar.service.money import indian_number, original, rupees

_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=_TEMPLATES_DIR)
templates.env.globals["nav_items"] = nav_items
templates.env.globals["BUCKET_CLASS"] = {
    "immediate": "badge-error",
    "consulting": "badge-primary",
    "emerging": "badge-info badge-outline",
    "dropped": "badge-ghost",
}
templates.env.globals["MODE_CLASS"] = {
    "client": "badge-primary",
    "contract": "badge-secondary",
    "career": "badge-accent",
}
templates.env.globals["CLASS_ICON"] = {
    "hiring": "mdi-account-multiple-plus",
    "trigger": "mdi-flash",
    "ai": "mdi-robot",
    "technology": "mdi-web",
    "direct": "mdi-message-text",
    "shortage": "mdi-earth",
}
templates.env.globals["DIMENSION_LABEL"] = {
    "shortage": "Shortage",
    "low_depth": "Low depth",
    "affordability": "Affordability",
    "offshore_open": "Offshore-open",
    "senior_demand": "Senior demand",
    "timezone": "Timezone",
}
_DASH = "—"


def fmt_date(value: Any) -> Any:
    if not value:
        return _DASH
    if isinstance(value, (date, datetime)):
        return value.strftime("%d-%b-%Y")
    return value


def fmt_dt(value: Any) -> Any:
    if not value:
        return _DASH
    if isinstance(value, datetime):
        return value.astimezone().strftime("%d-%b-%Y %H:%M")
    return value


def money(inr: Any, amount: Any = None, currency: str | None = None) -> str:
    """₹ first; the original figure beside it when it was not INR."""
    head = rupees(inr)
    if amount is not None and currency and currency != "INR":
        return f"{head} ({original(Decimal(str(amount)), currency)})"
    return head


def score_class(score: int) -> str:
    return "text-success" if score >= 80 else "text-warning" if score >= 60 else "text-base-content/60"


templates.env.filters["fmt_date"] = fmt_date
templates.env.filters["fmt_dt"] = fmt_dt
templates.env.filters["num"] = indian_number
templates.env.filters["rupees"] = rupees
templates.env.filters["money"] = money
templates.env.filters["score_class"] = score_class
