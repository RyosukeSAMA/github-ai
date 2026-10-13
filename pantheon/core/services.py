"""Workspace capabilities shared by CLI, Web and SDK."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pantheon.core.budgets import BudgetStore
from pantheon.core.credentials import CredentialStore
from pantheon.core.extensions import MCPError, MCPManager, PluginStore, SkillStore
from pantheon.core.memory import MemoryStore, detect_memory_candidate, normalize_memory_role
from pantheon.core.paths import DataPaths
from pantheon.core.readiness import ReadinessStore
from pantheon.core.scheduler import ChronosScheduler


class WorkspaceServices:
    def __init__(self, paths: DataPaths) -> None:
        self.paths = paths
        self.credentials = CredentialStore(paths.env)
        self.budget = BudgetStore(paths.state / 'budgets.sqlite')
        self.readiness = ReadinessStore(paths.state / 'readiness.sqlite')
        self.memory = MemoryStore(paths.state / 'memory.sqlite')
        self.skills = SkillStore(paths.state / 'skills', legacy_path=paths.state / 'skills.json')
        self.plugins = PluginStore(paths.state / 'plugins.json')
        self.mcp = MCPManager(paths.state / 'mcp_servers.json', env_lookup=self.env_value)
        self.scheduler = ChronosScheduler(paths.state / 'chronos_jobs.json')
        self.approval_handler: Callable[[dict[str, Any]], bool] | None = None

    def env_value(self, name: str) -> str:
        return self.credentials.get(name)

    def memory_context(self, content: str, role: str):
        return self.memory.context_block(content, role=role)

    def process_input(self, content: str) -> dict[str, list]:
        detected = detect_memory_candidate(content)
        if not detected:
            return {'saved': [], 'suggestions': []}
        values = {key: detected[key] for key in ('content', 'kind', 'source', 'role')}
        if detected['action'] == 'save':
            return {'saved': [self.memory.add(**values)], 'suggestions': []}
        suggestion = self.memory.suggest(**values, reason=detected['reason'])
        return {'saved': [], 'suggestions': [suggestion] if suggestion.get('status') == 'pending' else []}

    def capture_result(self, task: str, result: dict, mode: str) -> None:
        settings = self.memory.settings()
        content = str(result.get('content') or '').strip()
        if not settings['enabled'] or not settings['auto_capture'] or not content or mode == 'role:chronos':
            return
        summary = f"Task: {task.strip()[:500]}\nResult: {' '.join(content.split())[:1000]}"
        self.memory.add(summary, kind='task', source='auto', role=normalize_memory_role(mode))

    def execute_tool(self, call: dict[str, Any], *, role_name: str = '', on_event=None):
        server_id, tool_name = str(call.get('server_id') or ''), str(call.get('tool') or '')
        policy = self.mcp.agent_tool_policy(server_id, tool_name, role_name)
        if policy.get('approval') == 'ask':
            payload = {**call, 'role': role_name, 'risk': policy.get('tool', {}).get('risk', 'unknown'),
                       'server_name': policy.get('server_name') or server_id}
            if self.approval_handler is None:
                raise MCPError('This tool needs approval. Use the interactive CLI/Web or set a SDK approval handler.')
            if not self.approval_handler(payload):
                raise MCPError('MCP tool call was denied by the user')
        return self.mcp.call_tool(server_id, tool_name, call.get('arguments') or {})

    def attach(self, pantheon: Any) -> None:
        hermes = pantheon.hermes
        hermes.memory_context_provider = self.memory_context
        hermes.skill_context_provider = self.skills.context_block
        hermes.skill_catalog_provider = self.skills.catalog_for_roles
        hermes.skill_lookup_provider = self.skills.get
        hermes.plugin_context_provider = self.plugins.context_block
        hermes.mcp_context_provider = self.mcp.agent_context
        hermes.mcp_tool_executor = self.execute_tool
        chronos = pantheon.get_role('chronos')
        if chronos is not None:
            chronos.config['scheduler'] = self.scheduler
