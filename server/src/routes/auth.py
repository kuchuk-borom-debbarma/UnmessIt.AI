from fastapi import APIRouter, Depends, Request
from src.routes.auth_utils import get_current_user_id
from src.services.auth import get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/sign_up")
async def sign_up(request: Request) -> dict:
    """Initiate or complete a sign-up flow depending on payload and backend implementation."""
    payload = await request.json()
    return await get_auth_service().sign_up(payload)
    
@router.post("/sign_in")
async def sign_in(request: Request) -> dict:
    """Initiate or complete a sign-in flow depending on payload and backend implementation."""
    payload = await request.json()
    return await get_auth_service().sign_in(payload)


@router.get("/me")
async def me(user_id: str = Depends(get_current_user_id)) -> dict:
    return {"id": user_id}


@router.post("/logout")
async def logout() -> dict:
    return {"status": "ok"}
