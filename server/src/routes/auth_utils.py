from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from src.services.auth import AuthService, get_auth_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user_id(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> str:
    """FastAPI dependency to secure routes and extract user_id."""
    user = auth_service.verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user["id"]
