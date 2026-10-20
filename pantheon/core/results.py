"""Consistent terminal outcomes at the CLI and HTTP boundaries.

SDK results retain their TaskResult objects; transport payloads use JSON objects.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def json_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return json_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def result_payload(result: dict) -> dict:
    """Add explicit terminal flags, without overriding evidence of failure."""
    payload = json_value(result)
    steps = payload.get('steps') or []
    failed = [step for step in steps if step.get('success') is False or step.get('error')]
    status = payload.get('status')
    if status not in {'failed', 'partial_failure', 'stopped', 'interrupted'}:
        if failed:
            status = 'partial_failure' if any(step.get('success', True) and not step.get('error') for step in steps) else 'failed'
        elif payload.get('success') is False or payload.get('error'):
            status = 'failed'
        else:
            status = 'completed'
    error = payload.get('error')
    if status != 'completed' and not error:
        error = next((step.get('error') for step in failed if step.get('error')), None)
        error = error or payload.get('content') or status.replace('_', ' ')
    return {**payload, 'task_id': payload.get('task_id'), 'status': status,
            'success': status == 'completed', 'error': error or None}


def result_exit_code(result: dict) -> int:
    status = result_payload(result)['status']
    return 0 if status == 'completed' else 130 if status in {'stopped', 'interrupted'} else 1
