#!/usr/bin/env python3
"""
Create the schema and seed the profile and sources.

    python load_data.py              # create what is missing, seed profile.yaml + source.csv (upsert)
    python load_data.py --drop       # DROP the schema first (loses signals, feedback, outcomes — asks)
    python load_data.py --seed-only

Imports of the application package are inside the functions on purpose: OPPORTUNITY_RADAR_ENV has to be
set from --env before config is imported, because config reads its YAML at import and fails fast.
"""

import argparse
import csv
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
VENV_PYTHON = REPO_ROOT / "api" / ".venv" / "bin" / "python"
SCHEMA_FILE = REPO_ROOT / "schema" / "schema.sql"
SEED_DIR = REPO_ROOT / "resources" / "seed"

if Path(sys.executable) != VENV_PYTHON:
    if not VENV_PYTHON.is_file():
        raise SystemExit(f"No venv at {VENV_PYTHON}. Run: cd api && uv sync")
    os.execv(VENV_PYTHON, [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path.insert(0, str(REPO_ROOT / "api" / "src"))


def create_schema(drop: bool) -> None:
    from sqlalchemy import text

    from opportunity_radar.config import DATABASE_SCHEMA
    from opportunity_radar.db import engine

    with engine.begin() as connection:
        if drop:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{DATABASE_SCHEMA}" CASCADE'))
            print(f"  dropped schema {DATABASE_SCHEMA}")
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{DATABASE_SCHEMA}"'))
        connection.execute(text(f'SET search_path TO "{DATABASE_SCHEMA}", public'))
        connection.exec_driver_sql(SCHEMA_FILE.read_text())
    print(f"  schema {DATABASE_SCHEMA} ready")


def seed() -> None:
    import yaml

    from opportunity_radar.db import execute, row, transaction
    from opportunity_radar.ids import new_id

    profile = yaml.safe_load((SEED_DIR / "profile.yaml").read_text())
    with transaction() as connection:
        existing = row(connection, "SELECT id FROM user_profile ORDER BY created_at LIMIT 1")
        profile_id = existing["id"] if existing else new_id()
        fields = {
            k: profile[k]
            for k in (
                "name",
                "headline",
                "summary",
                "seniority",
                "years_experience",
                "country",
                "timezone",
                "rate_floor_inr_hour",
                "rate_target_inr_hour",
                "remote_only",
                "open_to_fulltime",
                "domains",
            )
        }
        if existing:
            # Rates and preferences edited in the UI win over the seed; identity fields refresh.
            execute(
                connection,
                "UPDATE user_profile SET name = :name, headline = :headline, summary = :summary, updated_at = now() WHERE id = :id",
                {"id": profile_id, **fields},
            )
        else:
            execute(
                connection,
                """INSERT INTO user_profile (id, name, headline, summary, seniority, years_experience, country, timezone,
                                   rate_floor_inr_hour, rate_target_inr_hour, remote_only, open_to_fulltime, domains)
                                   VALUES (:id, :name, :headline, :summary, :seniority, :years_experience, :country, :timezone,
                                   :rate_floor_inr_hour, :rate_target_inr_hour, :remote_only, :open_to_fulltime, :domains)""",
                {"id": profile_id, **fields},
            )
        ids: dict[str, str] = {}
        for skill in profile["skills"]:  # parents are listed before children in the seed
            found = row(
                connection,
                "SELECT id FROM skill WHERE profile_id = :p AND name = :n",
                {"p": profile_id, "n": skill["name"]},
            )
            skill_id = found["id"] if found else new_id()
            execute(
                connection,
                """INSERT INTO skill (id, profile_id, name, parent_id, confidence, years, aliases) VALUES (:id, :p, :n, :parent, :c, :y, :a)
                                   ON CONFLICT (profile_id, name) DO UPDATE SET parent_id = EXCLUDED.parent_id, confidence = EXCLUDED.confidence, years = EXCLUDED.years, aliases = EXCLUDED.aliases""",
                {
                    "id": skill_id,
                    "p": profile_id,
                    "n": skill["name"],
                    "parent": ids.get(skill.get("parent", "")),
                    "c": skill["confidence"],
                    "y": skill.get("years", 0),
                    "a": [alias.lower() for alias in skill.get("aliases", [])],
                },
            )
            ids[skill["name"]] = skill_id
        print(f"  profile {profile['name']}: {len(profile['skills'])} skills")
        with (SEED_DIR / "source.csv").open() as handle:
            sources = list(csv.DictReader(handle))
        for source in sources:
            execute(
                connection,
                """INSERT INTO source (key, kind, region, label, config) VALUES (:key, :kind, :region, :label, CAST(:config AS jsonb))
                                   ON CONFLICT (key) DO UPDATE SET kind = EXCLUDED.kind, region = EXCLUDED.region, label = EXCLUDED.label, config = EXCLUDED.config""",
                source,
            )
        print(f"  {len(sources)} sources")
        with (SEED_DIR / "country.csv").open() as handle:
            countries = list(csv.DictReader(handle))
        for country in countries:
            execute(
                connection,
                """INSERT INTO country (code, name, region, utc_offset, english_ok) VALUES (:code, :name, :region, :utc_offset, CAST(:english_ok AS boolean))
                                   ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, region = EXCLUDED.region, utc_offset = EXCLUDED.utc_offset, english_ok = EXCLUDED.english_ok""",
                country,
            )
        print(f"  {len(countries)} countries")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--env", default=os.getenv("OPPORTUNITY_RADAR_ENV", "dev"))
    parser.add_argument("--drop", action="store_true")
    parser.add_argument("--seed-only", action="store_true")
    args = parser.parse_args()
    os.environ["OPPORTUNITY_RADAR_ENV"] = args.env
    if (
        args.drop
        and input("DROP the schema and every signal, feedback and outcome? [y/N] ").strip().lower() != "y"
    ):
        raise SystemExit("aborted")
    if not args.seed_only:
        create_schema(args.drop)
    seed()
    print("done")


if __name__ == "__main__":
    main()
