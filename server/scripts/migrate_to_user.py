import sys
from pathlib import Path

# Add server dir to sys.path so we can import src
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
import jwt
from src.infra.sqlite import init_db, get_connection
from src.services.auth import get_auth_service
from src.services.auth.local_impl import JWT_SECRET, JWT_ALGORITHM

async def main():
    print("Initializing Database...")
    init_db()
    
    auth = get_auth_service()
    
    # 1. Create or get user
    print("Creating user 'user'...")
    signup_res = await auth.sign_up({"username": "user", "password": "user"})
    if signup_res["status"] == "error" and signup_res["message"] == "User already exists":
        print("User already exists, signing in...")
        signin_res = await auth.sign_in({"username": "user", "password": "user"})
        token = signin_res["token"]
    else:
        token = signup_res["token"]
        
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    user_id = payload["sub"]
    
    print(f"User ID: {user_id}")
    
    # 2. Migrate tables
    conn = get_connection()
    
    print("Migrating raw_inputs...")
    cursor = conn.execute("UPDATE raw_inputs SET user_id = ? WHERE user_id IS NULL", (user_id,))
    print(f"Updated {cursor.rowcount} raw_inputs")
    
    print("Migrating recall_keys...")
    cursor = conn.execute("UPDATE recall_keys SET user_id = ? WHERE user_id IS NULL", (user_id,))
    print(f"Updated {cursor.rowcount} recall_keys")
    
    conn.commit()
    print("Migration complete!")
    
if __name__ == "__main__":
    asyncio.run(main())
