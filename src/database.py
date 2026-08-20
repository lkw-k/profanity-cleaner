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
            created_at  TEXT NOT NULL,
            trained     INTEGER NOT NULL DEFAULT 0
        )
    """)
    # trained 컬럼이 없던 기존 DB 마이그레이션
    cols = [row[1] for row in con.execute("PRAGMA table_info(feedback)")]
    if 'trained' not in cols:
        con.execute("ALTER TABLE feedback ADD COLUMN trained INTEGER NOT NULL DEFAULT 0")
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

def get_all_feedback():
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT content, label FROM feedback").fetchall()
    con.close()
    return rows

def get_untrained_feedback():
    """아직 학습에 쓰지 않은 피드백만 반환. (message_id, content, label)"""
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT message_id, content, label FROM feedback WHERE trained=0"
    ).fetchall()
    con.close()
    return rows

def mark_trained(message_ids):
    """학습에 쓴 행만 표시한다.

    학습 중에 들어온 피드백까지 싸잡아 표시하면 그 데이터는 학습 없이 버려지므로
    전체 UPDATE 대신 실제로 쓴 id만 받는다.
    """
    con = sqlite3.connect(DB_PATH)
    con.executemany(
        "UPDATE feedback SET trained=1 WHERE message_id=?",
        [(mid,) for mid in message_ids]
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
