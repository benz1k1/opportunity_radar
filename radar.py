#!/usr/bin/env python3
"""
Run the pipeline.

    python radar.py run                 # fx -> sources -> watchlist ATS boards -> geo -> tech stack -> signals -> needs -> regions -> score
    python radar.py fx
    python radar.py sources [--only remotive]
    python radar.py watchlist [--only stripe]
    python radar.py techstack [--limit 20]
    python radar.py signals
    python radar.py needs
    python radar.py geo                 # resolve posting locations to countries
    python radar.py regions             # score region gaps from the resolved postings
    python radar.py score
    python radar.py status
"""

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
VENV_PYTHON = REPO_ROOT / "api" / ".venv" / "bin" / "python"

if Path(sys.executable) != VENV_PYTHON:
    if not VENV_PYTHON.is_file():
        raise SystemExit(f"No venv at {VENV_PYTHON}. Run: cd api && uv sync")
    os.execv(VENV_PYTHON, [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path.insert(0, str(REPO_ROOT / "api" / "src"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "command",
        choices=["run", "fx", "sources", "watchlist", "geo", "techstack", "signals", "needs", "regions", "score", "status"],
    )
    parser.add_argument("--env", default=os.getenv("OPPORTUNITY_RADAR_ENV", "dev"))
    parser.add_argument("--only")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    os.environ["OPPORTUNITY_RADAR_ENV"] = args.env

    from opportunity_radar.db import rows, transaction
    from opportunity_radar.main import configure_logging
    from opportunity_radar.service import geo, needs, opportunities, pipeline, regions, signals
    from opportunity_radar.sources import techstack

    configure_logging()
    if args.command == "run":
        print(pipeline.run_all())
    elif args.command == "fx":
        pipeline.run_sources("frankfurter")
    elif args.command == "sources":
        pipeline.run_sources(args.only)
    elif args.command == "watchlist":
        pipeline.run_watchlist(args.only)
    elif args.command == "techstack":
        techstack.scan(args.limit)
    elif args.command == "signals":
        signals.derive()
    elif args.command == "geo":
        geo.resolve_all()
    elif args.command == "needs":
        needs.detect()
    elif args.command == "regions":
        regions.compute()
    elif args.command == "score":
        opportunities.score_all()
        print(opportunities.record_run())
    elif args.command == "status":
        with transaction() as connection:
            for table in (
                "company",
                "job_posting",
                "signal",
                "need",
                "opportunity",
                "feedback",
                "outcome",
                "fx_rate",
                "region_gap",
            ):
                print(f"  {table:12} {rows(connection, f'SELECT count(*) AS n FROM {table}')[0]['n']}")
            for source in rows(
                connection, "SELECT key, last_run_at, last_status, last_count FROM source ORDER BY key"
            ):
                print(
                    f"  {source['key']:28} {source['last_run_at'] or '-'!s:26} {source['last_status'] or '-'} ({source['last_count']})"
                )


if __name__ == "__main__":
    main()
