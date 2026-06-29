from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.repositories import notes, tags
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
    tags: list[str] | None = None


def _with_tags(note: dict) -> dict:
    return {**note, "tags": tags.get_for_note(note["id"])}


@router.get("/")
async def list_notes(
    directory_id: str | None = None,
    all: bool = False,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    return {"status": "success", "data": [_with_tags(note) for note in notes.list_notes(user_id, directory_id, all)]}


@router.get("/{note_id}")
async def get_note(note_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
    note = notes.get(note_id, user_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "success", "data": _with_tags(note)}


@router.post("/")
async def create_note(
    request: NoteCreateRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    try:
        note_id = await get_notes_service().create_note(
            text=request.text,
            user_id=user_id,
            directory_id=request.directory_id,
            tag_names=request.tags,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "created", "note_id": note_id}


@router.put("/{note_id}")
async def update_note(
    note_id: str,
    request: NoteUpdateRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    try:
        success = await get_notes_service().update_note(
            note_id=note_id,
            text=request.text,
            user_id=user_id,
            directory_id=request.directory_id,
            tag_names=request.tags,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not success:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "updated", "note_id": note_id}


@router.delete("/{note_id}")
async def delete_note(note_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
    if not notes.delete(note_id, user_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "deleted", "note_id": note_id}
