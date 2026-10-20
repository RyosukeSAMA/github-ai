"""Provider identities are independent of the protocol adapter used to call them."""
from __future__ import annotations

import copy

PROVIDERS = {
    'deepseek': {'adapter': 'openai', 'env_var': 'DEEPSEEK_API_KEY', 'base_url': 'https://api.deepseek.com'},
    'openai': {'adapter': 'openai', 'env_var': 'OPENAI_API_KEY', 'base_url': 'https://api.openai.com/v1'},
    'anthropic': {'adapter': 'anthropic', 'env_var': 'ANTHROPIC_API_KEY', 'base_url': 'https://api.anthropic.com'},
    'ollama': {'adapter': 'ollama', 'env_var': '', 'base_url': 'http://localhost:11434'},
}


def provider_identity(name: str, providers: dict) -> str:
    cfg = providers.get(name, {}) or {}
    if cfg.get('provider_id') in PROVIDERS:
        return cfg['provider_id']
    if name == 'openai' and ('deepseek' in str(cfg.get('base_url', '')).lower()
                             or 'DEEPSEEK_API_KEY' in str(cfg.get('api_key', ''))):
        return 'deepseek'
    return name


def connection_config(config: dict, provider: str) -> dict:
    """Explicit profiles take precedence; old YAML stays usable without rewriting it."""
    profiles = config.get('provider_connections', {}) or {}
    if isinstance(profiles.get(provider), dict):
        return profiles[provider]
    providers = config.get('llm_providers', {}) or {}
    for name, cfg in providers.items():
        if isinstance(cfg, dict) and provider_identity(name, providers) == provider:
            return cfg
    return {}


def resolve_connection(config: dict, provider: str, env_lookup, *, require_enabled=False) -> tuple[str, str]:
    preset = PROVIDERS[provider]
    cfg = connection_config(config, provider)
    if require_enabled and (not cfg.get('enabled', True) or cfg.get('deleted')):
        raise ValueError(f'{provider} connection is disabled or removed. Enable or save it in Connections first.')
    raw = str(cfg.get('api_key') or '')
    if raw.startswith('${') and raw.endswith('}'):
        key = env_lookup(raw[2:-1])
    elif raw:
        key = raw
    else:
        key = env_lookup(preset['env_var']) if preset['env_var'] else ''
    if provider == 'anthropic' and key.lower().startswith('bearer '):
        key = key[7:].strip()
    return str(cfg.get('base_url') or preset['base_url']).strip(), key


def normalized_config(config: dict) -> dict:
    """Resolve legacy adapter references before adding independent provider profiles."""
    result = copy.deepcopy(config)
    old = config.get('llm_providers', {}) or {}
    pantheon = result.get('pantheon', {}) or {}
    roles = [pantheon.get('hermes', {})] + list((pantheon.get('roles', {}) or {}).values())
    for role in roles:
        if role.get('provider'):
            role['provider'] = role.get('provider_id') or provider_identity(role['provider'], old)
    legacy_default = provider_identity('openai', old)
    if legacy_default != 'openai':
        for name in ('hephaestus', 'athena', 'apollo'):
            result.setdefault('pantheon', {}).setdefault('roles', {}).setdefault(name, {}).setdefault('provider', legacy_default)
    providers = {}
    for name, cfg in old.items():
        if not isinstance(cfg, dict):
            continue
        identity = provider_identity(name, old)
        providers[identity] = {**cfg, 'adapter': cfg.get('adapter') or PROVIDERS.get(identity, {}).get('adapter', name),
                               'provider_id': identity}
    for name, cfg in (config.get('provider_connections', {}) or {}).items():
        if name in PROVIDERS and isinstance(cfg, dict):
            providers[name] = {**cfg, 'adapter': PROVIDERS[name]['adapter'], 'provider_id': name, 'enabled': cfg.get('enabled', True) and not cfg.get('deleted', False)}
    result['llm_providers'] = providers
    return result
