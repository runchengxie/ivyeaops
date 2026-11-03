"""Explicit compatibility responses for unsupported claudecodeui plugins."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("")
def list_plugins() -> dict:
    return {"plugins": []}


@router.api_route("/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def plugin_unsupported(rest: str) -> JSONResponse:
    return JSONResponse(status_code=501, content={
        "error": "The native backend does not support claudecodeui plugins.",
    })
