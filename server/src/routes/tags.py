from __future__ import annotations

from fastapi import APIRouter, Depends

from src.repositories import tags
from src.routes.auth_utils import get_current_user_id

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/")
async def list_tags(page: int = 1, limit: int = 20, user_id: str = Depends(get_current_user_id)) -> dict:
    page = max(1, page)
    limit = max(1, min(limit, 50))
    result = tags.list_tags(user_id, page, limit)
    return {"status": "success", **result}


@router.get("/search")
async def search_tags(q: str = "", limit: int = 20, cursor: int = 0, user_id: str = Depends(get_current_user_id)) -> dict:
    return {"status": "success", "data": tags.search_tags(user_id, q, limit, cursor)}
