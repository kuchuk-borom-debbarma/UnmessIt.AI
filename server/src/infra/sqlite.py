import sqlite3
import json
import os
from pathlib import Path
from uuid import uuid5

# Global variable to hold our single database connection
_db_connection = None

# Calculate the absolute path to server/data/sqlite.db
# __file__ is server/src/infra/sqlite.py
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = str(BASE_DIR / "data" / "sqlite.db")

def get_db_connection(db_path=DEFAULT_DB_PATH):
    """
    Returns a highly optimized, shared SQLite database connection.
    Implements a singleton pattern so multiple calls return the exact same connection.
    """
    global _db_connection
    
    # If the connection already exists, just return it
    if _db_connection is not None:
        return _db_connection
        
    # Ensure the directory exists before connecting
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # check_same_thread=False is needed in multithreaded web server environments.
    # Note: SQLite handles concurrent reads well in WAL mode, but only one concurrent writer.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    
    # Return rows as dictionary-like objects instead of tuples
    conn.row_factory = sqlite3.Row
    
    # Apply performance PRAGMAs
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")       # Enable Write-Ahead Logging for concurrent readers/writer
    conn.execute("PRAGMA synchronous = NORMAL;")     # Faster synchronization
    conn.execute("PRAGMA cache_size = -20000;")      # ~20MB cache
    conn.execute("PRAGMA temp_store = MEMORY;")      # Store temp tables/indices in RAM
    conn.execute("PRAGMA mmap_size = 30000000000;")  # Enable memory-mapped I/O (up to ~30GB)
    
    # Store the connection globally for future calls
    _db_connection = conn
    
    return _db_connection

def init_db():
    """
    Initializes the database by executing the schema.sql file.
    Should be run once when the server starts.
    """
    schema_path = BASE_DIR / "data" / "schema.sql"
    conn = get_db_connection()
    
    # Read the schema file and execute it
    with open(schema_path, 'r') as f:
        schema_script = f.read()
        
    # Execute the SQL script
    conn.executescript(schema_script)
    conn.commit()
