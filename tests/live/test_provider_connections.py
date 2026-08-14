"""Opt-in live provider checks.

Run with PANTHEON_LIVE_TEST=1 and provider credentials in the environment.
These tests make real, low-output API requests and may incur a small charge.
"""

from __future__ import annotations

import os

import pytest

from pantheon.diagnostics import probe_role_provider

pytestmark = pytest.mark.live


def test_saved_role_provider_connection() -> None:
    if os.environ.get("PANTHEON_LIVE_TEST") != "1":
        pytest.skip("set PANTHEON_LIVE_TEST=1 to allow a real provider request")
    role = os.environ.get("PANTHEON_LIVE_ROLE", "hermes")
    result = probe_role_provider(role)
    assert result["ok"] is True
    assert result["response_preview"]
