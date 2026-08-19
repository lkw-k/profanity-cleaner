import sqlite3

import pytest

import database


@pytest.fixture
def db(tmp_path, monkeypatch):
    """실제 feedback.db 대신 임시 DB를 쓰도록 모듈 상수를 교체한다."""
    path = tmp_path / "feedback.db"
    monkeypatch.setattr(database, "DB_PATH", str(path))
    database.init_db()
    return path


def test_init_db_creates_table(db):
    con = sqlite3.connect(db)
    row = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='feedback'"
    ).fetchone()
    con.close()
    assert row is not None


def test_init_db_is_idempotent(db):
    database.init_db()


def test_is_already_saved_before_and_after_save(db):
    assert database.is_already_saved("111") is False
    database.save_profanity("111", "테스트 메시지")
    assert database.is_already_saved("111") is True


def test_save_profanity_ignores_duplicate_message_id(db):
    database.save_profanity("222", "첫 번째")
    database.save_profanity("222", "두 번째")

    con = sqlite3.connect(db)
    rows = con.execute(
        "SELECT content FROM feedback WHERE message_id='222'"
    ).fetchall()
    con.close()
    assert rows == [("첫 번째",)]


def test_save_profanity_stores_content_and_label(db):
    database.save_profanity("333", "아 진짜")

    con = sqlite3.connect(db)
    content, label, created_at = con.execute(
        "SELECT content, label, created_at FROM feedback WHERE message_id='333'"
    ).fetchone()
    con.close()
    assert content == "아 진짜"
    assert label == 1
    assert created_at
