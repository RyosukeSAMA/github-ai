"""Shared project-state routes; existing host/auth/origin middleware applies."""
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from pantheon.core.project import ProjectConflictError


class ProjectReview(BaseModel):
    model_config = ConfigDict(extra='forbid')
    project_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    revision: int = Field(ge=0)
    fingerprint: str = Field(pattern=r'^[a-f0-9]{64}$')


class ProjectEntryRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    project_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    expected_revision: int = Field(ge=0)
    kind: Literal['goal', 'decision', 'output', 'todo', 'check']
    text: str = Field(min_length=1, max_length=4000)
    status: str = Field(default='', max_length=30)
    reference: str = Field(default='', max_length=300)
    file_path: str = Field(default='', max_length=400)
    replaces: str = Field(default='', max_length=40)
    acknowledge_file: bool = False
    expected_hash: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')


class ProjectDeleteRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    project_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    expected_revision: int = Field(ge=0)


class ContinueRequest(ProjectReview):
    intent: str = Field(min_length=1, max_length=12000)


def install_project_routes(app, store):
    router = APIRouter(prefix='/api/project')

    def perform(callback):
        try:
            return callback()
        except ProjectConflictError as exc:
            raise HTTPException(409, str(exc)) from exc
        except (ValueError, OSError) as exc:
            raise HTTPException(400, str(exc) if isinstance(exc, ValueError) else 'Could not safely inspect the file.') from exc

    @router.get('')
    def project_state():
        return store.snapshot()

    @router.post('/entries')
    def create_entry(body: ProjectEntryRequest):
        perform(lambda: store.save(body.model_dump()))
        return store.snapshot()

    @router.patch('/entries/{entry_id}')
    def edit_entry(entry_id: str, body: ProjectEntryRequest):
        perform(lambda: store.save(body.model_dump(), entry_id))
        return store.snapshot()

    @router.delete('/entries/{entry_id}')
    def delete_entry(entry_id: str, body: ProjectDeleteRequest):
        perform(lambda: store.delete(entry_id, body.expected_revision, body.project_id))
        return store.snapshot()

    @router.post('/continue')
    def prepare_continue(body: ContinueRequest):
        perform(lambda: store.validate_review(body.model_dump()))
        return {'prompt': body.intent.strip(), 'project_review': body.model_dump(exclude={'intent'}),
                'note': 'Draft prepared. No task was sent. Project context will be read again when execution starts.'}

    app.include_router(router)
