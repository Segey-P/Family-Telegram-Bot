def test_bot_imports():
    import bot
    assert hasattr(bot, "main")


def test_bot_pure_functions_accessible():
    import bot
    assert callable(bot.parse_time_input)
    assert callable(bot.resolve_timezone)
    assert callable(bot.generate_time_options)
    assert callable(bot.format_time_in_tz)
    assert callable(bot.format_all_member_times)
    assert callable(bot.get_responses_text)
