"""Nạp kịch bản vào database giả lập, không trộn với số thật (spec synthetic-data 2.3–2.4)."""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from macro.db import connect, init_schema
from macro.ingest import RunResult, ingest
from macro.synthetic.connector import NAME, SyntheticConnector
from macro.synthetic.model import Scenario, load_scenario

RAW_PATH_PREFIX = "synthetic:"
_loading = threading.Lock()  # một database giả lập: mỗi lúc chỉ nạp một kịch bản


class Refused(Exception):
    """Từ chối ghi vì sẽ trộn số giả lập với số thật."""


def _connectors(conn: psycopg.Connection[dict]) -> set[str]:
    rows = conn.execute("SELECT DISTINCT connector FROM fetch_runs").fetchall()
    return {r["connector"] for r in rows}


def refuse_if_synthetic(conn: psycopg.Connection[dict]) -> None:
    """Cho `ingest` thường: database đã có lần lấy giả lập thì không ghi số thật vào."""
    if NAME in _connectors(conn):
        raise Refused(
            "Từ chối: database này đang chứa dữ liệu giả lập; số liệu thật phải ở database riêng."
        )


def refuse_if_real(conn: psycopg.Connection[dict]) -> None:
    real = _connectors(conn) - {NAME}
    if real:
        raise Refused(
            "Từ chối: database này đã có số liệu thật"
            f" ({', '.join(sorted(real))}); dữ liệu giả lập phải ở database riêng"
            " (vd macro_synthetic)."
        )


def ensure_database(url: str) -> None:
    """Tạo database nếu chưa có (cần quyền CREATEDB trên máy chủ Postgres)."""
    name = conninfo_to_dict(url).get("dbname")
    if not name:
        raise ValueError("URL database giả lập thiếu tên database")
    admin_url = make_conninfo(url, dbname="postgres")
    with psycopg.connect(admin_url, autocommit=True) as admin:
        exists = admin.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
        if not exists:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(str(name))))


def load(url: str, scenario_name: str, seed: int | None = None) -> tuple[Scenario, int]:
    """Xoá dữ liệu giả cũ trong `url` rồi nạp kịch bản. Trả (kịch bản, seed đã dùng)."""
    scenario = load_scenario(scenario_name)
    seed = scenario.seed if seed is None else seed
    with _loading:
        ensure_database(url)
        with connect(url) as conn:
            init_schema(conn)
            refuse_if_real(conn)
            with conn.transaction():
                conn.execute("TRUNCATE observations, fetch_runs, series RESTART IDENTITY CASCADE")
            runs = [SyntheticConnector(scenario, seed)]
            if scenario.source_failure:
                runs.append(SyntheticConnector(scenario, seed, fail=True))
            results: list[RunResult] = []
            with tempfile.TemporaryDirectory() as raw:
                for connector in runs:
                    results += ingest(conn, [connector], raw_root=Path(raw), offline=False)
            with conn.transaction():
                conn.execute(
                    "UPDATE fetch_runs SET raw_path = %s WHERE connector = %s",
                    (f"{RAW_PATH_PREFIX}{scenario.name}:{seed}", NAME),
                )
    if results[0].status != "ok":
        raise RuntimeError(f"Không sinh được dữ liệu giả lập: {results[0].error}")
    return scenario, seed


def loaded(url: str) -> tuple[str, int] | None:
    """(kịch bản, seed) đang nạp trong `url`; None nếu database chưa có hoặc chưa nạp gì."""
    try:
        with connect(url) as conn:
            row = conn.execute(
                "SELECT raw_path FROM fetch_runs WHERE connector = %s ORDER BY id DESC LIMIT 1",
                (NAME,),
            ).fetchone()
    except psycopg.Error:
        return None
    if not row or not str(row["raw_path"]).startswith(RAW_PATH_PREFIX):
        return None
    name, _, seed = str(row["raw_path"]).removeprefix(RAW_PATH_PREFIX).rpartition(":")
    return name, int(seed)
