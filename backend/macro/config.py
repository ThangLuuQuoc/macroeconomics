"""Cấu hình đọc từ biến môi trường (và `.env` ở gốc repo, nếu có; biến môi trường thật thắng)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from psycopg.conninfo import make_conninfo

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = "postgresql://macro:macro@localhost:5544/macro"
DEFAULT_WEB_DIR = REPO_ROOT / "web" / "out"
DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw"
ENV_FILE = REPO_ROOT / ".env"
SYNTHETIC_DATABASE = "macro_synthetic"


@dataclass(frozen=True)
class Settings:
    database_url: str = DEFAULT_DATABASE_URL
    web_dir: Path = DEFAULT_WEB_DIR
    raw_dir: Path = DEFAULT_RAW_DIR
    openstock_url: str | None = None  # Tài khoản chỉ đọc vào stock_db của openstock
    # Database riêng cho dữ liệu giả lập (spec synthetic-data); để trống thì là database
    # `macro_synthetic` trên cùng máy chủ với `database_url`.
    synthetic_database_url: str = ""

    def __post_init__(self) -> None:
        if not self.synthetic_database_url:
            derived = make_conninfo(self.database_url, dbname=SYNTHETIC_DATABASE)
            object.__setattr__(self, "synthetic_database_url", derived)


def read_env_file(path: Path) -> dict[str, str]:
    """`KEY=VALUE` mỗi dòng; bỏ dòng trống và dòng bắt đầu bằng `#`."""
    if not path.is_file():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_settings() -> Settings:
    env = {**read_env_file(ENV_FILE), **os.environ}
    return Settings(
        database_url=env.get("MACRO_DATABASE_URL", DEFAULT_DATABASE_URL),
        web_dir=Path(env.get("MACRO_WEB_DIR", DEFAULT_WEB_DIR)),
        raw_dir=Path(env.get("MACRO_RAW_DIR", DEFAULT_RAW_DIR)),
        openstock_url=env.get("MACRO_OPENSTOCK_URL") or None,
        synthetic_database_url=env.get("MACRO_SYNTHETIC_DATABASE_URL", ""),
    )
