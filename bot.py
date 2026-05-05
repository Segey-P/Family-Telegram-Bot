import asyncio
import html
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
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
        "`/tz Europe/Berlin` (или Европа/Берлин)\n\n"
        "Для справки: `/help`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tz command."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Формат: `/tz Europe/Berlin` (или любая из https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)",
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
    """Handle /help command."""
    text = (
        "<b>Команды</b>\n\n"
        "<b>Пользователь:</b>\n"
        "<code>/tz Europe/Berlin</code> — установить вашу временную зону\n"
        "<code>/mytime</code> — показать ваше текущее время\n"
        "<code>/help</code> — этот список\n\n"
        "<b>Администратор:</b>\n"
        "<code>/time 10:00 America/Vancouver</code> — обновить время созвона\n"
        "<code>/poll on</code> — включить еженедельные опросы\n"
        "<code>/poll off</code> — отключить еженедельные опросы\n"
        "<code>/debug_invite</code> — отправить опрос вручную (тестирование)\n\n"
        "<b>Примеры:</b>\n"
        "<code>/tz Europe/Berlin</code>\n"
        "<code>/tz America/Vancouver</code>\n"
        "<code>/mytime</code>"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def handle_time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /time command (admin only)."""
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
            "Формат: `/time 10:00 America/Vancouver`",
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
    """Handle /poll command (admin only). /poll on or /poll off"""
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

    if not context.args:
        await update.message.reply_text("Формат: `/poll on` или `/poll off`", parse_mode="Markdown")
        return

    action = context.args[0].lower()
    settings = load_settings()

    if action == "on":
        settings["poll_enabled"] = True
        await update.message.reply_text("✅ Еженедельные опросы включены.")
    elif action == "off":
        settings["poll_enabled"] = False
        await update.message.reply_text("✅ Еженедельные опросы отключены.")
    else:
        await update.message.reply_text("❌ Неизвестный параметр. Используйте: `on` или `off`", parse_mode="Markdown")
        return

    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def generate_time_options(base_time_str: str) -> list[str]:
    """Generate 6 time options: base ± 2h to +3h."""
    hour, minute = map(int, base_time_str.split(":"))
    base = datetime.min.replace(hour=hour, minute=minute)

    offsets = [-2, -1, 0, 1, 2, 3]
    options = []
    for offset in offsets:
        dt = base + timedelta(hours=offset)
        options.append(dt.strftime("%H:%M"))

    return options


def format_time_in_tz(time_str: str, from_tz_name: str, to_tz_name: str) -> str:
    """Convert time_str (HH:MM) from from_tz to to_tz and return HH:MM."""
    try:
        from_tz = pytz.timezone(from_tz_name)
        to_tz = pytz.timezone(to_tz_name)

        hour, minute = map(int, time_str.split(":"))
        dt_from = from_tz.localize(datetime(2026, 5, 5, hour, minute))  # arbitrary date
        dt_to = dt_from.astimezone(to_tz)

        return dt_to.strftime("%H:%M")
    except Exception as e:
        logger.error(f"Time conversion error: {e}")
        return time_str


async def handle_proposal_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User confirmed the proposed time (button: ✅ Подходит)."""
    query = update.callback_query
    await query.answer()

    sessions = load_sessions()
    chat_id = str(query.message.chat_id)
    user_id = str(query.from_user.id)

    if chat_id not in sessions:
        await query.edit_message_text("❌ Сессия истекла. Попросите администратора отправить новый опрос.")
        return

    if query.message.chat.type == "private":
        # In private chat—user selected a time from options
        # Extract time from callback data: "time_HHMM"
        if query.data.startswith("time_"):
            selected_time = query.data[5:]  # "time_1000" -> "1000"
            selected_time = f"{selected_time[:2]}:{selected_time[2:]}"  # "1000" -> "10:00"
            sessions[chat_id]["event"]["current_time"] = selected_time
            sessions[chat_id]["event"]["proposal_author"] = user_id
            sessions[chat_id]["event"]["responses"] = {uid: "pending" for uid in sessions[chat_id]["members"].keys()}
            sessions[chat_id]["event"]["status"] = "proposed"
            sessions[chat_id]["event"]["deadline"] = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()

            save_sessions(sessions)

            # Private feedback
            await query.edit_message_text("✅ Принято 👍 Уведомил всех")

            # Notify group
            if chat_id in sessions:
                settings = load_settings()
                base_tz = settings["base_timezone"]

                # Convert selected time to group message context
                author_name = sessions[chat_id]["members"][user_id]["name"]
                settings = load_settings()
                group_text = (
                    f"{html.escape(author_name)} предлагает новое время:\n\n"
                    f"➡️ <b>{selected_time}</b>\n\n"
                    f"Подходит?"
                )
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Подходит", callback_data=f"group_yes_{chat_id}_{user_id}")],
                    [InlineKeyboardButton("❌ Не подходит", callback_data=f"group_no_{chat_id}_{user_id}")],
                    [InlineKeyboardButton("🔄 Предложить другое", callback_data="group_propose")],
                ])

                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=group_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                except Exception as e:
                    logger.error(f"Failed to notify group: {e}")
    else:
        # In group chat—user responds to proposal
        if query.data.startswith("group_yes"):
            sessions[chat_id]["event"]["responses"][user_id] = "yes"
            save_sessions(sessions)
            await query.answer("✅ Спасибо!")

        elif query.data.startswith("group_no"):
            sessions[chat_id]["event"]["responses"][user_id] = "no"
            save_sessions(sessions)
            await query.answer("❌ Записано.")

        elif query.data == "group_propose":
            # Trigger time proposal UI in private chat
            settings = load_settings()
            base_tz_name = settings["base_timezone"]
            user_tz = sessions[chat_id]["members"][user_id]["timezone"]

            if not user_tz:
                await query.answer("⚠️ Установите вашу временную зону: /таймзона", alert=True)
                return

            base_time = settings["call_time"]
            options = generate_time_options(base_time)

            # Convert to user timezone
            tz_options = []
            for opt in options:
                local_time = format_time_in_tz(opt, base_tz_name, user_tz)
                tz_options.append((opt, local_time))

            text = "Выберите время:\n\n"
            keyboard_buttons = []
            for base_opt, local_opt in tz_options:
                text += f"🕐 {local_opt}\n"
                button_label = f"🕐 {local_opt}"
                button_data = f"time_{base_opt.replace(':', '')}"
                keyboard_buttons.append([InlineKeyboardButton(button_label, callback_data=button_data)])

            keyboard = InlineKeyboardMarkup(keyboard_buttons)

            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=keyboard
                )
                await query.answer("Отправил вам варианты в личное сообщение.")
            except Exception as e:
                logger.error(f"Failed to send private message: {e}")
                await query.answer("❌ Ошибка. Попробуйте еще раз.", alert=True)


async def check_autoconfirm_job(app):
    """Scheduled job: Check for expired deadlines and auto-confirm if no rejections."""
    logger.info("Auto-confirm check triggered")

    sessions = load_sessions()

    for chat_id, session_data in sessions.items():
        event = session_data.get("event", {})

        if event.get("status") != "proposed" or not event.get("deadline"):
            continue

        deadline = datetime.fromisoformat(event["deadline"])
        now = datetime.now(timezone.utc)

        if now < deadline:
            continue

        responses = event.get("responses", {})
        has_rejection = any(r == "no" for r in responses.values())

        if has_rejection:
            logger.info(f"Chat {chat_id}: Proposal rejected (has 'no' vote)")
            event["status"] = "idle"
            continue

        # Auto-confirm
        event["status"] = "confirmed"
        confirmed_time = event.get("current_time", "10:00")
        author_id = event.get("proposal_author")

        confirmed_users = [uid for uid, resp in responses.items() if resp == "yes"]
        pending_users = [uid for uid, resp in responses.items() if resp == "pending"]

        confirmed_names = [
            session_data["members"][uid]["name"]
            for uid in confirmed_users
            if uid in session_data["members"]
        ]
        pending_names = [
            session_data["members"][uid]["name"]
            for uid in pending_users
            if uid in session_data["members"]
        ]

        confirmed_str = ", ".join(confirmed_names) if confirmed_names else "—"
        pending_str = ", ".join(pending_names) if pending_names else "—"

        text = (
            f"✅ Время подтверждено автоматически:\n\n"
            f"➡️ <b>{confirmed_time}</b>\n\n"
            f"<b>Подтвердили:</b>\n{confirmed_str}\n\n"
            f"<b>Ожидаем:</b>\n{pending_str}"
        )

        try:
            await app.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML"
            )
            logger.info(f"Chat {chat_id}: Auto-confirmed at {confirmed_time}")
        except Exception as e:
            logger.error(f"Failed to send auto-confirm message to {chat_id}: {e}")

    save_sessions(sessions)


async def friday_invite_job(app):
    """Scheduled job: Send Friday invite to all active chat groups."""
    logger.info("Friday invite job triggered")

    sessions = load_sessions()
    settings = load_settings()

    if not settings.get("poll_enabled", True):
        logger.info("Polls disabled. Skipping Friday invite.")
        return

    base_time = settings["call_time"]

    for chat_id, session_data in sessions.items():
        try:
            # Reset event state
            session_data["event"] = {
                "status": "idle",
                "proposal_id": None,
                "current_time": base_time,
                "proposal_author": None,
                "deadline": None,
                "responses": {uid: "pending" for uid in session_data["members"].keys()}
            }

            text = (
                f"Созвон в воскресенье:\n\n"
                f"Базовое время: <b>{base_time}</b>\n\n"
                f"Подходит?"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Подходит", callback_data="fri_yes")],
                [InlineKeyboardButton("🔄 Предложить другое", callback_data="fri_propose")],
                [InlineKeyboardButton("❌ Не смогу", callback_data="fri_no")],
            ])

            await app.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            logger.info(f"Friday invite sent to chat {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send Friday invite to {chat_id}: {e}")

    save_sessions(sessions)


async def handle_debug_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command: Manually trigger Friday invite (testing only)."""
    sessions = load_sessions()
    chat_id = str(update.message.chat_id)
    user_id = str(update.message.from_user.id)

    if chat_id not in sessions or user_id not in sessions[chat_id]["members"]:
        await update.message.reply_text("❌ Сначала установите вашу временную зону: `/таймзона`", parse_mode="Markdown")
        return

    is_admin = sessions[chat_id]["members"][user_id].get("is_admin", False)
    if not is_admin:
        await update.message.reply_text("❌ Только администратор может это делать.")
        return

    await update.message.reply_text("⏳ Отправляю приглашение на созвон...")

    # Manually trigger Friday invite job
    await friday_invite_job(context.application)
    await update.message.reply_text("✅ Приглашение отправлено!")


async def handle_friday_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Friday invite button responses."""
    query = update.callback_query
    await query.answer()

    sessions = load_sessions()
    chat_id = str(query.message.chat_id)
    user_id = str(query.from_user.id)

    if query.data == "fri_yes":
        if chat_id in sessions:
            sessions[chat_id]["event"]["responses"][user_id] = "yes"
        save_sessions(sessions)
        await query.answer("✅ Спасибо!")

    elif query.data == "fri_no":
        if chat_id in sessions:
            sessions[chat_id]["event"]["responses"][user_id] = "no"
        save_sessions(sessions)
        await query.answer("❌ Записано.")

    elif query.data == "fri_propose":
        # Send time options in private chat
        if chat_id not in sessions or user_id not in sessions[chat_id]["members"]:
            await query.answer("⚠️ Установите вашу временную зону: /таймзона", alert=True)
            return

        user_tz = sessions[chat_id]["members"][user_id]["timezone"]
        if not user_tz:
            await query.answer("⚠️ Установите вашу временную зону: /таймзона", alert=True)
            return

        settings = load_settings()
        base_time = settings["call_time"]
        base_tz_name = settings["base_timezone"]

        options = generate_time_options(base_time)
        tz_options = []
        for opt in options:
            local_time = format_time_in_tz(opt, base_tz_name, user_tz)
            tz_options.append((opt, local_time))

        text = "Выберите время:\n\n"
        keyboard_buttons = []
        for base_opt, local_opt in tz_options:
            text += f"🕐 {local_opt}\n"
            button_label = f"🕐 {local_opt}"
            button_data = f"time_{base_opt.replace(':', '')}"
            keyboard_buttons.append([InlineKeyboardButton(button_label, callback_data=button_data)])

        keyboard = InlineKeyboardMarkup(keyboard_buttons)

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=keyboard
            )
            await query.answer("Отправил вам варианты в личное сообщение.")
        except Exception as e:
            logger.error(f"Failed to send private message: {e}")
            await query.answer("❌ Ошибка. Попробуйте еще раз.", alert=True)


async def set_bot_commands(app):
    """Set bot commands for the UI."""
    commands = [
        BotCommand("tz", "Установить временную зону (Telegram limitation: ASCII only)"),
        BotCommand("mytime", "Показать ваше время"),
        BotCommand("help", "Список команд"),
        BotCommand("time", "Обновить время созвона (администратор)"),
        BotCommand("poll", "Включить/отключить опросы"),
        BotCommand("debug_invite", "Отправить опрос вручную (администратор, тестирование)"),
    ]
    await app.bot.set_my_commands(commands)


async def post_init(app):
    """Called after bot starts."""
    await set_bot_commands(app)

    # Set up scheduler
    scheduler = AsyncIOScheduler()
    scheduler.start()

    # Schedule Friday invite at 12:00 (every Friday)
    scheduler.add_job(
        friday_invite_job,
        "cron",
        day_of_week=4,  # Friday (0=Mon, 4=Fri)
        hour=12,
        minute=0,
        args=[app],
        id="friday_invite",
        replace_existing=True
    )

    # Schedule auto-confirm check every minute
    scheduler.add_job(
        check_autoconfirm_job,
        "interval",
        minutes=1,
        args=[app],
        id="autoconfirm_check",
        replace_existing=True
    )

    logger.info("Scheduler initialized with Friday invite + auto-confirm jobs")
    app.scheduler = scheduler


def main():
    load_dotenv(dotenv_path=".env.local")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in .env.local")

    app = ApplicationBuilder().token(token).build()

    # Command handlers (ASCII names only—Telegram limitation)
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("tz", handle_timezone))  # /tz (was /таймзона)
    app.add_handler(CommandHandler("mytime", handle_mytime))  # /mytime (was /моевремя)
    app.add_handler(CommandHandler("help", handle_help))  # /help (was /помощь)
    app.add_handler(CommandHandler("time", handle_time_command))  # /time (was /время)
    app.add_handler(CommandHandler("poll", handle_poll_on))  # /poll (was /опрос)
    app.add_handler(CommandHandler("debug_invite", handle_debug_invite))  # /debug_invite (was /отправить_опрос)

    # Callback handlers
    app.add_handler(CallbackQueryHandler(handle_friday_response, pattern="^fri_"))
    app.add_handler(CallbackQueryHandler(handle_proposal_yes, pattern="^time_"))
    app.add_handler(CallbackQueryHandler(handle_proposal_yes, pattern="^group_"))

    # Post-init hook
    app.post_init = post_init

    logger.info("Starting bot...")
    app.run_polling(allowed_updates=[
        "message",
        "callback_query",
        "my_chat_member",
    ])


if __name__ == "__main__":
    main()
