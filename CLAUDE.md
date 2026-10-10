# CLAUDE.md

Opportunity Radar — evidence-led opportunity discovery for one individual consultant (English only,
₹ as the display currency, draft in `opportunity-radar-product-draft.md`; read the section a change
touches, not the whole file). FastAPI + Jinja2 + htmx + Alpine + Tailwind/daisyUI (vendored, no
build step), Postgres, Granian. Same shape as `../finance` and `../oraceuticmd`.

## Commands

```bash
cd api && uv sync                      # venv at api/.venv; uv only
python start.py --load-data            # schema + seed (profile.yaml, source.csv), then the UI on 5020
python start.py --stop
python load_data.py [--drop|--seed-only]
python radar.py run                    # the whole pipeline; see `python radar.py -h` for the stages
python radar.py geo && python radar.py regions   # just the region-gap stages (location -> country, then the per-country score)
python radar.py status
cd api && uv run ruff check --fix . && uv run ruff format . && uv run mypy src/
```

The DB role and database were created by hand (`opportunity_radar_app` / `opportunity_radar_dev`);
the password is a Fernet token in `resources/env/dev/.env.yaml` (gitignored, `.example` is the template).

## Layout

```
api/src/opportunity_radar/
  config.py          _require() over the env YAML; LLM is optional (llm.enabled)
  db.py ids.py       raw SQL helpers, nanoid ids
  sources/           http.py (paced fetch + raw copy + fetch_log), ats.py (Greenhouse/Lever/Ashby public
                     boards), boards.py (Remotive, Arbeitnow), rss.py (funding headlines), fx.py
                     (Frankfurter -> INR), techstack.py (homepage fingerprint), postings.py (common shape + upsert)
  service/           classify.py (family/seniority/tech/remote/rate/English), geo.py (location text -> ISO countries,
                     keyword table, no geocoder), regions.py (region gaps: per-country shortage / low depth / affordability
                     / offshore-open / senior demand / timezone), signals.py (derived signals),
                     needs.py (rules, then Claude when enabled), scoring.py (dimensions + weights per mode),
                     opportunities.py (packet rows + buckets), pipeline.py (run order), money.py (₹)
  pages/             urls.py (route list), templating.py, nav.py, queries.py, controller/, templates/, static/
schema/schema.sql    whole schema; resources/seed/{profile.yaml,source.csv,watchlist.csv,country.csv}
```

## Rules

- **No signal, no need.** A need row must link to at least one signal (`need_signal`); the LLM pass
  must cite signal ids it was given or its output is discarded. Never invent a problem.
- **Non-English postings are stored flagged (`is_english = false`) and never scored.** English-deliverable
  is a hard filter, not a dimension.
- **Money is stored in its original currency** (`rate_*`, `value_*`) and converted to ₹ only for display
  via `fx_rate`. Never re-score on an FX move alone.
- Every fact and signal carries `source_key`, `source_url` and dates; signals expire, needs expire after
  them, opportunities drop when their posting closes or need expires (`drop_reason` says which).
- Sources are public JSON APIs and feeds only. No login, no real-name accounts, no scraping behind auth.
  Every fetch is paced per host, written under `raw/`, and logged in `fetch_log`.
- Routes are a list in `pages/urls.py`; REST paths are singular. Pages are cookie-less and bound to
  127.0.0.1 (single user, no auth).
- **Region gaps are computed, never curated.** `region_gap` is rebuilt every run from open English
  engineering postings and live signals; `country.csv` holds stable facts only (name, region, UTC offset,
  English as working language), never a hand-ranked list of "weak IT" countries. A country under
  `EVIDENCE_FLOOR` postings is shown as thin and capped. The shortage dimension needs days-open history,
  so it reads near zero until the radar has run for a few weeks. Parsed rates below ₹400/h are stray
  numbers, not prices, and are excluded from the country median.
- Loguru f-strings only; imports at module scope (the two `noqa: PLC0415` cases are the documented
  optional-dependency and load-order exceptions).
