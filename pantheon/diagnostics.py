"""Explicit, low-cost live diagnostics for configured model providers."""

from __future__ import annotations

import time
from typing import Any

from pantheon.core.pantheon import Pantheon
from pantheon.llm.openai_client import is_responses_api_model


class ProviderProbeError(RuntimeError):
    """Raised when a saved role cannot complete a provider probe."""


def _probe_kwargs(client: Any, model: str) -> dict[str, Any]:
    official_openai = callable(getattr(client, "_uses_official_openai_endpoint", None))
    if official_openai and client._uses_official_openai_endpoint() and is_responses_api_model(model):
        return {"max_output_tokens": 8, "timeout": 20.0}
    return {"max_tokens": 8, "timeout": 20.0}


def _safe_provider_error(error: Exception, api_key: str) -> str:
    message = str(error)
    if not api_key:
        return message
    masked = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 10 else "[redacted]"
    return message.replace(api_key, masked)


def _provider_name(client: Any) -> str:
    base_url = str(getattr(client, "base_url", "") or "").lower()
    if "deepseek" in base_url:
        return "deepseek"
    return str(getattr(client, "provider_name", "unknown"))


def probe_role_provider(
    role_name: str,
    *,
    config_path: str | None = None,
    pantheon: Pantheon | None = None,
) -> dict[str, Any]:
    """Make one minimal live request using a role's saved provider configuration."""
    runtime = pantheon or Pantheon(config_path=config_path)
    normalized_role = role_name.strip().lower()
    if normalized_role == "hermes":
        client = runtime.router.llm_client
        model = str(runtime.router.hermes_model or getattr(client, "default_model", ""))
    else:
        role = runtime.get_role(normalized_role)
        if role is None:
            raise ProviderProbeError(f"Unknown or disabled role: {normalized_role}")
        client = getattr(role, "llm", None)
        model = str(getattr(role, "model", "") or getattr(client, "default_model", ""))

    if client is None:
        raise ProviderProbeError(f"Role '{normalized_role}' has no usable provider client.")
    if not model or model == "none":
        raise ProviderProbeError(f"Role '{normalized_role}' has no model to test.")
    if getattr(client, "provider_name", "") != "ollama" and not getattr(client, "api_key", ""):
        raise ProviderProbeError(f"Role '{normalized_role}' has no configured API key.")

    started = time.monotonic()
    try:
        response = client.complete(
            [{"role": "user", "content": "Reply with exactly: ok"}],
            model=model,
            system="You are testing an API connection. Reply with exactly: ok",
            temperature=0,
            **_probe_kwargs(client, model),
        )
    except Exception as exc:
        raise ProviderProbeError(
            _safe_provider_error(exc, str(getattr(client, "api_key", "")))
        ) from exc

    return {
        "ok": True,
        "role": normalized_role,
        "provider": _provider_name(client),
        "model": model,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "response_preview": str(response)[:80],
    }
