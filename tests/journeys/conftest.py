"""Hạ tầng kịch bản người dùng: `macro_app(rounds)` dựng app thật trên database riêng.

Mỗi vòng trong `rounds` là một lần lấy dữ liệu (`{connector: bản ghi nguồn}`), nạp qua đúng đường
`python -m macro.ingest --raw-dir`; sau các vòng, app (API + bản build web) được khởi chạy và hàm
trả về URL trang chủ.
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest
import uvicorn

from macro import ingest
from macro.api import create_app
from macro.config import DEFAULT_WEB_DIR, Settings

from .support import write_round

MacroApp = Callable[..., str]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture
def macro_app(database_url: str, tmp_path: Path) -> Iterator[MacroApp]:
    if not (DEFAULT_WEB_DIR / "index.html").is_file():
        pytest.fail(f"Chưa có bản build web ở {DEFAULT_WEB_DIR}: chạy `pnpm --dir web build`.")
    servers: list[tuple[uvicorn.Server, threading.Thread]] = []

    def start(rounds: list[dict[str, object]]) -> str:
        for index, sources in enumerate(rounds):
            raw_dir = tmp_path / f"round-{index}"
            write_round(raw_dir, sources)
            ingest.main(["--raw-dir", str(raw_dir), "--database-url", database_url])
        settings = Settings(database_url=database_url, web_dir=DEFAULT_WEB_DIR)
        port = _free_port()
        server = uvicorn.Server(
            uvicorn.Config(create_app(settings), host="127.0.0.1", port=port, log_level="warning")
        )
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        servers.append((server, thread))
        url = f"http://127.0.0.1:{port}/"
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                if httpx.get(f"{url}api/health", timeout=2).status_code == 200:
                    return url
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        pytest.fail(f"App không khởi chạy được ở {url}")

    yield start
    for server, thread in servers:
        server.should_exit = True
        thread.join(timeout=10)
