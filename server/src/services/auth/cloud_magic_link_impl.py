import logging
from typing import Any
from src.infra.events import get_event_bus

logger = logging.getLogger(__name__)

class CloudMagicLinkAuthService:
    async def sign_up(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Multi-pass sign up via Magic Link."""
        return {"status": "error", "message": "Not implemented"}
        
    async def sign_in(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Sign in via Magic Link."""
        email = payload.get("email")
        if not email:
            return {"status": "error", "message": "Email is required"}
            
        # In a real implementation, we'd generate a link and save the token.
        link = f"http://localhost:3000/auth/verify?token=mock_token"
        get_event_bus().publish("notification.send", {
            "recipient": email,
            "subject": "Your Magic Login Link",
            "message": f"Click here to login: {link}"
        })
        
        return {"status": "check_email", "message": "Magic link sent."}
