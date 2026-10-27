"""Tải file từ nguồn: một chỗ cho timeout, User-Agent và lỗi HTTP."""

from __future__ import annotations

from pathlib import Path

import httpx

from macro.connectors.base import SourceError

USER_AGENT = "macroeconomics/0.1 (personal research tool)"
TIMEOUT = httpx.Timeout(60.0)


def get(url: str) -> httpx.Response:
    try:
        response = httpx.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT, follow_redirects=True
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise SourceError(f"{url}: {exc}") from exc
    return response


def download(url: str, target: Path) -> None:
    target.write_bytes(get(url).content)
