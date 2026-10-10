"""One engine, one transaction helper, raw SQL. Rows come back as plain dicts."""

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Connection, create_engine, event, text
from sqlalchemy.engine import Engine

from opportunity_radar.config import (
    DATABASE_POOL_SIZE,
    DATABASE_SCHEMA,
    DATABASE_STATEMENT_TIMEOUT_MS,
    DATABASE_URL,
)


@event.listens_for(Engine, "connect")
def _disable_psycopg_auto_prepare(dbapi_connection: Any, connection_record: Any) -> None:
    # Pooled connections outlive psycopg's client-side prepared-statement names under prefork.
    if hasattr(dbapi_connection, "prepare_threshold"):
        dbapi_connection.prepare_threshold = None


engine = create_engine(
    DATABASE_URL,
    pool_size=DATABASE_POOL_SIZE,
    max_overflow=10,
    pool_recycle=1800,
    pool_pre_ping=True,
    pool_reset_on_return="rollback",
    connect_args={"options": f"-csearch_path={DATABASE_SCHEMA},public", "connect_timeout": 10},
)


@contextmanager
def transaction() -> Iterator[Connection]:
    """Commits on exit, rolls back on exception."""
    with engine.begin() as connection:
        connection.execute(text(f"SET LOCAL statement_timeout = {DATABASE_STATEMENT_TIMEOUT_MS}"))
        yield connection


def rows(connection: Connection, sql: str, params: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    return [dict(found) for found in connection.execute(text(sql), params or {}).mappings()]


def row(connection: Connection, sql: str, params: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    found = connection.execute(text(sql), params or {}).mappings().first()
    return dict(found) if found is not None else None


def scalar(connection: Connection, sql: str, params: Mapping[str, Any] | None = None) -> Any:
    return connection.execute(text(sql), params or {}).scalar()


def execute(connection: Connection, sql: str, params: Mapping[str, Any] | None = None) -> int:
    return connection.execute(text(sql), params or {}).rowcount


def execute_many(connection: Connection, sql: str, params: Sequence[Mapping[str, Any]]) -> None:
    if params:
        connection.execute(text(sql), list(params))
