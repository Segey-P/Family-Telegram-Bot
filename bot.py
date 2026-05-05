import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    GroupHandler,
)

from session import Session

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

SETTINGS_FILE = Path("settings.json")
SESSIONS_FILE = Path("sessions.json")


def load_settings() -> dict:
    with open(SETTINGS_FILE) as f:
        return json.load(f)


def load_sessions() -> dict:
    if SESSIONS_FILE.exists():
        with open(SESSIONS_FILE) as f:
            return json.load(f)
    return {}


def save_sessions(sessions: dict):
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f, indent=2, default=str)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start in private chat."""
    user = update.message.from_user
    chat_id = update.message.chat_id

    text = (
        "👋 Привет! Я помогу координировать еженедельный созвон.\n\n"
        "Сначала установите вашу временную зону:\n"
        "`/таймзона Европа/Берлин`\n\n"
        "Для справки: `/помощь`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /таймзона command."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Формат: `/таймзона Европа/Берлин`",
            parse_mode="Markdown"
        )
        return

    tz_name = " ".join(context.args)

    try:
        pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        await update.message.reply_text(
            f"❌ Неизвестная временная зона: `{tz_name}`\n\n"
            "Используйте формат: `Европа/Берлин`\n"
            "Список: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones",
            parse_mode="Markdown"
        )
        return

    sessions = load_sessions()
    chat_id = str(update.message.chat_id)
    user_id = str(update.message.from_user.id)

    if chat_id not in sessions:
        sessions[chat_id] = {
            "members": {},
            "event": {"status": "idle"},
            "last_active": datetime.now(timezone.utc).isoformat()
        }

    if user_id not in sessions[chat_id]["members"]:
        sessions[chat_id]["members"][user_id] = {
            "name": update.message.from_user.first_name or "User",
            "timezone": None,
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "is_admin": len(sessions[chat_id]["members"]) == 0
        }

    sessions[chat_id]["members"][user_id]["timezone"] = tz_name
    save_sessions(sessions)

    await update.message.reply_text(f"✅ Сохранено: {tz_name}")


async def handle_mytime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /моевремя command."""
    sessions = load_sessions()
    chat_id = str(update.message.chat_id)
    user_id = str(update.message.from_user.id)

    if chat_id not in sessions or user_id not in sessions[chat_id]["members"]:
        await update.message.reply_text("⚠️ Пожалуйста, установите вашу временную зону: `/таймзона Европа/Берлин`", parse_mode="Markdown")
        return

    user_tz_name = sessions[chat_id]["members"][user_id]["timezone"]
    if not user_tz_name:
        await update.message.reply_text("⚠️ Пожалуйста, установите вашу временную зону: `/таймзона Европа/Берлин`", parse_mode="Markdown")
        return

    try:
        user_tz = pytz.timezone(user_tz_name)
    except pytz.UnknownTimeZoneError:
        await update.message.reply_text("❌ Ошибка с вашей временной зоной. Переустановите: `/таймзона Европа/Берлин`", parse_mode="Markdown")
        return

    settings = load_settings()
    base_tz = pytz.timezone(settings["base_timezone"])
    call_time_str = settings["call_time"]

    # Parse call time (HH:MM)
    hour, minute = map(int, call_time_str.split(":"))

    # Create a Sunday datetime in base timezone
    now_utc = datetime.now(timezone.utc)
    now_base = now_utc.astimezone(base_tz)

    # Find next Sunday
    days_ahead = 6 - now_base.weekday()  # Sunday = 6
    if days_ahead <= 0:
        days_ahead += 7

    next_sunday_base = now_base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    next_sunday_base = next_sunday_base.replace(day=next_sunday_base.day + days_ahead)

    # Convert to user timezone
    next_sunday_user = next_sunday_base.astimezone(user_tz)
    current_user = now_utc.astimezone(user_tz)

    text = (
        f"🕐 <b>Ваше текущее время</b>\n"
        f"{current_user.strftime('%H:%M (%Z)')}\n\n"
        f"🗓️ <b>Следующий созвон (воскресенье)</b>\n"
        f"{next_sunday_user.strftime('%H:%M (%Z)')}"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /помощь command."""
    text = (
        "<b>Команды</b>\n\n"
        "<b>Пользователь:</b>\n"
        "`/таймзона Европа/Берлин` — установить вашу временную зону\n"
        "`/моевремя` — показать ваше текущее время\n"
        "`/помощь` — этот список\n\n"
        "<b>Администратор:</b>\n"
        "`/время 10:00 Америка/Ванкувер` — обновить время созвона\n"
        "`/опрос вкл` — включить еженедельные опросы\n"
        "`/опрос выкл` — отключить еженедельные опросы"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /время command (admin only)."""
    sessions = load_sessions()
    chat_id = str(update.message.chat_id)
    user_id = str(update.message.from_user.id)

    if chat_id not in sessions or user_id not in sessions[chat_id]["members"]:
        await update.message.reply_text("❌ Только администратор может это делать.")
        return

    is_admin = sessions[chat_id]["members"][user_id].get("is_admin", False)
    if not is_admin:
        await update.message.reply_text("❌ Только администратор может это делать.")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Формат: `/время 10:00 Америка/Ванкувер`",
            parse_mode="Markdown"
        )
        return

    time_str = context.args[0]
    tz_name = " ".join(context.args[1:])

    try:
        pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        await update.message.reply_text(f"❌ Неизвестная временная зона: `{tz_name}`", parse_mode="Markdown")
        return

    try:
        hour, minute = map(int, time_str.split(":"))
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Неправильный формат времени. Используйте HH:MM", parse_mode="Markdown")
        return

    settings = load_settings()
    settings["call_time"] = time_str
    settings["base_timezone"] = tz_name

    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

    await update.message.reply_text(f"✅ Время обновлено: {time_str} {tz_name}")


async def handle_poll_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /опрос вкл command (admin only)."""
    sessions = load_sessions()
    chat_id = str(update.message.chat_id)
    user_id = str(update.message.from_user.id)

    if chat_id not in sessions or user_id not in sessions[chat_id]["members"]:
        await update.message.reply_text("❌ Только администратор может это делать.")
        return

    is_admin = sessions[chat_id]["members"][user_id].get("is_admin", False)
    if not is_admin:
        await update.message.reply_text("❌ Только администратор может это делать.")
        return

    settings = load_settings()
    settings["poll_enabled"] = True

    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

    await update.message.reply_text("✅ Еженедельные опросы включены.")


async def handle_poll_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /опрос выкл command (admin only)."""
    sessions = load_sessions()
    chat_id = str(update.message.chat_id)
    user_id = str(update.message.from_user.id)

    if chat_id not in sessions or user_id not in sessions[chat_id]["members"]:
        await update.message.reply_text("❌ Только администратор может это делать.")
        return

    is_admin = sessions[chat_id]["members"][user_id].get("is_admin", False)
    if not is_admin:
        await update.message.reply_text("❌ Только администратор может это делать.")
        return

    settings = load_settings()
    settings["poll_enabled"] = False

    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

    await update.message.reply_text("✅ Еженедельные опросы отключены.")


async def friday_invite_job(context: ContextTypes.DEFAULT_TYPE):
    """Scheduled job: Send Friday invite to group."""
    logger.info("Friday invite job triggered")
    # Stub for now—Phase 1.5


async def set_bot_commands(app):
    """Set bot commands for the UI."""
    commands = [
        BotCommand("таймзона", "Установить временную зону"),
        BotCommand("моевремя", "Показать ваше время"),
        BotCommand("помощь", "Список команд"),
        BotCommand("время", "Обновить время созвона (только администратор)"),
        BotCommand("опрос", "Включить/отключить опросы (только администратор)"),
    ]
    await app.bot.set_my_commands(commands)


async def post_init(app):
    """Called after bot starts."""
    await set_bot_commands(app)
    logger.info("Bot initialized")


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set")

    app = ApplicationBuilder().token(token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("таймзона", handle_timezone))
    app.add_handler(CommandHandler("моевремя", handle_mytime))
    app.add_handler(CommandHandler("помощь", handle_help))
    app.add_handler(CommandHandler("время", handle_time_command))
    app.add_handler(CommandHandler(["опрос"], handle_poll_on))  # /опрос вкл
    app.add_handler(CommandHandler(["опрос"], handle_poll_off))  # /опрос выкл

    # Post-init hook
    app.post_init = post_init

    # Scheduler (APScheduler)
    scheduler = AsyncIOScheduler()
    scheduler.start()

    logger.info("Starting bot...")
    app.run_polling(allowed_updates=[
        "message",
        "callback_query",
        "my_chat_member",
    ])


if __name__ == "__main__":
    main()
