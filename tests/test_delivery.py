import json

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from pantheon.cli import app as cli
from pantheon.core.delivery import DeliveryStore
from pantheon.core.paths import DataPaths
from pantheon.core.project import ProjectConflictError
from pantheon.core.services import WorkspaceServices
from pantheon.web.app import create_app


@pytest.fixture
def delivery(tmp_path, monkeypatch):
    monkeypatch.setenv('PANTHEON_WORKSPACE', str(tmp_path))
    monkeypatch.setenv('PANTHEON_STATE_MODE', 'workspace')
    (tmp_path/'index.html').write_text('<button id="add">Add</button><p id="total">0</p>')
    services = WorkspaceServices(DataPaths.for_workspace(tmp_path))
    store = services.delivery
    contract = store.save_contract({'context':'site','title':'Product site','goal':'Show the product',
        'files':['index.html'],'entrypoint':'index.html','requirements':['Brand is appropriate'],
        'interactions':[{'label':'Add works','click':'#add','expect':'#total','text':'1'}]}, 0)
    return store, contract, tmp_path


def reference(contract):
    return {'id':contract['id'],'version':contract['version']}


def observed(status):
    return {'checks':[{'label':'Actual fixture check','status':status,'detail':'Observed fixture'}], 'screenshots':[]}


def test_criteria_conflicts_paths_and_stale_send_are_rejected(delivery):
    store, contract, _ = delivery
    assert 'Show the product' in store.acceptance_context(reference(contract))
    updated = store.save_contract({**contract['data'],'goal':'New goal'}, 1)
    with pytest.raises(ProjectConflictError):
        store.save_contract(contract['data'], 1)
    with pytest.raises(ProjectConflictError):
        store.acceptance_context(reference(contract))
    for name in ['.env','../index.html','config/pantheon.yaml','x.sqlite','/index.html']:
        with pytest.raises(ValueError):
            store.save_contract({**updated['data'],'files':[name],'entrypoint':name}, 2)


def test_repair_stays_candidate_until_review_and_acceptance_is_versioned(delivery, monkeypatch):
    store, contract, root = delivery
    monkeypatch.setattr(store, '_browser', lambda identity, round_number, files, spec: observed('failed' if round_number==0 else 'passed'))
    requested=[]
    def repair(*args):
        requested.append(args)
        return json.dumps({'files':{'index.html':'<p>Fixed site</p>'},'handoff':{'decisions':['Keep the offer clear']}})
    report=store.execute(store.prepare(reference(contract), repair=True), repair)
    assert len(requested)==1 and report['verification']=='candidate_passed'
    assert 'Fixed site' not in (root/'index.html').read_text()
    assert 'Fixed site' in store.diffs(report['id'])[0]['diff']
    with pytest.raises(ValueError):
        store.accept(report['id'], report['proof'], acknowledge_requirements=True)
    applied=store.apply(report['id'],report['proof'])
    assert applied['verification']=='passed' and (root/'index.html').read_text()=='<p>Fixed site</p>'
    with pytest.raises(ValueError):
        store.accept(report['id'], applied['proof'])
    accepted=store.accept(report['id'],applied['proof'],acknowledge_requirements=True)
    assert accepted['accepted']
    (root/'index.html').write_text('External change')
    stale=store.report(report['id'])
    assert stale['verification']=='stale' and not stale['accepted']
    with pytest.raises(ProjectConflictError):
        store.accept(report['id'], accepted['proof'], acknowledge_requirements=True)


def test_exact_two_round_limit_and_unverified_never_means_passed(delivery, monkeypatch):
    store, contract, root = delivery
    monkeypatch.setattr(store, '_browser', lambda *args: observed('failed'))
    calls=[]
    def repair(*args):
        calls.append(1)
        return json.dumps({'files':{'index.html':'Candidate '+str(len(calls))}})
    report=store.execute(store.prepare(reference(contract), repair=True),repair)
    assert len(calls)==2 and len(report['data']['attempts'])==3
    assert report['verification']=='candidate_failed'
    assert (root/'index.html').read_text().startswith('<button')
    monkeypatch.setattr(store, '_browser', lambda *args: observed('unverified'))
    report=store.execute(store.prepare(reference(contract), repair=True),repair)
    assert len(calls)==2 and report['verification']=='unverified'


def test_external_edits_block_apply_and_no_tool_or_undeclared_output_can_be_written(delivery, monkeypatch):
    store, contract, root=delivery
    monkeypatch.setattr(store, '_browser',lambda *args: observed('failed'))
    bad=store.execute(store.prepare(reference(contract),repair=True),lambda *args:json.dumps({'files':{'.env':'wrong'}}))
    assert bad['status']=='failed' and not (root/'.env').exists()
    monkeypatch.setattr(store, '_browser',lambda identity,n,*args: observed('failed' if n==0 else 'passed'))
    report=store.execute(store.prepare(reference(contract),repair=True),lambda *args:json.dumps({'files':{'index.html':'candidate'}}))
    (root/'index.html').write_text('Keep external work')
    with pytest.raises(ProjectConflictError):
        store.apply(report['id'],report['proof'])
    assert (root/'index.html').read_text()=='Keep external work'


def test_handoff_is_explicit_atomic_and_applied_once(delivery, monkeypatch):
    store, contract, _=delivery
    monkeypatch.setattr(store, '_browser',lambda *args:observed('passed'))
    report=store.execute(store.prepare(reference(contract)))
    state=store.services.project.snapshot()
    entries=[{'kind':'decision','text':'Use forest green'},{'kind':'todo','text':'Add pricing'},
             {'kind':'output','text':'Current website','file_path':'index.html'}]
    with pytest.raises(ProjectConflictError):
        store.handoff(report['id'],report['proof'],state['project_id'],state['revision']+1,entries)
    assert store.services.project.snapshot()['entries']==[]
    result=store.handoff(report['id'],report['proof'],state['project_id'],state['revision'],entries)
    assert len(result['project']['entries'])==3
    assert 'Use forest green' in store.services.project.context_block()
    with pytest.raises(ValueError):
        store.handoff(report['id'],report['proof'],state['project_id'],result['project']['revision'],entries)


def test_concurrent_checks_stop_recovery_and_cli_read(delivery, monkeypatch):
    store, contract, _=delivery
    prepared=store.prepare(reference(contract))
    with pytest.raises(RuntimeError):
        store.prepare(reference(contract))
    store.stop(prepared[0])
    report=store.execute(prepared)
    assert report['status']=='stopped' and report['verification']=='unverified'
    result=CliRunner().invoke(cli,['delivery','--report',report['id']])
    assert result.exit_code==0 and 'stopped' in result.stdout
    store._update(report['id'],status='running')
    store.recover()
    assert store.report(report['id'])['status']=='interrupted'


def test_api_auth_and_acceptance_bound_to_actual_task(delivery):
    store, contract, _=delivery
    with TestClient(create_app()) as client:
        updated=client.post('/api/delivery/contract',json={**contract['data'],'expected_version':1})
        assert updated.status_code==200
        stale=client.post('/api/ask/stream',json={'task':'Build the site','delivery_contract':reference(contract)})
        assert stale.status_code==409
        assert client.post('/api/delivery/contract',json={**contract['data'],'expected_version':2,'passed':True}).status_code==422
        assert client.post('/api/delivery/check',json={**reference(updated.json()),'repair':False},headers={'Origin':'https://evil.invalid'}).status_code==403


def test_acceptance_is_frozen_through_dispatch_and_new_tasks_get_new_criteria(delivery):
    from pantheon.core.base import Task
    from tests.conftest import MockLLMClient
    from tests.test_hermes import _build_hermes
    store,contract,_=delivery
    mock=MockLLMClient()
    mock.add_response('Website draft')
    hermes,_=_build_hermes(mock)
    text=store.acceptance_context(reference(contract))
    hermes.dispatch(Task(content='Build the site',mode='role:hephaestus',acceptance=text))
    assert 'Show the product' in json.dumps(mock.calls)
    mock.calls.clear()
    hermes.dispatch(Task(content='An unrelated task',mode='role:hephaestus'))
    assert 'Show the product' not in json.dumps(mock.calls)


def test_repair_budget_is_cumulative_and_stops_before_another_provider_call(delivery, monkeypatch):
    from types import SimpleNamespace

    from pantheon.core.delivery import model_repairer
    from pantheon.llm.base import BaseLLMClient
    store, contract, _ = delivery
    calls = []
    class Client(BaseLLMClient):
        provider_name = 'fixture'
        def complete(self, messages, model='', system='', **kwargs):
            calls.append(1)
            return json.dumps({'files': {'index.html': 'Candidate'}})
    client = Client()
    client.budget = store.services.budget
    store.services.budget.save_policy({'task_requests': 1})
    role = SimpleNamespace(llm_client=client, model='fixture-model')
    pantheon = SimpleNamespace(get_role=lambda name: role)
    monkeypatch.setattr(store, '_browser', lambda *args: observed('failed'))
    result = store.execute(store.prepare(reference(contract), repair=True), model_repairer(pantheon))
    assert len(calls) == 1 and result['usage']['requests'] == 1
    assert result['status'] == 'failed' and 'request limit reached' in result['data']['error']


def test_reviewed_apply_rolls_back_own_writes_if_a_later_write_fails(delivery, monkeypatch):
    store, contract, root = delivery
    (root/'style.css').write_text('original style')
    contract = store.save_contract({**contract['data'], 'files':['index.html','style.css']}, 1)
    monkeypatch.setattr(store, '_browser',lambda identity,n,*args:observed('failed' if n==0 else 'passed'))
    before = (root/'index.html').read_text()
    result = store.execute(store.prepare(reference(contract),repair=True),lambda *args:json.dumps({'files':{'index.html':'Candidate','style.css':'new style'}}))
    original = store.services.project.write_reviewed
    def writer(name, text, expected_hash):
        if name == 'style.css':
            raise OSError('fixture write failure')
        return original(name, text, expected_hash)
    monkeypatch.setattr(store.services.project, 'write_reviewed', writer)
    with pytest.raises(OSError):
        store.apply(result['id'],result['proof'])
    assert (root/'index.html').read_text() == before
    assert (root/'style.css').read_text() == 'original style'


def test_cli_check_returns_nonzero_for_failed_evidence(delivery, monkeypatch):
    store, _, _ = delivery
    monkeypatch.setattr(DeliveryStore, '_browser', lambda *args: observed('failed'))
    result = CliRunner().invoke(cli, ['delivery','--context','site','--run'])
    assert result.exit_code == 2 and 'failed' in result.stdout


def test_repairs_use_reviewed_project_state_and_refuse_obsolete_context(delivery, monkeypatch):
    store, contract, root = delivery
    state = store.services.project.snapshot()
    store.services.project.save({'project_id':state['project_id'],'expected_revision':state['revision'],
                                 'kind':'decision','text':'Keep forest green','status':'confirmed'})
    monkeypatch.setattr(store, '_browser', lambda identity,n,*args:observed('failed' if n==0 else 'passed'))
    contexts = []
    def repair(spec, failures, files, attempt, project_context):
        contexts.append(project_context)
        return json.dumps({'files':{'index.html':'Candidate preserving forest green'}})
    result = store.execute(store.prepare(reference(contract),repair=True),repair)
    assert 'Keep forest green' in contexts[0]
    latest = store.services.project.snapshot()
    store.services.project.save({'project_id':latest['project_id'],'expected_revision':latest['revision'],
                                 'kind':'decision','text':'A newer confirmed decision','status':'confirmed'})
    assert store.report(result['id'])['verification']=='stale'
    with pytest.raises(ProjectConflictError):
        store.apply(result['id'], result['proof'])
    assert (root/'index.html').read_text().startswith('<button')
