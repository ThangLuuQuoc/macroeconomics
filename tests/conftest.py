"""Fixture dùng chung: mỗi test một database Postgres riêng, xoá sau khi xong."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

ADMIN_URL = os.environ.get(
    "MACRO_TEST_DATABASE_URL", "postgresql://macro:macro@localhost:5544/postgres"
)


@pytest.fixture
def database_url() -> Iterator[str]:
    name = f"macro_test_{uuid.uuid4().hex[:12]}"
    try:
        admin = psycopg.connect(ADMIN_URL, autocommit=True)
    except psycopg.OperationalError as exc:
        pytest.fail(
            f"Không kết nối được Postgres cho test ({ADMIN_URL}). "
            f"Chạy `docker compose up -d db` (hoặc đặt MACRO_TEST_DATABASE_URL). Lỗi: {exc}"
        )
    with admin:
        admin.execute(f'CREATE DATABASE "{name}"')
        try:
            yield make_conninfo(ADMIN_URL, dbname=name)
        finally:
            admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
