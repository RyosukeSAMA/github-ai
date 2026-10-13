"""Atomic request budgets and explicitly labelled local cost estimates."""
from __future__ import annotations

import json
import math
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from pantheon.core.usage import usage_from_response

TASK_ID: ContextVar[str] = ContextVar('pantheon_budget_task', default='')
RESERVATION: ContextVar[tuple | None] = ContextVar('pantheon_budget_reservation', default=None)
DEFAULT_POLICY = {'task_requests': 0, 'daily_requests': 0, 'output_tokens': 0,
                  'task_usd': 0.0, 'daily_usd': 0.0, 'prices': {}, 'operation_prices': {}}


class BudgetExceededError(RuntimeError):
    pass


class BudgetStore:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        os.chmod(self.path, 0o600)
        db.row_factory = sqlite3.Row
        try:
            db.execute('CREATE TABLE IF NOT EXISTS policy (id INTEGER PRIMARY KEY, data TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS reservations (id TEXT PRIMARY KEY, created REAL, task TEXT, provider TEXT, model TEXT, estimate REAL, state TEXT, rates TEXT)')
            db.execute('CREATE INDEX IF NOT EXISTS reservation_task ON reservations(task)')
            db.execute('CREATE INDEX IF NOT EXISTS reservation_created ON reservations(created)')
            if 'rates' not in {row[1] for row in db.execute('PRAGMA table_info(reservations)')}:
                db.execute('ALTER TABLE reservations ADD COLUMN rates TEXT')
            db.commit()
            with db:
                yield db
        finally:
            db.close()

    def _policy(self, db):
        row = db.execute('SELECT data FROM policy WHERE id=1').fetchone()
        return {**DEFAULT_POLICY, **json.loads(row['data'])} if row else dict(DEFAULT_POLICY)

    def policy(self):
        with self.connect() as db:
            return self._policy(db)

    def save_policy(self, value: dict):
        policy = {**DEFAULT_POLICY, **value}
        if set(policy) != set(DEFAULT_POLICY):
            raise ValueError('Unknown budget setting')
        for name in ('task_requests', 'daily_requests', 'output_tokens'):
            if type(policy[name]) is not int or not 0 <= policy[name] <= 1000000:
                raise ValueError(f'{name} must be a non-negative integer')
        for name in ('task_usd', 'daily_usd'):
            if type(policy[name]) not in (int, float) or not math.isfinite(policy[name]) or policy[name] < 0:
                raise ValueError(f'{name} must be non-negative and finite')
        if not isinstance(policy['prices'], dict):
            raise ValueError('prices must map provider/model to input and output USD per million tokens')
        for key, rates in policy['prices'].items():
            if not isinstance(key, str) or not isinstance(rates, dict) or set(rates) != {'input', 'output'}:
                raise ValueError('Each price needs input and output rates')
            if any(type(rate) not in (float, int) or not math.isfinite(rate) or rate < 0 for rate in rates.values()):
                raise ValueError('Token prices must be non-negative and finite')
        if not isinstance(policy['operation_prices'], dict) or any(
            not isinstance(key, str) or type(rate) not in (float, int) or not math.isfinite(rate) or rate < 0
            for key, rate in policy['operation_prices'].items()
        ):
            raise ValueError('operation_prices must map provider/model to a non-negative USD estimate per media request')
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO policy VALUES (1, ?)', (json.dumps(policy),))
        return policy

    def reserve(self, provider: str, model: str, messages, system: str, max_output: int, *, media=False) -> tuple[str, int]:
        task = TASK_ID.get() or 'request:' + uuid.uuid4().hex
        now = time.time()
        # A rolling 24-hour window also remains predictable across local timezone changes.
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            policy = self._policy(db)
            if policy['output_tokens']:
                max_output = min(max_output, policy['output_tokens'])
            flat = policy['operation_prices'].get(f'{provider}/{model}') if media else None
            price = {'flat': flat} if flat is not None else (None if media else policy['prices'].get(f'{provider}/{model}'))
            if price is None and (policy['daily_usd'] or policy['task_usd']):
                raise BudgetExceededError(f'No price configured for {provider}/{model}. Set a price estimate or use request limits.')
            # UTF-8 bytes are a conservative text-token bound, including serialized message overhead.
            input_bound = len((system + json.dumps(messages, ensure_ascii=False)).encode()) + 128 if not media else 0
            estimate = flat if media else ((input_bound * price['input'] + max_output * price['output']) / 1000000 if price else None)
            for field, clause, parameter in [('daily', 'created > ?', now - 86400), ('task', 'task = ?', task)]:
                row = db.execute(f'SELECT COUNT(*) AS calls, COALESCE(SUM(estimate), 0) AS cost FROM reservations WHERE {clause}', (parameter,)).fetchone()
                if policy[f'{field}_requests'] and row['calls'] >= policy[f'{field}_requests']:
                    raise BudgetExceededError(f'{field.capitalize()} request limit reached. Review Settings → Info → Budgets.')
                if policy[f'{field}_usd'] and row['cost'] + (estimate or 0) > policy[f'{field}_usd']:
                    raise BudgetExceededError(f'{field.capitalize()} estimated cost limit reached. No new model request was sent.')
            identity = uuid.uuid4().hex
            db.execute('INSERT INTO reservations VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                       (identity, now, task, provider, model, estimate, 'reserved', json.dumps(price) if price else None))
        return identity, max_output

    def settle(self, identity: str, response, *, responses_api=False):
        counts = usage_from_response(response, responses_api=responses_api)
        with self.connect() as db:
            row = db.execute('SELECT rates FROM reservations WHERE id=?', (identity,)).fetchone()
            if not row:
                return
            price = json.loads(row['rates']) if row['rates'] else None
            if price and 'flat' in price:
                db.execute('UPDATE reservations SET state=? WHERE id=?', ('estimated', identity))
            elif price and counts['input_tokens'] is not None and counts['output_tokens'] is not None:
                estimate = (counts['input_tokens'] * price['input'] + counts['output_tokens'] * price['output']) / 1000000
                db.execute('UPDATE reservations SET estimate=?, state=? WHERE id=?', (estimate, 'reported', identity))
            else:
                db.execute('UPDATE reservations SET state=? WHERE id=?', ('unmetered', identity))

    def summary(self):
        with self.connect() as db:
            row = db.execute('SELECT COUNT(*) AS requests, COALESCE(SUM(estimate), 0) AS estimated_usd, SUM(estimate IS NULL) AS unpriced, SUM(state="reserved") AS uncertain FROM reservations WHERE created > ?', (time.time() - 86400,)).fetchone()
            policy = self._policy(db)
        warnings = []
        if row['unpriced']:
            warnings.append('Some recent requests have no configured price; their cost is unknown and excluded from the estimate.')
        if policy['daily_requests'] and row['requests'] >= policy['daily_requests'] * .8:
            warnings.append('At least 80% of the daily request limit has been used.')
        if policy['daily_usd'] and row['estimated_usd'] >= policy['daily_usd'] * .8:
            warnings.append('At least 80% of the daily cost estimate limit has been used.')
        return {'policy': policy, 'last_24_hours': dict(row), 'warnings': warnings,
                'note': 'Workspace limits count request attempts, including failures. Costs use your rates and are estimates, not provider invoices. Unpriced calls have unknown cost; unmetered or failed calls retain their reservation. SDK internal retries are disabled.'}
