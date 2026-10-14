import json
from collections import Counter

from pantheon.core.base import Plan, PlanStep, Task, TaskResult
from pantheon.core.hermes import Hermes
from pantheon.core.router import Router
from pantheon.core.tasks import TaskStore
from tests.conftest import MockLLMClient


def test_recovery_retains_successes_and_unblocks_dependents(tmp_path):
    calls = Counter()
    class Agent:
        config = {}
        parallel_safe = True
        def __init__(self, name):
            self.name = name
        def run(self, task, context=None):
            calls[self.name] += 1
            success = self.name != 'b' or calls[self.name] > 1
            return TaskResult(self.name, 'done' if success else 'temporary failure', success=success)
    repairs = []
    class Planner:
        def revise_steps(self, task, plan, results, eligible):
            repairs.append(eligible)
            return [{'index': 1, 'task': 'retry the original build with a clearer instruction'}]
        def summarize(self, *args):
            return 'complete'
    hermes = Hermes({name: Agent(name) for name in ('a', 'b', 'c')}, Planner())
    hermes.replan_attempts = 1
    plan = Plan.multi([PlanStep('a', 'research'), PlanStep('b', 'build', depends_on=[1]), PlanStep('c', 'review', depends_on=[2])])
    result = hermes._run_multi(Task('Original scoped task'), plan)
    assert result['success']
    assert calls == {'a': 1, 'b': 2, 'c': 1}
    assert repairs == [[1]]
    assert len(result['recovery_attempts']) == 2  # Failed build and its previously blocked review.
    assert plan.steps[1].task == 'build'


def test_recovery_is_bounded_and_never_replays_external_actions(tmp_path):
    calls = []
    class Agent:
        parallel_safe = True
        config = {}
        def run(self, *args, **kwargs):
            calls.append('run')
            return TaskResult('a', 'failed', success=False, error='temporary failure')
    class Planner:
        def revise_steps(self, *args):
            return [{'index': 0, 'task': 'try within original scope'}]
        def summarize(self, *args):
            return 'done'
    hermes = Hermes({'a': Agent()}, Planner())
    hermes.replan_attempts = 2
    hermes._run_multi(Task('work'), Plan.multi([PlanStep('a', 'work')]))
    assert len(calls) == 3  # Original plus at most two recoveries.
    calls.clear()
    hermes.task_store = TaskStore(tmp_path / 'tasks.sqlite')
    task = Task('work')
    hermes.task_store.start(task.task_id, task.content, task.mode)
    hermes.active_task_id = task.task_id
    hermes.task_store.record_effect(task.task_id, 1, {'kind': 'mcp', 'tool': 'write'})
    result = hermes._run_multi(task, Plan.multi([PlanStep('a', 'work')]))
    assert len(calls) == 1
    assert not result['success']
    assert result['recovery_attempts'] == []


def test_router_repair_cannot_change_roles_or_completed_steps():
    client = MockLLMClient()
    client.add_response(json.dumps({'repairs': [
        {'step': 1, 'task': 'repeat completed step'}, {'step': 2, 'task': 'safe repair'},
        {'step': 2, 'task': 'duplicate repair'}, {'step': 2, 'task': 'new tool', 'role': 'chronos'},
        {'step': 99, 'task': 'expand plan'}]}))
    plan = Plan.multi([PlanStep('athena', 'research'), PlanStep('hephaestus', 'build', depends_on=[1])])
    repairs = Router(client).revise_steps('Original task', plan,
        [TaskResult('athena', 'done'), TaskResult('hephaestus', 'failed', success=False)], [1])
    assert repairs == [{'index': 1, 'task': 'safe repair', 'reason': ''}]
    assert 'Original task' in client.calls[0]['messages'][0]['content']
    assert 'Preserve the original objective' in client.calls[0]['system']
