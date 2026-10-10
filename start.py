#!/usr/bin/env python3
"""
Start Opportunity Radar locally.

    python start.py                # granian --reload on 5020 (127.0.0.1)
    python start.py --load-data    # create the schema and seed the profile + sources first
    python start.py --no-reload
    python start.py --stop

Port 5020 follows the workspace map (finance 5018, learn_mba 5016, oraceuticmd 5014, loylty_program 5012).
The pipeline is not started here; it is `python radar.py run`.
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
API_DIR = REPO_ROOT / "api"
VENV_PYTHON = API_DIR / ".venv" / "bin" / "python"
DEFAULT_PORT = 5020


def _python() -> str:
    if not VENV_PYTHON.is_file():
        raise SystemExit(f"No venv at {VENV_PYTHON}. Run: cd api && uv sync")
    return str(VENV_PYTHON)


def _environment(profile: str) -> dict[str, str]:
    environment = dict(os.environ)
    environment["OPPORTUNITY_RADAR_ENV"] = profile
    src = str(API_DIR / "src")
    existing = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = f"{src}:{existing}" if existing else src
    return environment


def _pids_on_port(port: int) -> list[int]:
    result = subprocess.run(["lsof", "-t", f"-i:{port}"], capture_output=True, text=True)
    return [int(line) for line in result.stdout.split() if line.strip().isdigit()]


def stop(port: int, wait_seconds: int = 15) -> None:
    for pid in _pids_on_port(port):
        print(f"  killing pid {pid} on port {port}")
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.time() + wait_seconds
    while time.time() < deadline and _pids_on_port(port):
        time.sleep(0.5)
    for pid in _pids_on_port(port):
        os.kill(pid, signal.SIGKILL)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--env", default="dev")
    parser.add_argument("--load-data", action="store_true")
    parser.add_argument("--no-reload", action="store_true")
    parser.add_argument("--stop", action="store_true")
    args = parser.parse_args()
    if args.stop:
        stop(args.port)
        return
    environment = _environment(args.env)
    (REPO_ROOT / "logs").mkdir(exist_ok=True)
    if args.load_data:
        subprocess.run(
            [_python(), str(REPO_ROOT / "load_data.py"), "--env", args.env],
            cwd=REPO_ROOT,
            env=environment,
            check=True,
        )
    if _pids_on_port(args.port):
        print(f"port {args.port} is busy; stopping the previous server")
        stop(args.port)
    command = [
        _python(),
        "-m",
        "granian",
        "--interface",
        "asgi",
        "opportunity_radar.main:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    if not args.no_reload:
        command += ["--reload", "--reload-paths", str(API_DIR / "src")]
    print(f"Opportunity Radar on http://{args.host}:{args.port}")
    try:
        subprocess.run(command, cwd=API_DIR, env=environment, check=False)
    except KeyboardInterrupt:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
