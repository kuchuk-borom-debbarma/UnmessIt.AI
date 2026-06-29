from __future__ import annotations

from fastapi import APIRouter, Depends

from src.repositories import tags
from src.routes.auth_utils import get_current_user_id

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/")
async def list_tags(user_id: str = Depends(get_current_user_id)) -> dict:
    return {"status": "success", "data": tags.list_tags(user_id)}
