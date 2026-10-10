"""Daily reference rates into INR from Frankfurter (ECB data, no key). RBI's own feed has no API."""

from datetime import date
from decimal import Decimal

from loguru import logger

from opportunity_radar.db import execute_many, transaction
from opportunity_radar.sources.http import fetch

CURRENCIES = ("USD", "EUR", "GBP", "JPY", "AUD", "CAD", "SGD", "CHF")


def refresh(url: str) -> int:
    response = fetch("frankfurter", url, {"from": "INR", "to": ",".join(CURRENCIES)})
    body = response.json()
    as_of = date.fromisoformat(body["date"])
    # Frankfurter gives units of foreign currency per 1 INR; store INR per 1 unit.
    records = [
        {"c": currency, "d": as_of, "r": Decimal(1) / Decimal(str(value))}
        for currency, value in body["rates"].items()
    ]
    with transaction() as connection:
        execute_many(
            connection,
            "INSERT INTO fx_rate (currency, as_of, rate_inr) VALUES (:c, :d, :r) ON CONFLICT (currency, as_of) DO UPDATE SET rate_inr = EXCLUDED.rate_inr, fetched_at = now()",
            records,
        )
    logger.info(f"fx: {len(records)} rates as of {as_of}")
    return len(records)
