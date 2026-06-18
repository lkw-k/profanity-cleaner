import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'feedback.db')

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            message_id  TEXT PRIMARY KEY,
            content     TEXT NOT NULL,
            label       INTEGER DEFAULT 1,
            created_at  TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()

def is_already_saved(message_id: str) -> bool:
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT 1 FROM feedback WHERE message_id=?", (message_id,)).fetchone()
    con.close()
    return row is not None

def save_profanity(message_id: str, content: str):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT OR IGNORE INTO feedback (message_id, content, label, created_at) VALUES (?,?,1,?)",
        (message_id, content, datetime.utcnow().isoformat())
    )
    con.commit()
    con.close()

def save_false_positive(message_id: str, content: str):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT OR IGNORE INTO feedback (message_id, content, label, created_at) VALUES (?,?,0,?)",
        (message_id, content, datetime.utcnow().isoformat())
    )
    con.commit()
    con.close()
