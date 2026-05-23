import pytest


@pytest.fixture
def sample_members():
    return {
        "111": {"name": "Serge", "timezone": "America/Vancouver"},
        "222": {"name": "Ekaterina", "timezone": "Europe/Warsaw"},
        "333": {"name": "Pavel_P", "timezone": "Europe/Minsk"},
    }


@pytest.fixture
def sample_responses():
    return {
        "111": "yes",
        "222": "no",
        "333": "pending",
    }


@pytest.fixture
def sample_session_data():
    return {
        "members": {
            "111": {"name": "Serge", "timezone": "America/Vancouver"},
            "222": {"name": "Ekaterina", "timezone": "Europe/Warsaw"},
        },
        "event": {
            "status": "idle",
            "proposal_id": None,
            "current_time": None,
            "proposal_author": None,
            "deadline": None,
            "responses": {},
        },
        "last_active": "2026-05-05T12:00:00+00:00",
    }
