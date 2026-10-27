"""Cấu hình đọc từ biến môi trường."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = "postgresql://macro:macro@localhost:5544/macro"
DEFAULT_WEB_DIR = REPO_ROOT / "web" / "out"
DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw"


@dataclass(frozen=True)
class Settings:
    database_url: str = DEFAULT_DATABASE_URL
    web_dir: Path = DEFAULT_WEB_DIR
    raw_dir: Path = DEFAULT_RAW_DIR


def load_settings() -> Settings:
    return Settings(
        database_url=os.environ.get("MACRO_DATABASE_URL", DEFAULT_DATABASE_URL),
        web_dir=Path(os.environ.get("MACRO_WEB_DIR", DEFAULT_WEB_DIR)),
        raw_dir=Path(os.environ.get("MACRO_RAW_DIR", DEFAULT_RAW_DIR)),
    )
