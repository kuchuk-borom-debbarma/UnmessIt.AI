from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.repositories import directories
from src.routes.auth_utils import get_current_user_id
from src.services.notes.notes_service import get_notes_service

router = APIRouter(prefix="/directories", tags=["directories"])


class DirectoryCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    parent_id: str | None = None


class DirectoryUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1)


@router.get("/")
async def list_directories(
    parent_id: str | None = None,
    subtree_of: str | None = None,
    all: bool = False,
    page: int = 1,
    limit: int = 50,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    page = max(1, page)
    limit = max(1, min(limit, 100))
    if all:
        result = directories.list_all(user_id, page, limit)
    else:
        result = directories.list_subtree(subtree_of, user_id, page, limit) if subtree_of else directories.list_children(user_id, parent_id, page, limit)
    return {"status": "success", **result}


@router.get("/{directory_id}")
async def get_directory(directory_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
    d = directories.get(directory_id, user_id)
    if not d:
        raise HTTPException(status_code=404, detail="Directory not found")
    return {"status": "success", "data": d}

@router.post("/")
async def create_directory(
    request: DirectoryCreateRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    directory_id = directories.create(request.name, user_id, request.parent_id)
    return {"status": "created", "directory_id": directory_id}


@router.put("/{directory_id}")
async def update_directory(
    directory_id: str,
    request: DirectoryUpdateRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    if not directories.update(directory_id, request.name, user_id):
        raise HTTPException(status_code=404, detail="Directory not found")
    return {"status": "updated", "directory_id": directory_id}


@router.delete("/{directory_id}")
async def delete_directory(directory_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
    if not await get_notes_service().delete_directory(directory_id, user_id):
        raise HTTPException(status_code=404, detail="Directory not found")
    return {"status": "deleted", "directory_id": directory_id}
