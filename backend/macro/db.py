"""Kết nối Postgres và tạo schema."""

from __future__ import annotations

from importlib import resources

import psycopg
from psycopg.rows import dict_row


def connect(database_url: str) -> psycopg.Connection[dict]:
    return psycopg.connect(database_url, row_factory=dict_row)


def init_schema(conn: psycopg.Connection[dict]) -> None:
    sql = resources.files("macro").joinpath("schema.sql").read_text(encoding="utf-8")
    with conn.transaction():
        conn.execute(sql)
