import logging
from typing import Any
from src.infra.events import get_event_bus

logger = logging.getLogger(__name__)

class CloudOtpAuthService:
    async def sign_up(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Multi-pass sign up via OTP."""
        email = payload.get("email")
        otp = payload.get("otp")
        
        if not email:
            return {"status": "error", "message": "Email is required"}
            
        if not otp:
            # Step 1: Send OTP
            # In a real implementation, we'd generate a code, save it in the DB linked to this email,
            # and publish a notification event.
            code = "123456" # Mock
            get_event_bus().publish("notification.send", {
                "recipient": email,
                "subject": "Your Verification Code",
                "message": f"Your code is {code}"
            })
            return {"status": "requires_otp", "message": "Code sent."}
            
        # Step 2: Verify OTP
        # In a real implementation, we'd verify the code against the DB, 
        # create the user if valid, and return a JWT.
        if otp == "123456":
            return {"status": "success", "token": "mock_jwt_token"}
            
        return {"status": "error", "message": "Invalid code"}
        
    async def sign_in(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Sign in for cloud could also use OTP or password."""
        return {"status": "error", "message": "Not implemented"}
