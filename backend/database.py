import sqlite3
import json
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "thea.db")

def get_db_connection():
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Memories: Stores what Thea has seen or talked about
    c.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,  -- 'observation' or 'chat'
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            meta TEXT -- JSON string for extra data (e.g. image path, sender)
        )
    ''')
    
    # System State: Stores mood, last active, etc.
    c.execute('''
        CREATE TABLE IF NOT EXISTS system_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def add_memory(mem_type, content, meta=None):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO memories (type, content, meta) VALUES (?, ?, ?)",
        (mem_type, content, json.dumps(meta) if meta else None)
    )
    conn.commit()
    conn.close()

def get_recent_memories(limit=10):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM memories ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows][::-1] # Return in chronological order

# Initialize on import
init_db()
