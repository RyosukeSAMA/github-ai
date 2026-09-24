"""Cached check of the latest published Pantheon GitHub Release."""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any

import httpx

RELEASE_API = "https://api.github.com/repos/RyosukeSAMA/github-ai/releases/latest"
RELEASES_URL = "https://github.com/RyosukeSAMA/github-ai/releases"
CHECK_INTERVAL = 6 * 60 * 60


def version_tuple(value: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value.strip())
    return tuple(map(int, match.groups())) if match else None


class UpdateChecker:
    def __init__(self, current_version: str) -> None:
        self.current_version = current_version
        self._cache: dict[str, Any] | None = None
        self._checked = 0.0
        self._lock = asyncio.Lock()

    async def check(self, *, force: bool = False) -> dict[str, Any]:
        async with self._lock:
            if self._cache and not force and time.monotonic() - self._checked < CHECK_INTERVAL:
                return self._cache
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(RELEASE_API, headers={"Accept": "application/vnd.github+json", "User-Agent": "pantheon-update-check"})
                    response.raise_for_status()
                    release = response.json()
                tag = str(release.get("tag_name", ""))
                latest = version_tuple(tag)
                current = version_tuple(self.current_version)
                if latest is None or current is None:
                    raise ValueError("Unsupported release version")
                url = str(release.get("html_url", ""))
                if not url.startswith(RELEASES_URL + "/tag/"):
                    url = RELEASES_URL
                self._cache = {"current_version": self.current_version, "latest_version": tag,
                               "update_available": latest > current, "release_url": url,
                               "checked_at": int(time.time()), "error": None}
            except (httpx.HTTPError, ValueError, TypeError) as exc:
                if self._cache:
                    self._cache = {**self._cache, "error": str(exc)}
                else:
                    self._cache = {"current_version": self.current_version, "latest_version": None,
                                   "update_available": False, "release_url": RELEASES_URL,
                                   "checked_at": None, "error": str(exc)}
            self._checked = time.monotonic()
            return self._cache
