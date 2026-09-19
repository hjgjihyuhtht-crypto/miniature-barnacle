"""Memory CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.auth import get_user_id, require_api_key
from backend.memory.memory_manager import get_memory_manager
from backend.models import MemoryCreate, MemoryOut, MemoryUpdate

router = APIRouter(prefix="/v1/memory", tags=["memory"])


@router.get("")
async def list_memory(
    request: Request,
    q: str | None = Query(default=None),
    _: str = Depends(require_api_key),
):
    user_id = get_user_id(request)
    items = await get_memory_manager().long.list(user_id, query=q)
    return {"data": items}


@router.post("")
async def create_memory(
    body: MemoryCreate,
    request: Request,
    _: str = Depends(require_api_key),
):
    user_id = get_user_id(request)
    item = await get_memory_manager().long.create(
        user_id=user_id,
        type=body.type,
        content=body.content,
        source=body.source,
        importance=body.importance,
    )
    return item


@router.put("/{memory_id}")
async def update_memory(
    memory_id: str,
    body: MemoryUpdate,
    _: str = Depends(require_api_key),
):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    item = await get_memory_manager().long.update(memory_id, **fields)
    if not item:
        raise HTTPException(404, "Memory not found")
    return item


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str, _: str = Depends(require_api_key)):
    ok = await get_memory_manager().long.delete(memory_id)
    if not ok:
        raise HTTPException(404, "Memory not found")
    return {"deleted": True, "id": memory_id}


@router.delete("")
async def delete_all_memory(request: Request, _: str = Depends(require_api_key)):
    user_id = get_user_id(request)
    count = await get_memory_manager().long.delete_all(user_id)
    return {"deleted": count}
