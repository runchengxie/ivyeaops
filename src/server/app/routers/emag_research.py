"""Administrator-only local research evidence."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from app.core.security import require_admin
from app.services import emag_research as service

router = APIRouter(dependencies=[Depends(require_admin)])


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid')
    snapshot_id: str = Field(min_length=1,max_length=100)
    payload: dict
    record_id: str | None = Field(default=None,min_length=1,max_length=100)
    revision: int = Field(default=0,ge=0,strict=True)


class Import(BaseModel):
    model_config = ConfigDict(extra='forbid')
    snapshot_id: str = Field(min_length=1,max_length=100)
    rows: list[dict] = Field(min_length=1,max_length=500)


def call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except OSError as exc:
        raise HTTPException(404,str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409 if 'reload' in str(exc) or 'immutable' in str(exc) else 422,str(exc)) from exc


@router.get('/stores/{store_id}/research')
def view(store_id: str):
    return call(service.view,store_id)


@router.post('/stores/{store_id}/research')
def save(store_id: str, body: Record, actor=Depends(require_admin)):
    return call(service.save,store_id,**body.model_dump(),actor=str(actor))


@router.post('/stores/{store_id}/research/import')
def import_rows(store_id: str, body: Import, actor=Depends(require_admin)):
    return call(service.import_rows,store_id,**body.model_dump(),actor=str(actor))
