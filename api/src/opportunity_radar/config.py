"""
Configuration. The env file is nested YAML, loaded once at import. Required keys go through
:func:`_require`, which raises when missing: no code default, nothing re-read from ``os.environ``.
Secrets (database password, LLM key) are Fernet tokens under ``fernet.key``.
"""

import os
from pathlib import Path
from typing import Any

from lr_lib.env_yaml import load_yaml_settings_file, nested_get
from lr_lib.fernet_str import try_fernet_decrypt_password
from lr_lib.sqlalchemy_url import url_with_decrypted_password

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve_env_file() -> Path:
    explicit = (os.getenv("OPPORTUNITY_RADAR_ENV_YAML") or "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise ValueError(f"OPPORTUNITY_RADAR_ENV_YAML file not found: {path}")
        return path
    profile = (os.getenv("OPPORTUNITY_RADAR_ENV") or "").strip()
    if not profile:
        raise ValueError(
            "Neither OPPORTUNITY_RADAR_ENV_YAML nor OPPORTUNITY_RADAR_ENV is set. "
            "Export OPPORTUNITY_RADAR_ENV=dev, or OPPORTUNITY_RADAR_ENV_YAML=/path/to/.env.yaml."
        )
    path = _REPO_ROOT / "resources" / "env" / profile / ".env.yaml"
    if not path.is_file():
        raise ValueError(f"OPPORTUNITY_RADAR_ENV={profile} resolves to {path}, which does not exist.")
    return path


ENV_FILE = _resolve_env_file()
SETTINGS: dict[str, Any] = load_yaml_settings_file(ENV_FILE)


def _scalar_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip()


def _require(*keys: str) -> str:
    value = _scalar_str(nested_get(SETTINGS, *keys))
    if not value:
        raise ValueError(f"Missing required config: {'.'.join(keys)}. Set it in {ENV_FILE}.")
    return value


def _opt_str(*keys: str, default: str) -> str:
    return _scalar_str(nested_get(SETTINGS, *keys, default=None)) or default


def _opt_float(*keys: str, default: float) -> float:
    value = _scalar_str(nested_get(SETTINGS, *keys, default=None))
    return float(value) if value else default


def _opt_int(*keys: str, default: int) -> int:
    value = _scalar_str(nested_get(SETTINGS, *keys, default=None))
    return int(value) if value else default


# ------------------------------------------------------------------ required
FERNET_KEY = _require("fernet", "key")
APP_HOST = _require("app", "host")
APP_PORT = int(_require("app", "port"))

DATABASE_URL = url_with_decrypted_password(_require("database", "url"), FERNET_KEY)
DATABASE_SCHEMA = _require("database", "schema")

RAW_DIR = Path(_require("paths", "raw_dir"))
LOG_DIR = Path(_require("paths", "log_dir"))

FETCH_USER_AGENT = _require("fetch", "user_agent")
# Base currency for every displayed amount. INR by decision (draft §1); other currencies convert to it.
BASE_CURRENCY = _require("currency", "base")

# ------------------------------------------------------------------ optional tuning
DATABASE_POOL_SIZE = max(2, _opt_int("database", "pool_size", default=5))
DATABASE_STATEMENT_TIMEOUT_MS = _opt_int("database", "statement_timeout_ms", default=60000)
FETCH_MIN_INTERVAL_SECONDS = _opt_float("fetch", "min_interval_seconds", default=1.0)
FETCH_TIMEOUT_SECONDS = _opt_float("fetch", "timeout_seconds", default=30.0)
LOG_LEVEL = _opt_str("logging", "level", default="INFO").upper()

# ------------------------------------------------------------------ optional feature: LLM need extraction
LLM_ENABLED = _opt_str("llm", "enabled", default="false").lower() == "true"
LLM_API_KEY = try_fernet_decrypt_password(_require("llm", "api_key"), FERNET_KEY) if LLM_ENABLED else ""
LLM_MODEL = _require("llm", "model") if LLM_ENABLED else ""
