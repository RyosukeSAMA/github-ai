"""Runtime model discovery for supported Pantheon providers."""

from __future__ import annotations

import re
from typing import Any

import httpx

MODEL_DISCOVERY_TIMEOUT_SECONDS = 12.0


class ModelDiscoveryError(RuntimeError):
    """Raised when a provider model catalog cannot be fetched or parsed."""


def _models_url(provider: str, base_url: str) -> str:
    base = base_url.rstrip("/")
    if provider == "anthropic":
        return f"{base}/models" if base.endswith("/v1") else f"{base}/v1/models"
    if provider == "ollama":
        if base.endswith("/v1"):
            base = base[:-3].rstrip("/")
        return f"{base}/api/tags"
    return f"{base}/models"


def _is_chat_model(provider: str, model_id: str) -> bool:
    value = model_id.strip().lower()
    if not value:
        return False
    excluded = (
        "audio",
        "embedding",
        "image",
        "moderation",
        "realtime",
        "transcribe",
        "tts",
        "whisper",
    )
    if any(token in value for token in excluded):
        return False
    if provider == "openai":
        return (
            value.startswith("gpt-")
            or value.startswith("chatgpt-")
            or bool(re.match(r"^o\d", value))
        )
    if provider == "anthropic":
        return value.startswith("claude-")
    if provider == "deepseek":
        return value.startswith("deepseek-")
    if provider == "ollama":
        return "embed" not in value
    return False


def _model_items(provider: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    raw_items = payload.get("models", []) if provider == "ollama" else payload.get("data", [])
    if not isinstance(raw_items, list):
        raise ModelDiscoveryError("Provider returned an invalid model catalog.")

    models: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id") or item.get("model") or item.get("name") or "").strip()
        if not _is_chat_model(provider, model_id) or model_id in seen:
            continue
        display_name = str(item.get("display_name") or "").strip()
        models.append({"id": model_id, "label": display_name or model_id})
        seen.add(model_id)
    return models


async def discover_provider_models(
    provider: str,
    base_url: str,
    api_key: str = "",
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[dict[str, str]]:
    """Fetch text-capable model IDs available to the configured account."""
    headers: dict[str, str] = {"Accept": "application/json"}
    params: dict[str, Any] | None = None
    if provider == "anthropic":
        token = api_key[7:].strip() if api_key.lower().startswith("bearer ") else api_key
        if "api.kie.ai" in base_url.lower():
            headers["Authorization"] = f"Bearer {token}"
        else:
            headers["x-api-key"] = token
        headers["anthropic-version"] = "2023-06-01"
        params = {"limit": 100}
    elif api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(
            timeout=MODEL_DISCOVERY_TIMEOUT_SECONDS,
            follow_redirects=True,
            transport=transport,
        ) as client:
            response = await client.get(
                _models_url(provider, base_url),
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ModelDiscoveryError(str(exc)) from exc

    if not isinstance(payload, dict):
        raise ModelDiscoveryError("Provider returned an invalid model catalog.")
    models = _model_items(provider, payload)
    if not models:
        raise ModelDiscoveryError("Provider returned no compatible chat models.")
    return models
