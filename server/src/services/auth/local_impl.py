import time
import uuid
import jwt
import bcrypt
import logging
from typing import Any
from src.infra.sqlite import get_connection

# A simple secret key for local development JWTs.
# In production, this should be an environment variable.
JWT_SECRET = "local_secret_key"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = 86400 * 30  # 30 days

logger = logging.getLogger(__name__)

class LocalAuthService:
    async def sign_up(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Local sign up is one-pass: creates user and returns a token immediately."""
        username = payload.get("username")
        password = payload.get("password")
        
        if not username or not password:
            return {"status": "error", "message": "Username and password are required"}
            
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        
        conn = get_connection()
        user_id = str(uuid.uuid4())
        try:
            # Note: synchronous db call works in this single-tenant RAG model,
            # but usually would be wrapped in asyncio.to_thread
            conn.execute(
                "INSERT INTO users (id, identifier, password_hash) VALUES (?, ?, ?)",
                (user_id, username, hashed)
            )
            conn.commit()
        except Exception as e:
            logger.error("Failed to create user: %s", e)
            return {"status": "error", "message": "User already exists"}
            
        token = self._generate_token(user_id, username)
        return {"status": "success", "token": token}
        
    async def sign_in(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Local sign in verifies password and returns a token immediately."""
        username = payload.get("username")
        password = payload.get("password")
        
        if not username or not password:
            return {"status": "error", "message": "Username and password are required"}
            
        conn = get_connection()
        row = conn.execute("SELECT id, password_hash FROM users WHERE identifier = ?", (username,)).fetchone()
        if not row:
            return {"status": "error", "message": "Invalid credentials"}
            
        hashed = row["password_hash"]
        if not bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8")):
            return {"status": "error", "message": "Invalid credentials"}
            
        token = self._generate_token(row["id"], username)
        return {"status": "success", "token": token}
        
    def _generate_token(self, user_id: str, identifier: str) -> str:
        token_payload = {
            "sub": user_id,
            "identifier": identifier,
            "exp": int(time.time()) + JWT_EXPIRATION_SECONDS
        }
        return jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
