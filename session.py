"""Session management for Family Telegram Bot."""

import json
from datetime import datetime, timezone
from pathlib import Path

SESSIONS_FILE = Path("sessions.json")


class Session:
    """Manage session state."""

    @staticmethod
    def load() -> dict:
        """Load sessions from file."""
        if SESSIONS_FILE.exists():
            with open(SESSIONS_FILE) as f:
                return json.load(f)
        return {}

    @staticmethod
    def save(sessions: dict):
        """Save sessions to file."""
        with open(SESSIONS_FILE, "w") as f:
            json.dump(sessions, f, indent=2, default=str)

    @staticmethod
    def init_chat(chat_id: str, sessions: dict) -> dict:
        """Initialize a chat session if it doesn't exist."""
        if chat_id not in sessions:
            sessions[chat_id] = {
                "members": {},
                "event": {
                    "status": "idle",
                    "proposal_id": None,
                    "current_time": None,
                    "proposal_author": None,
                    "deadline": None,
                    "responses": {}
                },
                "last_active": datetime.now(timezone.utc).isoformat()
            }
        return sessions

    @staticmethod
    def add_member(chat_id: str, user_id: str, first_name: str, sessions: dict) -> dict:
        """Add or retrieve a member in the chat."""
        Session.init_chat(chat_id, sessions)

        if user_id not in sessions[chat_id]["members"]:
            sessions[chat_id]["members"][user_id] = {
                "name": first_name or "User",
                "timezone": None,
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "is_admin": len(sessions[chat_id]["members"]) == 0
            }

        return sessions
