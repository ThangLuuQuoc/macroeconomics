"""`python -m macro.ingest`: chạy các connector, ghi chuỗi số liệu vào Postgres.

- Không có `--raw-dir`: mỗi connector tải bản gốc mới vào
  `data/raw/<connector>/<thời điểm>/` rồi đọc.
- Có `--raw-dir`: chỉ đọc bản gốc có sẵn trong `<raw-dir>/<connector>/` (không gọi mạng), dùng để
  kiểm thử và nạp lại.

Mỗi connector là một lần lấy (`fetch_runs`). Lỗi thì ghi lại và giữ nguyên số cũ (T-4).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import psycopg

from macro.config import load_settings
from macro.connectors import CONNECTORS, Connector
from macro.connectors.base import raise_if_failure_recorded
from macro.db import connect, init_schema
from macro.series import upsert_series


@dataclass(frozen=True)
class RunResult:
    connector: str
    status: str  # "ok" | "error" | "skipped"
    observations: int = 0
    error: str = ""


def ingest(
    conn: psycopg.Connection[dict],
    connectors: list[Connector],
    *,
    raw_root: Path,
    offline: bool,
) -> list[RunResult]:
    results = []
    for connector in connectors:
        source = raw_root / connector.name
        if not offline:
            source = source / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        elif not source.is_dir():
            results.append(RunResult(connector.name, "skipped"))
            continue
        with conn.transaction():
            for item in connector.series():
                upsert_series(conn, item)
            run_id = conn.execute(
                "INSERT INTO fetch_runs (connector, status, raw_path)"
                " VALUES (%s, 'running', %s) RETURNING id",
                (connector.name, str(source)),
            ).fetchone()["id"]  # type: ignore[index]
        try:
            if not offline:
                source.mkdir(parents=True, exist_ok=True)
                connector.fetch(source)
            raise_if_failure_recorded(source)
            observations = connector.parse(source)
        except Exception as exc:  # T-4: ghi lỗi, không đụng tới số đã có
            with conn.transaction():
                conn.execute(
                    "UPDATE fetch_runs SET status = 'error', error = %s, finished_at = now()"
                    " WHERE id = %s",
                    (str(exc)[:1000], run_id),
                )
            results.append(RunResult(connector.name, "error", error=str(exc)))
            continue
        with conn.transaction():
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO observations (series_id, period, value, fetch_run_id)"
                    " VALUES (%s, %s, %s, %s)",
                    [(o.series_id, o.period, o.value, run_id) for o in observations],
                )
            conn.execute(
                "UPDATE fetch_runs SET status = 'ok', finished_at = now() WHERE id = %s",
                (run_id,),
            )
        results.append(RunResult(connector.name, "ok", observations=len(observations)))
    return results


def main(argv: list[str] | None = None, connectors: list[Connector] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m macro.ingest")
    parser.add_argument("--raw-dir", type=Path, help="Chỉ đọc bản gốc có sẵn trong thư mục này")
    parser.add_argument("--database-url", help="Mặc định: $MACRO_DATABASE_URL")
    args = parser.parse_args(argv)
    settings = load_settings()
    connectors = CONNECTORS if connectors is None else connectors
    known = {c.name for c in connectors}
    if args.raw_dir is not None and args.raw_dir.is_dir():
        for folder in sorted(p for p in args.raw_dir.iterdir() if p.is_dir()):
            if folder.name not in known:
                print(f"Bỏ qua {folder.name}: chưa có connector", file=sys.stderr)
    with connect(args.database_url or settings.database_url) as conn:
        init_schema(conn)
        results = ingest(
            conn,
            connectors,
            raw_root=args.raw_dir or settings.raw_dir,
            offline=args.raw_dir is not None,
        )
    for r in results:
        detail = f"{r.observations} quan sát" if r.status == "ok" else r.error
        print(f"{r.connector}: {r.status} {detail}".rstrip())
    return 1 if any(r.status == "error" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
