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


def test_save_false_positive_stores_label_zero(db):
    database.save_false_positive("444", "정상 메시지")

    con = sqlite3.connect(db)
    content, label = con.execute(
        "SELECT content, label FROM feedback WHERE message_id='444'"
    ).fetchone()
    con.close()
    assert content == "정상 메시지"
    assert label == 0


def test_save_false_positive_ignores_duplicate_message_id(db):
    database.save_false_positive("555", "첫 번째")
    database.save_false_positive("555", "두 번째")

    con = sqlite3.connect(db)
    rows = con.execute(
        "SELECT content FROM feedback WHERE message_id='555'"
    ).fetchall()
    con.close()
    assert rows == [("첫 번째",)]


def test_get_all_feedback_returns_content_and_label(db):
    database.save_profanity("666", "욕설 메시지")
    database.save_false_positive("777", "정상 메시지")

    rows = database.get_all_feedback()
    assert sorted(rows) == sorted([("욕설 메시지", 1), ("정상 메시지", 0)])


def test_get_all_feedback_empty(db):
    assert database.get_all_feedback() == []


def test_label_is_not_updated_when_message_id_already_exists(db):
    """INSERT OR IGNORE라 라벨이 뒤집히지 않는다. 현재 동작을 고정해둔다."""
    database.save_profanity("888", "메시지")
    database.save_false_positive("888", "메시지")

    rows = database.get_all_feedback()
    assert rows == [("메시지", 1)]
