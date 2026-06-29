from typing import Any, Protocol

class AuthService(Protocol):
    async def sign_up(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Initiate or complete a sign-up flow."""
        ...
        
    async def sign_in(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Initiate or complete a sign-in flow."""
        ...
