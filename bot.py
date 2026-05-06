import asyncio
import html
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

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
            "⚠️ Формат: `/tz America/Vancouver` или `/tz Europe/Berlin`\n"
            "Примеры: `Vancouver`, `Berlin`, `Tokyo`, `New_York`",
            parse_mode="Markdown"
        )
        return

    tz_input = " ".join(context.args)
    resolved_tz, error_msg = resolve_timezone(tz_input)

    if error_msg:
        await update.message.reply_text(error_msg, parse_mode="Markdown")
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

    sessions[chat_id]["members"][user_id]["timezone"] = resolved_tz
    save_sessions(sessions)

    await update.message.reply_text(f"✅ Сохранено: {resolved_tz}")


async def handle_mytime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mytime command."""
    sessions = load_sessions()
    chat_id = str(update.message.chat_id)
    user_id = str(update.message.from_user.id)

    if chat_id not in sessions or user_id not in sessions[chat_id]["members"]:
        await update.message.reply_text("⚠️ Пожалуйста, установите вашу временную зону: `/tz America/Vancouver`", parse_mode="Markdown")
        return

    user_tz_name = sessions[chat_id]["members"][user_id]["timezone"]
    if not user_tz_name:
        await update.message.reply_text("⚠️ Пожалуйста, установите вашу временную зону: `/tz America/Vancouver`", parse_mode="Markdown")
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
    sessions = load_sessions()
    chat_id = str(update.message.chat_id)
    user_id = str(update.message.from_user.id)

    is_admin = False
    if chat_id in sessions and user_id in sessions[chat_id]["members"]:
        is_admin = sessions[chat_id]["members"][user_id].get("is_admin", False)

    text = (
        "<b>Команды</b>\n\n"
        "<b>Пользователь:</b>\n"
        "<code>/tz Europe/Berlin</code> — установить вашу временную зону\n"
        "<code>/mytime</code> — показать ваше текущее время\n"
        "<code>/help</code> — этот список\n\n"
    )

    if is_admin:
        text += (
            "<b>Администратор:</b>\n"
            "<code>/time 10:00 America/Vancouver</code> — обновить время созвона\n"
            "<code>/poll on</code> — включить еженедельные опросы\n"
            "<code>/poll off</code> — отключить еженедельные опросы\n"
            "<code>/test_mode on</code> — включить тестовый режим (10 мин цикл)\n"
            "<code>/test_mode off</code> — отключить тестовый режим\n"
            "<code>/debug_invite</code> — отправить опрос вручную (тестирование)\n"
        )

    text += (
        "\n<b>Примеры:</b>\n"
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


def resolve_timezone(tz_input: str) -> Tuple[Optional[str], str]:
    """
    Fuzzy-match timezone input. Returns (resolved_tz_name, error_msg).
    If error_msg is not empty, resolved_tz_name is None.
    """
    # Try exact match first
    try:
        pytz.timezone(tz_input)
        return tz_input, ""
    except pytz.UnknownTimeZoneError:
        pass

    # Try common prefix matches (e.g., "Vancouver" → "America/Vancouver")
    all_tzs = pytz.all_timezones
    matches = [tz for tz in all_tzs if tz_input.lower() in tz.lower()]

    if len(matches) == 1:
        return matches[0], ""
    elif len(matches) > 1:
        # Multiple matches—suggest the most common ones
        top_matches = matches[:5]
        suggestions = "\n".join(f"  • {tz}" for tz in top_matches)
        return None, f"❌ Неоднозначно. Уточните:\n{suggestions}"
    else:
        return None, f"❌ Неизвестная временная зона: `{tz_input}`. Примеры: `America/Vancouver`, `Europe/Berlin`, `Asia/Tokyo`"


def generate_time_options(base_time_str: str) -> List[str]:
    """Generate 6 time options: base - 1h to + 4h."""
    hour, minute = map(int, base_time_str.split(":"))
    base = datetime.min.replace(hour=hour, minute=minute)

    offsets = [-1, 0, 1, 2, 3, 4]
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


async def handle_private_change_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User clicked 'change choice' in private chat—show time options again."""
    query = update.callback_query
    await query.answer()

    sessions = load_sessions()
    chat_id = str(query.message.chat_id)
    user_id = str(query.from_user.id)

    if chat_id not in sessions or user_id not in sessions[chat_id]["members"]:
        await query.edit_message_text("❌ Сессия истекла. Попросите администратора отправить новый опрос.")
        return

    user_tz = sessions[chat_id]["members"][user_id]["timezone"]
    if not user_tz:
        await query.answer("⚠️ Установите вашу временную зону: /tz", alert=True)
        return

    settings = load_settings()
    base_time = settings["call_time"]
    base_tz_name = settings["base_timezone"]

    # Get the current selected time to show in the message
    current_time = sessions[chat_id]["event"].get("current_time", base_time)
    current_local_time = format_time_in_tz(current_time, base_tz_name, user_tz)

    options = generate_time_options(base_time)
    tz_options = []
    for opt in options:
        local_time = format_time_in_tz(opt, base_tz_name, user_tz)
        tz_options.append((opt, local_time))

    text = (
        f"<b>✅ Текущее время:</b> {current_local_time} {user_tz}\n"
        f"<i>({current_time} {base_tz_name})</i>\n\n"
        f"<b>Выберите другое:</b>\n\n"
        f"<i>Базовое:</i> <code>{base_time} {base_tz_name}</code>\n"
        f"<i>Ваша зона:</i> <code>{user_tz}</code>\n\n"
    )
    keyboard_buttons = []
    for base_opt, local_opt in tz_options:
        button_label = f"🕐 {local_opt}"
        button_data = f"time_{base_opt.replace(':', '')}"
        keyboard_buttons.append([InlineKeyboardButton(button_label, callback_data=button_data)])

    keyboard = InlineKeyboardMarkup(keyboard_buttons)

    try:
        await query.edit_message_text(
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Failed to edit message: {e}")
        await query.answer("❌ Ошибка. Попробуйте еще раз.", alert=True)


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
        # Extract time and group chat_id from callback data: "time_HHMM_CHATID"
        if query.data.startswith("time_"):
            parts = query.data.split("_")
            if len(parts) >= 3:
                # time_HHMM_CHATID format
                time_str = parts[1]  # "1000"
                group_chat_id = "_".join(parts[2:])  # handle chat_ids with underscores (e.g., negative numbers)
            else:
                # fallback to old format (shouldn't happen after deploy)
                time_str = query.data[5:]
                group_chat_id = chat_id

            selected_time = f"{time_str[:2]}:{time_str[2:]}"  # "1000" -> "10:00"
            chat_id = group_chat_id  # Use the group chat ID

            if chat_id not in sessions:
                await query.edit_message_text("❌ Сессия истекла. Попросите администратора отправить новый опрос.")
                return

            sessions[chat_id]["event"]["current_time"] = selected_time
            sessions[chat_id]["event"]["proposal_author"] = user_id
            # Auto-vote "yes" for the proposer; others are pending
            sessions[chat_id]["event"]["responses"] = {uid: ("yes" if uid == user_id else "pending") for uid in sessions[chat_id]["members"].keys()}
            sessions[chat_id]["event"]["status"] = "proposed"
            # In test mode, use 1 minute; otherwise 12 hours
            deadline_delta = timedelta(minutes=1) if load_settings().get("test_mode") else timedelta(hours=12)
            sessions[chat_id]["event"]["deadline"] = (datetime.now(timezone.utc) + deadline_delta).isoformat()

            save_sessions(sessions)

            # Private feedback with change button
            settings = load_settings()
            base_tz = settings["base_timezone"]
            user_tz = sessions[chat_id]["members"][user_id]["timezone"]

            # Convert base time to user's local time for display
            local_time = format_time_in_tz(selected_time, base_tz, user_tz)

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Изменить время", callback_data="private_change_time")]
            ])
            await query.edit_message_text(
                text=(
                    f"✅ Принято 👍\n\n"
                    f"➡️ <b>{local_time}</b> {user_tz}\n"
                    f"<i>({selected_time} {base_tz})</i>\n\n"
                    f"Уведомил всех"
                ),
                parse_mode="HTML",
                reply_markup=keyboard
            )

            # Notify group
            if chat_id in sessions:
                settings = load_settings()
                base_tz = settings["base_timezone"]

                # Convert selected time to group message context
                author_name = sessions[chat_id]["members"][user_id]["name"]
                proposer_tz = sessions[chat_id]["members"][user_id]["timezone"]
                settings = load_settings()
                base_tz = settings["base_timezone"]

                # Show both proposer's local time and base time
                proposer_local = format_time_in_tz(selected_time, base_tz, proposer_tz)
                group_text = (
                    f"{html.escape(author_name)} предлагает новое время:\n\n"
                    f"➡️ <code>{proposer_local} {proposer_tz}</code>\n"
                    f"<i>({selected_time} {base_tz})</i>\n\n"
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

            # Edit message to remove buttons and confirm vote
            original_text = query.message.text
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Изменить выбор", callback_data="group_change")]
            ])
            await query.edit_message_text(
                text=f"{original_text}\n\n✅ <b>Ваш голос: Подходит</b>",
                parse_mode="HTML",
                reply_markup=keyboard
            )

        elif query.data.startswith("group_no"):
            sessions[chat_id]["event"]["responses"][user_id] = "no"
            save_sessions(sessions)
            await query.answer("❌ Записано.")

            # Edit message to remove buttons and confirm vote
            original_text = query.message.text
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Изменить выбор", callback_data="group_change")]
            ])
            await query.edit_message_text(
                text=f"{original_text}\n\n❌ <b>Ваш голос: Не подходит</b>",
                parse_mode="HTML",
                reply_markup=keyboard
            )

        elif query.data == "group_change":
            # Show original 3 buttons again to change vote
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Подходит", callback_data=f"group_yes_{chat_id}_{user_id}")],
                [InlineKeyboardButton("❌ Не подходит", callback_data=f"group_no_{chat_id}_{user_id}")],
                [InlineKeyboardButton("🔄 Предложить другое", callback_data="group_propose")],
            ])
            await query.edit_message_text(
                text=query.message.text.split("\n\n✅")[0].split("\n\n❌")[0],  # Remove vote confirmation
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await query.answer("Выберите новый вариант")

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

            # Show current base time and its conversion to user's timezone
            current_local = format_time_in_tz(base_time, base_tz_name, user_tz)
            text = (
                f"<b>Текущее время:</b>\n"
                f"Базовое: <code>{base_time} {base_tz_name}</code>\n"
                f"Ваше: <code>{current_local} {user_tz}</code>\n\n"
                f"<b>Выберите другое:</b>\n\n"
            )
            keyboard_buttons = []
            for base_opt, local_opt in tz_options:
                button_label = f"🕐 {local_opt}"
                button_data = f"time_{base_opt.replace(':', '')}_{chat_id}"
                keyboard_buttons.append([InlineKeyboardButton(button_label, callback_data=button_data)])

            keyboard = InlineKeyboardMarkup(keyboard_buttons)

            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode="HTML",
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
    settings = load_settings()
    base_tz = settings["base_timezone"]

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

        # Auto-confirm (silently, without sending group message; will include vote info in Sunday reminder)
        event["status"] = "confirmed"
        confirmed_time = event.get("current_time", "10:00")
        logger.info(f"Chat {chat_id}: Auto-confirmed at {confirmed_time}")

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
    base_tz = settings["base_timezone"]

    for chat_id, session_data in sessions.items():
        # Skip private chats—only send to groups
        if int(chat_id) > 0:  # Positive chat_id = private/user chat; negative = group
            logger.info(f"Skipping private chat {chat_id}")
            continue

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
                f"<b>Базовое время:</b> <code>{base_time} {base_tz}</code>\n\n"
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


async def handle_test_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /test_mode command (admin only). /test_mode on or /test_mode off"""
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
        await update.message.reply_text("Формат: `/test_mode on` или `/test_mode off`", parse_mode="Markdown")
        return

    action = context.args[0].lower()
    settings = load_settings()

    if action == "on":
        settings["test_mode"] = True
        await update.message.reply_text(
            "🧪 Тестовый режим включен!\n\n"
            "• Опрос будет отправляться каждые 10 минут\n"
            "• Автоподтверждение: 1 минута\n"
            "• Напоминание: 5 секунд перед созвоном"
        )
    elif action == "off":
        settings["test_mode"] = False
        await update.message.reply_text("✅ Тестовый режим отключен. Обычный режим восстановлен.")
    else:
        await update.message.reply_text("❌ Неизвестный параметр. Используйте: `on` или `off`", parse_mode="Markdown")
        return

    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

    # Restart scheduler with new settings
    if hasattr(context.application, "scheduler"):
        scheduler = context.application.scheduler
        scheduler.remove_job("friday_invite")

        if settings.get("test_mode"):
            scheduler.add_job(
                friday_invite_job,
                "interval",
                minutes=10,
                args=[context.application],
                id="friday_invite",
                replace_existing=True
            )
            logger.info("Test mode: Friday job now runs every 10 minutes")
        else:
            scheduler.add_job(
                friday_invite_job,
                "cron",
                day_of_week=4,
                hour=12,
                minute=0,
                args=[context.application],
                id="friday_invite",
                replace_existing=True
            )
            logger.info("Normal mode: Friday job restored to Friday 12:00")


async def handle_debug_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command: Manually trigger Friday invite (testing only)."""
    sessions = load_sessions()
    chat_id = str(update.message.chat_id)
    user_id = str(update.message.from_user.id)

    if chat_id not in sessions or user_id not in sessions[chat_id]["members"]:
        await update.message.reply_text("❌ Сначала установите вашу временную зону: `/tz America/Vancouver`", parse_mode="Markdown")
        return

    is_admin = sessions[chat_id]["members"][user_id].get("is_admin", False)
    if not is_admin:
        await update.message.reply_text("❌ Только администратор может это делать. (первый пользователь в группе автоматически администратор)")
        return

    # Silently trigger Friday invite job—just send the invite, no extra messages
    await friday_invite_job(context.application)


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

        # Edit message to remove buttons and confirm vote
        original_text = query.message.text
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Изменить выбор", callback_data="fri_change")]
        ])
        await query.edit_message_text(
            text=f"{original_text}\n\n✅ <b>Ваш голос: Подходит</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )

    elif query.data == "fri_no":
        if chat_id in sessions:
            sessions[chat_id]["event"]["responses"][user_id] = "no"
        save_sessions(sessions)
        await query.answer("❌ Записано.")

        # Edit message to remove buttons and confirm vote
        original_text = query.message.text
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Изменить выбор", callback_data="fri_change")]
        ])
        await query.edit_message_text(
            text=f"{original_text}\n\n❌ <b>Ваш голос: Не смогу</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )

    elif query.data == "fri_change":
        # Show original 3 buttons again to change vote
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Подходит", callback_data="fri_yes")],
            [InlineKeyboardButton("🔄 Предложить другое", callback_data="fri_propose")],
            [InlineKeyboardButton("❌ Не смогу", callback_data="fri_no")],
        ])
        await query.edit_message_text(
            text=query.message.text.split("\n\n✅")[0].split("\n\n❌")[0],  # Remove vote confirmation
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await query.answer("Выберите новый вариант")

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

        # Show current base time and its conversion to user's timezone
        current_local = format_time_in_tz(base_time, base_tz_name, user_tz)
        text = (
            f"<b>Текущее время:</b>\n"
            f"Base: <code>{base_time} {base_tz_name}</code>\n"
            f"Your: <code>{current_local} {user_tz}</code>\n\n"
            f"<b>Выберите другое:</b>\n\n"
        )
        keyboard_buttons = []
        for base_opt, local_opt in tz_options:
            button_label = f"🕐 {local_opt}"
            button_data = f"time_{base_opt.replace(':', '')}_{chat_id}"
            keyboard_buttons.append([InlineKeyboardButton(button_label, callback_data=button_data)])

        keyboard = InlineKeyboardMarkup(keyboard_buttons)

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="HTML",
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

    settings = load_settings()
    test_mode = settings.get("test_mode", False)

    # Schedule Friday invite
    if test_mode:
        # Test mode: every 10 minutes
        scheduler.add_job(
            friday_invite_job,
            "interval",
            minutes=10,
            args=[app],
            id="friday_invite",
            replace_existing=True
        )
        logger.info("TEST MODE: Friday job runs every 10 minutes")
    else:
        # Normal mode: Friday at 12:00
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
        logger.info("Normal mode: Friday job scheduled for Friday 12:00")

    # Schedule auto-confirm check every minute (or 5 seconds in test mode)
    check_interval = 5 if test_mode else 60
    scheduler.add_job(
        check_autoconfirm_job,
        "interval",
        seconds=check_interval,
        args=[app],
        id="autoconfirm_check",
        replace_existing=True
    )

    logger.info(f"Scheduler initialized. Test mode: {test_mode}")
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
    app.add_handler(CommandHandler("test_mode", handle_test_mode))  # /test_mode on/off
    app.add_handler(CommandHandler("debug_invite", handle_debug_invite))  # /debug_invite (was /отправить_опрос)

    # Callback handlers
    app.add_handler(CallbackQueryHandler(handle_private_change_time, pattern="^private_change_time$"))
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
