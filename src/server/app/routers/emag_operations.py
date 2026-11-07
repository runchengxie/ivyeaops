from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from app.core.security import require_admin
from app.services import emag_operations as service
from app.services import emag_workspace, emag_jobs

router=APIRouter(dependencies=[Depends(require_admin)])


@router.get('/stores/{store_id}/clearance-review')
def clearance_review(store_id: str, baseline_snapshot_id: str | None = None):
    from app.services import emag_clearance_review
    try:
        return emag_clearance_review.read(store_id, baseline_snapshot_id)
    except (OSError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


class Draft(BaseModel):
    model_config=ConfigDict(extra='forbid')
    snapshot_id:str
    kind:str
    product_id:str=''
    title:str=Field(min_length=1,max_length=200)
    body:str=Field(min_length=1,max_length=40000)


@router.get('/stores/{store_id}/workspace')
def workspace(store_id:str):
    try:return emag_workspace.view(store_id)
    except (OSError,ValueError) as exc:raise HTTPException(404,str(exc)) from exc


@router.post('/stores/{store_id}/drafts')
def draft(store_id:str,body:Draft,actor=Depends(require_admin)):
    try:return emag_workspace.save_draft(store_id,**body.model_dump(),actor=str(actor))
    except (OSError,ValueError) as exc:raise HTTPException(409,str(exc)) from exc


@router.get('/stores/{store_id}/job')
def job(store_id:str):
    try:return emag_jobs.latest(store_id)
    except (OSError,ValueError) as exc:raise HTTPException(404,str(exc)) from exc


class Update(BaseModel):
    model_config=ConfigDict(extra='forbid')
    snapshot_id:str
    state:str
    revision:int=Field(ge=0)
    note:str=Field(min_length=1,max_length=4000)
    review_snapshot_id:str|None=None


@router.get('/stores')
def stores():
    return service.stores()


@router.get('/stores/{store_id}')
def board(store_id:str):
    try:
        return service.board(store_id)
    except (OSError,ValueError) as exc:
        raise HTTPException(404,str(exc)) from exc


@router.post('/stores/{store_id}/issues/{issue_id}')
def update(store_id:str,issue_id:str,body:Update,actor=Depends(require_admin)):
    try:
        return service.transition(store_id,body.snapshot_id,issue_id,body.state,body.revision,body.note,str(actor),body.review_snapshot_id)
    except (OSError,ValueError) as exc:
        raise HTTPException(409,str(exc)) from exc

class CommercialRecord(BaseModel):
    model_config=ConfigDict(extra='forbid')
    snapshot_id:str
    revision:int=Field(ge=0)
    inputs:dict


class ChangePreview(BaseModel):
    model_config=ConfigDict(extra='forbid')
    snapshot_id:str
    changes:dict


class Assignment(BaseModel):
    model_config=ConfigDict(extra='forbid')
    snapshot_id:str
    revision:int=Field(ge=0)
    owner:str=Field(max_length=100)
    note:str=Field(min_length=1,max_length=4000)


@router.get('/stores/{store_id}/commerce')
def commerce_view(store_id:str):
    from app.services import emag_commerce
    try:return emag_commerce.view(store_id)
    except (OSError,ValueError) as exc:raise HTTPException(404,str(exc)) from exc


@router.post('/stores/{store_id}/commerce/{product_id}')
def commerce_save(store_id:str,product_id:str,body:CommercialRecord,actor=Depends(require_admin)):
    from app.services import emag_commerce
    try:return emag_commerce.save(store_id,body.snapshot_id,product_id,body.revision,body.inputs,str(actor))
    except (OSError,ValueError) as exc:raise HTTPException(409,str(exc)) from exc


@router.post('/stores/{store_id}/preview/{product_id}')
def change_preview(store_id:str,product_id:str,body:ChangePreview):
    from app.services import emag_commerce
    try:
        snapshot=emag_commerce.source(store_id)
        if snapshot['snapshot_id']!=body.snapshot_id:raise ValueError('Evidence is stale; reload first')
        offer=next((o for o in snapshot['data']['offers'] if str(o['id'])==product_id),None)
        if offer is None:raise ValueError('Product absent from current snapshot')
        return emag_commerce.preview(snapshot,offer,body.changes)
    except (OSError,ValueError) as exc:raise HTTPException(409,str(exc)) from exc


@router.post('/stores/{store_id}/issues/{issue_id}/assignment')
def assignment(store_id:str,issue_id:str,body:Assignment,actor=Depends(require_admin)):
    try:return service.assign(store_id,body.snapshot_id,issue_id,body.revision,body.owner,body.note,str(actor))
    except (OSError,ValueError) as exc:raise HTTPException(409,str(exc)) from exc


@router.get('/stores/{store_id}/diagnostics')
def diagnostics(store_id:str):
    from app.services import emag_decisions, emag_commerce
    try:return emag_decisions.diagnose(emag_commerce.source(store_id))
    except (OSError,ValueError) as exc:raise HTTPException(404,str(exc)) from exc


@router.get('/stores/{store_id}/commerce/{product_id}/history')
def commerce_history(store_id:str,product_id:str,before_revision:int|None=None):
    from app.services import emag_commerce
    try:return emag_commerce.history(store_id,product_id,before_revision)
    except (OSError,ValueError) as exc:raise HTTPException(409,str(exc)) from exc


class PlaybookRecord(BaseModel):
    model_config = ConfigDict(extra='forbid')
    snapshot_id: str = Field(min_length=1, max_length=100)
    kind: str = Field(min_length=1, max_length=30)
    product_id: str = Field(min_length=1, max_length=200)
    payload: dict
    record_id: str | None = Field(default=None, min_length=1, max_length=100)
    revision: int = Field(default=0, ge=0, strict=True)


@router.get('/stores/{store_id}/playbooks')
def playbooks_view(store_id: str, before_sequence: int | None = Query(default=None, gt=0)):
    from app.services import emag_playbooks
    try:
        return emag_playbooks.view(store_id, before_sequence=before_sequence)
    except emag_playbooks.MissingWorkspace as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post('/stores/{store_id}/playbooks/records')
def playbooks_save(store_id: str, body: PlaybookRecord, actor=Depends(require_admin)):
    from app.services import emag_playbooks
    try:
        return emag_playbooks.save(store_id, **body.model_dump(), actor=str(actor))
    except emag_playbooks.MissingWorkspace as exc:
        raise HTTPException(404, str(exc)) from exc
    except emag_playbooks.Conflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
