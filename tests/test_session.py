import json
from pathlib import Path

import pytest

from session import Session


def test_session_load_nonexistent_file(tmp_path):
    SESSIONS_FILE = Path("sessions.json")
    if SESSIONS_FILE.exists():
        SESSIONS_FILE.unlink()
    result = Session.load()
    assert result == {}


def test_session_save_and_load_roundtrip(tmp_path, sample_session_data):
    chat_id = "test_chat"
    data = {chat_id: sample_session_data}
    Session.save(data)
    loaded = Session.load()
    assert chat_id in loaded
    assert loaded[chat_id]["members"]["111"]["name"] == "Serge"


def test_session_init_chat_creates_new(sample_session_data):
    sessions = {}
    chat_id = "chat_1"
    Session.init_chat(chat_id, sessions)
    assert chat_id in sessions
    assert sessions[chat_id]["event"]["status"] == "idle"


def test_session_init_chat_idempotent(sample_session_data):
    sessions = {"chat_1": sample_session_data}
    Session.init_chat("chat_1", sessions)
    assert sessions["chat_1"]["members"]["111"]["name"] == "Serge"


def test_session_add_member_first_is_admin():
    sessions = {}
    chat_id = "chat_1"
    Session.add_member(chat_id, "111", "Alice", sessions)
    assert sessions[chat_id]["members"]["111"]["is_admin"] is True


def test_session_add_member_second_not_admin():
    sessions = {}
    chat_id = "chat_1"
    Session.add_member(chat_id, "111", "Alice", sessions)
    Session.add_member(chat_id, "222", "Bob", sessions)
    assert sessions[chat_id]["members"]["111"]["is_admin"] is True
    assert sessions[chat_id]["members"]["222"]["is_admin"] is False


def test_session_add_member_existing_does_not_overwrite():
    sessions = {}
    chat_id = "chat_1"
    Session.add_member(chat_id, "111", "Alice", sessions)
    Session.add_member(chat_id, "111", "Alice_Renamed", sessions)
    assert sessions[chat_id]["members"]["111"]["name"] == "Alice"


def test_session_load_with_cleanup(tmp_path):
    original = Path("sessions.json")
    if original.exists():
        original.unlink()
    # Create a temp sessions file to verify load
    test_data = {"chat_x": {"members": {}}}
    with open("sessions.json", "w") as f:
        json.dump(test_data, f)
    try:
        loaded = Session.load()
        assert "chat_x" in loaded
    finally:
        original.unlink() if original.exists() else None
