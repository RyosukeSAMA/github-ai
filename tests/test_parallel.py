import threading
from dataclasses import asdict

from pantheon.core.base import Plan, PlanStep, Task, TaskResult
from pantheon.core.budgets import TASK_ID
from pantheon.core.hermes import Hermes
from pantheon.core.tasks import TaskStore


def test_independent_steps_overlap_and_dependencies_wait(tmp_path):
    barrier = threading.Barrier(2)
    context_seen = []
    task_ids = []
    class Agent:
        parallel_safe = True
        config = {}
        def __init__(self, name):
            self.name = name
        def run(self, task, context=None):
            task_ids.append(TASK_ID.get())
            if self.name in {'a', 'b'}:
                barrier.wait(timeout=3)
                assert context == []
            else:
                context_seen.extend(context)
            return TaskResult(self.name, self.name + '-result')
    class Router:
        def summarize(self, task, context):
            return 'complete'
    roles = {name: Agent(name) for name in ('a', 'b', 'c')}
    hermes = Hermes(roles, Router())
    hermes.parallel_workers = 2
    hermes.task_store = TaskStore(tmp_path / 'tasks.sqlite')
    plan = Plan.multi([PlanStep('a', 'one'), PlanStep('b', 'two'), PlanStep('c', 'combine', depends_on=[1, 2])])
    task = Task('work', mode='multi')
    result = hermes.dispatch(task, resume_checkpoint={'plan': asdict(plan)})
    assert result['success']
    assert [step.role for step in result['steps']] == ['a', 'b', 'c']
    assert {item['result'] for item in context_seen} == {'a-result', 'b-result'}
    assert task_ids == [task.task_id] * 3
    assert len(hermes.task_store.get(task.task_id)['data']['checkpoint']['steps']) == 3


def test_unsafe_steps_are_exclusive_even_if_independent():
    lock = threading.Lock()
    active = 0
    maximum = 0
    first_entered = threading.Event()
    release = threading.Event()
    class Agent:
        config = {}
        parallel_safe = True
        def run(self, task, context=None):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            first_entered.set()
            assert release.wait(3)
            with lock:
                active -= 1
            return TaskResult('write', 'done')
    hermes = Hermes({'write': Agent()}, type('Router', (), {'summarize': lambda *args: 'done'})())
    hermes.parallel_workers = 3
    hermes.parallel_policy = lambda _: False
    result = []
    thread = threading.Thread(target=lambda: result.append(hermes._run_multi(Task('work'), Plan.multi([
        PlanStep('write', 'first'), PlanStep('write', 'second'), PlanStep('write', 'third')]))))
    thread.start()
    assert first_entered.wait(3)
    release.set()
    thread.join(3)
    assert not thread.is_alive()
    assert maximum == 1
    assert result[0]['success']
