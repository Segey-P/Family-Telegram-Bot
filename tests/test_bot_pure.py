from unittest.mock import patch

from bot import (
    DEFAULT_TIMEZONE,
    ensure_member,
    generate_time_options,
    get_responses_text,
    parse_time_input,
    resolve_timezone,
    format_time_in_tz,
)


class TestParseTimeInput:
    def test_hh_colon_mm(self):
        assert parse_time_input("07:20") == "07:20"

    def test_hh_dot_mm(self):
        assert parse_time_input("7.30") == "07:30"

    def test_hh_space_mm(self):
        assert parse_time_input("7 45") == "07:45"

    def test_hhmm_four_digits(self):
        assert parse_time_input("1930") == "19:30"

    def test_hmm_three_digits(self):
        assert parse_time_input("720") == "07:20"

    def test_plain_hour(self):
        assert parse_time_input("9") == "09:00"

    def test_invalid_hour(self):
        assert parse_time_input("25:00") is None

    def test_invalid_minute(self):
        assert parse_time_input("12:60") is None

    def test_garbage(self):
        assert parse_time_input("abc") is None

    def test_empty_string(self):
        assert parse_time_input("") is None


class TestResolveTimezone:
    def test_exact_match(self):
        name, err = resolve_timezone("Europe/Berlin")
        assert err == ""
        assert name == "Europe/Berlin"

    def test_fuzzy_match(self):
        name, err = resolve_timezone("Vancouver")
        assert err == ""
        assert name == "America/Vancouver"

    def test_ambiguous_returns_error(self):
        name, err = resolve_timezone("America")
        assert name is None
        assert "Неоднозначно" in err

    def test_not_found_returns_error(self):
        name, err = resolve_timezone("Mars/Olympus")
        assert name is None
        assert "Неизвестная" in err


class TestGenerateTimeOptions:
    def test_basic_generation(self):
        options = generate_time_options("17:00")
        assert options == ["16:00", "17:00", "18:00", "19:00", "20:00", "21:00"]

    def test_wraps_past_midnight(self):
        options = generate_time_options("01:00")
        assert options == ["00:00", "01:00", "02:00", "03:00", "04:00", "05:00"]


class TestFormatTimeInTz:
    def test_basic_conversion(self):
        result = format_time_in_tz("12:00", "UTC", "Europe/Berlin")
        assert result == "14:00"

    def test_same_timezone(self):
        result = format_time_in_tz("10:30", "Europe/Minsk", "Europe/Minsk")
        assert result == "10:30"

    def test_negative_offset(self):
        result = format_time_in_tz("12:00", "UTC", "America/Vancouver")
        assert result == "05:00"

    def test_invalid_from_tz_returns_original(self):
        result = format_time_in_tz("12:00", "Not/ATimezone", "UTC")
        assert result == "12:00"


class TestGetResponsesText:
    def test_empty_responses(self):
        assert get_responses_text({}, {"111": {"name": "Alice"}}) == ""

    def test_all_yes(self, sample_members):
        responses = {"111": "yes", "222": "yes", "333": "yes"}
        text = get_responses_text(responses, sample_members)
        assert "✅" in text
        assert "Serge" in text

    def test_mixed_votes(self, sample_members, sample_responses):
        text = get_responses_text(sample_responses, sample_members)
        assert "✅ Serge" in text
        assert "❌ Ekaterina" in text
        assert "⏳" in text
        assert "Pavel" in text

    def test_unknown_user_id_skipped(self):
        responses = {"999": "yes"}
        members = {"111": {"name": "Alice"}}
        assert get_responses_text(responses, members) == ""

    def test_pending_only(self, sample_members):
        responses = {"111": "pending", "222": "pending"}
        text = get_responses_text(responses, sample_members)
        assert "⏳" in text
        assert "✅" not in text
        assert "❌" not in text


class TestEnsureMember:
    """ensure_member creates chat sessions and registers users."""

    def test_new_chat_creates_session(self):
        """A brand-new chat_id gets a session dict."""
        sessions = {}
        tz = ensure_member("-1001234", "u1", "Alice", sessions)
        assert "-1001234" in sessions
        assert sessions["-1001234"]["event"]["status"] == "idle"
        assert tz == DEFAULT_TIMEZONE

    def test_first_user_is_admin(self):
        """The first user in a chat gets admin=True."""
        sessions = {}
        ensure_member("-1001", "u1", "Alice", sessions)
        assert sessions["-1001"]["members"]["u1"]["is_admin"] is True

    def test_second_user_not_admin(self):
        """Subsequent users get admin=False."""
        sessions = {}
        ensure_member("-1001", "u1", "Alice", sessions)
        ensure_member("-1001", "u2", "Bob", sessions)
        assert sessions["-1001"]["members"]["u2"]["is_admin"] is False

    def test_existing_chat_does_not_overwrite(self):
        """Calling ensure_member again for the same user skips re-creation."""
        sessions = {}
        ensure_member("-1001", "u1", "Alice", sessions)
        ensure_member("-1001", "u1", "Alice_Renamed", sessions)
        assert sessions["-1001"]["members"]["u1"]["name"] == "Alice"  # original kept

    def test_timezone_from_global_cache(self):
        """If global cache has a timezone, it is used instead of default."""
        sessions = {}
        with patch("bot.get_user_timezone", return_value="Europe/Berlin"):
            tz = ensure_member("-1001", "u1", "Alice", sessions)
        assert tz == "Europe/Berlin"
        assert sessions["-1001"]["members"]["u1"]["timezone"] == "Europe/Berlin"

    def test_timezone_fallback_to_default(self):
        """Without global cache, new users get DEFAULT_TIMEZONE."""
        sessions = {}
        with patch("bot.get_user_timezone", return_value=None):
            tz = ensure_member("-1001", "u1", "Alice", sessions)
        assert tz == DEFAULT_TIMEZONE

    def test_existing_user_updated_from_global_cache(self):
        """Existing user with default tz gets updated when global cache has a value."""
        sessions = {}
        # First call with no global cache → default timezone
        with patch("bot.get_user_timezone", return_value=None):
            ensure_member("-1001", "u1", "Alice", sessions)

        # Second call with global cache set → tz updated
        with patch("bot.get_user_timezone", return_value="America/Vancouver"):
            tz = ensure_member("-1001", "u1", "Alice", sessions)

        assert tz == "America/Vancouver"
        assert sessions["-1001"]["members"]["u1"]["timezone"] == "America/Vancouver"

    def test_existing_user_with_custom_tz_not_overwritten(self):
        """If user already has a non-default timezone, global cache doesn't overwrite."""
        sessions = {"-1001": {"members": {"u1": {
            "name": "Alice",
            "timezone": "Asia/Tokyo",
            "first_seen": "2026-01-01T00:00:00+00:00",
            "is_admin": True,
        }}, "event": {"status": "idle"}, "last_active": "2026-01-01T00:00:00+00:00"}}
        with patch("bot.get_user_timezone", return_value="Europe/Berlin"):
            tz = ensure_member("-1001", "u1", "Alice", sessions)
        assert tz == "Asia/Tokyo"  # unchanged
