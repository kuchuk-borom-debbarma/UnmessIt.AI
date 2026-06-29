import sys
from pathlib import Path

# Add server dir to sys.path so we can import src
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
import jwt
from src.infra.sqlite import init_db, get_connection
from src.services.auth import get_auth_service
from src.services.auth.local_impl import JWT_SECRET, JWT_ALGORITHM
from src.repositories import source_chunks as source_chunks_repo
from src.repositories import source_chunk_vectors, recall_key_vectors

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
    
    print("Migrating source_chunks...")
    cursor = conn.execute("UPDATE source_chunks SET user_id = ? WHERE user_id IS NULL", (user_id,))
    print(f"Updated {cursor.rowcount} source_chunks")
    
    print("Migrating recall_links...")
    cursor = conn.execute("UPDATE recall_links SET user_id = ? WHERE user_id IS NULL", (user_id,))
    print(f"Updated {cursor.rowcount} recall_links")
    
    conn.commit()
    
    print("Rebuilding Chroma vectors...")
    chunks = source_chunks_repo.get_by_ids([r["id"] for r in conn.execute("SELECT id FROM source_chunks").fetchall()])
    if chunks:
        source_chunk_vectors.index(chunks)
        print(f"Indexed {len(chunks)} source chunks")
        
    keys = [dict(r) for r in conn.execute("SELECT * FROM recall_keys").fetchall()]
    if keys:
        recall_key_vectors.index(keys)
        print(f"Indexed {len(keys)} recall keys")
        
    print("Migration complete!")
    
if __name__ == "__main__":
    asyncio.run(main())
