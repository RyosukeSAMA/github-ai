"""Authenticated delivery actions shared by the native proxy and Web."""
from __future__ import annotations

import asyncio
import base64
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from pantheon.core.delivery import DeliveryContract, DeliveryRef, model_repairer
from pantheon.core.project import ProjectConflictError


class ContractSave(DeliveryContract):
    expected_version: int = Field(ge=0)


class RepairModel(BaseModel):
    model_config = ConfigDict(extra='forbid')
    provider: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=200)


class CheckRequest(DeliveryRef):
    repair: bool = False
    overrides: dict[str, RepairModel] = Field(default_factory=dict, max_length=1)


class Confirmation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    proof: str = Field(pattern=r'^[a-f0-9]{64}$')
    acknowledge_requirements: bool = False


class HandoffRequest(Confirmation):
    project_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    expected_revision: int = Field(ge=0)
    entries: list[dict] = Field(max_length=24)


def install_delivery_routes(app, services, pantheon_factory):
    router = APIRouter(prefix='/api/delivery')
    store, jobs = services.delivery, {}
    app.state.delivery_jobs = jobs

    def perform(callback):
        try:
            return callback()
        except ProjectConflictError as exc:
            raise HTTPException(409, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from exc
        except (ValueError, OSError) as exc:
            raise HTTPException(400, str(exc) if isinstance(exc, ValueError) else 'Could not read the approved output files. Save them before checking.') from exc

    @router.get('/contract')
    def contract(context: str):
        value = store.contract(context=context)
        return {'contract': value, 'runs': store.list_runs(value['id']) if value else []}

    @router.post('/contract')
    def save_contract(body: ContractSave):
        return perform(lambda: store.save_contract(body.model_dump(exclude={'expected_version'}), body.expected_version))

    @router.post('/check')
    async def check(body: CheckRequest):
        reference = body.model_dump(exclude={'repair', 'overrides'})
        if set(body.overrides) - {'hephaestus'}:
            raise HTTPException(400, 'Only the coding-role model can be selected for bounded repairs.')
        overrides = {key: value.model_dump() for key, value in body.overrides.items()}
        repairer = perform(lambda: model_repairer(pantheon_factory(overrides))) if body.repair else None
        prepared = perform(lambda: store.prepare(reference, repair=body.repair))
        async def execute():
            await asyncio.to_thread(store.execute, prepared, repairer)
        task = asyncio.create_task(execute())
        jobs[prepared[0]] = task
        task.add_done_callback(lambda _task: jobs.pop(prepared[0], None))
        return store.report(prepared[0])

    @router.get('/runs/{identity}')
    def run(identity: str):
        store.recover()
        return perform(lambda: store.report(identity))

    @router.post('/runs/{identity}/stop')
    def stop(identity: str):
        return perform(lambda: store.stop(identity))

    @router.get('/runs/{identity}/diffs')
    def diffs(identity: str):
        return {'files': perform(lambda: store.diffs(identity))}

    @router.post('/runs/{identity}/apply')
    def apply(identity: str, body: Confirmation):
        return perform(lambda: store.apply(identity, body.proof))

    @router.post('/runs/{identity}/accept')
    def accept(identity: str, body: Confirmation):
        return perform(lambda: store.accept(identity, body.proof, acknowledge_requirements=body.acknowledge_requirements))

    @router.post('/runs/{identity}/handoff')
    def handoff(identity: str, body: HandoffRequest):
        return perform(lambda: store.handoff(identity, body.proof, body.project_id, body.expected_revision, body.entries))

    @router.get('/runs/{identity}/evidence/{round_number}/{name}')
    def evidence(identity: str, round_number: int, name: str):
        report = perform(lambda: store.report(identity))
        relative = f'{round_number}/{name}'
        allowed = {item for attempt in report['data']['attempts'] for item in attempt['screenshots']}
        if relative not in allowed or not re.fullmatch(r'(desktop|mobile)\.png', name) or not 0 <= round_number <= 2:
            raise HTTPException(404, 'Recorded screenshot not found.')
        path = store.root/identity/str(round_number)/name
        if not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
            raise HTTPException(404, 'Recorded screenshot is unavailable.')
        return {'mime': 'image/png', 'data': base64.b64encode(path.read_bytes()).decode()}

    @router.delete('/runs/{identity}')
    def remove(identity: str):
        perform(lambda: store.remove(identity))
        return {'removed': True}

    app.include_router(router)
