import pytest
import jwt
from src.services.auth import local_impl
from src.services.auth import get_auth_service
from src.services.auth.local_impl import JWT_ALGORITHM
from src.infra.sqlite import get_connection, init_db

@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    monkeypatch.setattr(local_impl, "JWT_SECRET", "test_secret_for_hs256_with_32_bytes")
    init_db()
    conn = get_connection()
    conn.execute("DELETE FROM users")
    conn.commit()

@pytest.mark.asyncio
async def test_local_auth_signup_and_signin():
    auth = get_auth_service()
    
    # 1. Sign up
    signup_res = await auth.sign_up({"username": "testuser", "password": "password123"})
    assert signup_res["status"] == "success"
    assert "token" in signup_res
    
    token = signup_res["token"]
    payload = jwt.decode(token, local_impl.JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert payload["identifier"] == "testuser"
    assert "sub" in payload
    
    # 2. Prevent duplicate sign up
    signup_res2 = await auth.sign_up({"username": "testuser", "password": "password123"})
    assert signup_res2["status"] == "error"
    
    # 3. Sign in successfully
    signin_res = await auth.sign_in({"username": "testuser", "password": "password123"})
    assert signin_res["status"] == "success"
    assert "token" in signin_res
    
    # 4. Sign in with bad password
    bad_signin = await auth.sign_in({"username": "testuser", "password": "wrongpassword"})
    assert bad_signin["status"] == "error"
    assert bad_signin["message"] == "Invalid credentials"
