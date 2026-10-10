"""Rupee conversion and formatting. Amounts are stored in their original currency; INR is display-only."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Connection

from opportunity_radar.db import rows

HOURS_PER_MONTH = Decimal(170)
HOURS_PER_YEAR = Decimal(2000)
_DASH = "—"


def latest_rates(connection: Connection) -> dict[str, Decimal]:
    found = rows(
        connection,
        "SELECT DISTINCT ON (currency) currency, rate_inr FROM fx_rate ORDER BY currency, as_of DESC",
    )
    rates = {record["currency"]: Decimal(record["rate_inr"]) for record in found}
    rates["INR"] = Decimal(1)
    return rates


def to_inr(amount: Decimal | None, currency: str | None, rates: dict[str, Decimal]) -> Decimal | None:
    if amount is None or not currency or currency not in rates:
        return None
    return Decimal(amount) * rates[currency]


def to_inr_per_hour(
    amount: Decimal | None, currency: str | None, period: str | None, rates: dict[str, Decimal]
) -> Decimal | None:
    inr = to_inr(amount, currency, rates)
    if inr is None:
        return None
    if period == "year":
        return inr / HOURS_PER_YEAR
    if period == "month":
        return inr / HOURS_PER_MONTH
    return inr


def indian_number(value: Decimal | float | int | None, decimals: int = 0) -> str:
    if value is None:
        return _DASH
    number = Decimal(str(value))
    whole, _, fraction = f"{abs(number):.{decimals}f}".partition(".")
    head, tail = whole[:-3], whole[-3:]
    groups: list[str] = []
    while head:
        groups.insert(0, head[-2:])
        head = head[:-2]
    grouped = ",".join([*groups, tail])
    sign = "-" if number < 0 else ""
    return f"{sign}{grouped}.{fraction}" if decimals else f"{sign}{grouped}"


def rupees(value: Decimal | float | int | None) -> str:
    """₹ with lakh/crore words above 1L, Indian grouping below."""
    if value is None:
        return _DASH
    number = Decimal(str(value))
    if abs(number) >= 10_000_000:
        return f"₹{number / 10_000_000:.2f}Cr"
    if abs(number) >= 100_000:
        return f"₹{number / 100_000:.1f}L"
    return f"₹{indian_number(number)}"


def original(amount: Decimal | None, currency: str | None) -> str:
    if amount is None or not currency:
        return ""
    symbol = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "INR": "₹"}.get(currency, f"{currency} ")
    return f"{symbol}{Decimal(amount):,.0f}"


def as_of(connection: Connection) -> date | None:
    found = rows(connection, "SELECT max(as_of) AS d FROM fx_rate")
    return found[0]["d"] if found else None
