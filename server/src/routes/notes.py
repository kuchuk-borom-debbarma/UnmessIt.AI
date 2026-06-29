from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.routes.auth_utils import get_current_user_id
from src.services.notes import get_notes_service

router = APIRouter(prefix="/notes", tags=["notes"])


class NoteCreateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    directory_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class NoteUpdateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    directory_id: str | None = None


@router.post("/")
async def create_note(
    request: NoteCreateRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    note_id = await get_notes_service().create_note(
        text=request.text, 
        user_id=user_id, 
        directory_id=request.directory_id,
        tag_names=request.tags
    )
    return {"status": "created", "note_id": note_id}


@router.put("/{note_id}")
async def update_note(
    note_id: str,
    request: NoteUpdateRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    success = await get_notes_service().update_note(
        note_id=note_id,
        text=request.text,
        user_id=user_id,
        directory_id=request.directory_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "updated", "note_id": note_id}
