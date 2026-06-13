import html
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from telegram import BotCommand, ChatMember, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    ChatMemberHandler,
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
USER_TIMEZONES_FILE = Path("user_timezones.json")
PENDING_PROPOSALS_FILE = Path("pending_proposals.json")
DEFAULT_TIMEZONE = "Europe/Minsk"


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


def load_user_timezones() -> dict:
    """Load global user timezone cache (user_id -> timezone)."""
    if USER_TIMEZONES_FILE.exists():
        with open(USER_TIMEZONES_FILE) as f:
            return json.load(f)
    return {}


def save_user_timezones(user_tzs: dict):
    """Save global user timezone cache."""
    with open(USER_TIMEZONES_FILE, "w") as f:
        json.dump(user_tzs, f, indent=2, default=str)


def load_pending_proposals() -> dict:
    """user_id → group_chat_id: tracks who is mid-proposal."""
    if PENDING_PROPOSALS_FILE.exists():
        with open(PENDING_PROPOSALS_FILE) as f:
            return json.load(f)
    return {}


def save_pending_proposals(pending: dict):
    with open(PENDING_PROPOSALS_FILE, "w") as f:
        json.dump(pending, f, indent=2)


def parse_time_input(text: str) -> Optional[str]:
    """
    Parse flexible time strings typed by users → HH:MM or None.
    Accepts: 7:20  7.20  7 20  720  19:30  07:20  9
    """
    text = text.strip()
    # HH:MM, HH.MM, HH MM
    m = re.match(r'^(\d{1,2})[:\. ](\d{2})$', text)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}"
    # HHMM (e.g. 720 → 07:20, 1930 → 19:30)
    m = re.match(r'^(\d{3,4})$', text)
    if m:
        raw = m.group(1).zfill(4)
        h, mn = int(raw[:2]), int(raw[2:])
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}"
    # Plain hour (e.g. "9" → 09:00)
    m = re.match(r'^(\d{1,2})$', text)
    if m:
        h = int(m.group(1))
        if 0 <= h <= 23:
            return f"{h:02d}:00"
    return None


def get_user_timezone(user_id: str) -> Optional[str]:
    """Get user's timezone from global cache or None."""
    user_tzs = load_user_timezones()
    return user_tzs.get(str(user_id))


def ensure_member(chat_id: str, user_id: str, name: str, sessions: dict) -> str:
    """
    Ensure user exists in session with a valid timezone. Returns their timezone.
    Priority: global cache (set via /tz in private chat) → existing record → DEFAULT_TIMEZONE.
    """
    if chat_id not in sessions:
        sessions[chat_id] = {
            "members": {},
            "event": {"status": "idle"},
            "last_active": datetime.now(timezone.utc).isoformat()
        }

    global_tz = get_user_timezone(user_id)
    
    if user_id not in sessions[chat_id]["members"]:
        tz = global_tz or DEFAULT_TIMEZONE
        sessions[chat_id]["members"][user_id] = {
            "name": name,
            "timezone": tz,
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "is_admin": len(sessions[chat_id]["members"]) == 0
        }
    else:
        # If member exists but their timezone is default or missing, try updating from global cache
        member = sessions[chat_id]["members"][user_id]
        if global_tz and (not member.get("timezone") or member.get("timezone") == DEFAULT_TIMEZONE):
            member["timezone"] = global_tz

    return sessions[chat_id]["members"][user_id]["timezone"]


async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Auto-register group when bot is added."""
    my_chat_member = update.my_chat_member
    if not my_chat_member:
        return

    chat = my_chat_member.chat
    # Only handle groups / supergroups, not channels
    if chat.type not in ("group", "supergroup"):
        return

    new_status = my_chat_member.new_chat_member.status

    # Bot was added to the group (member or admin)
    if new_status in (ChatMember.MEMBER, ChatMember.ADMINISTRATOR):
        chat_id = str(chat.id)
        adder = my_chat_member.from_user
        adder_id = str(adder.id)

        sessions = load_sessions()

        if chat_id not in sessions:
            sessions[chat_id] = {
                "members": {},
                "event": {"status": "idle"},
                "last_active": datetime.now(timezone.utc).isoformat(),
            }

        # Register the user who added the bot as admin if not yet registered
        if adder_id not in sessions[chat_id]["members"]:
            tz = get_user_timezone(adder_id) or DEFAULT_TIMEZONE
            sessions[chat_id]["members"][adder_id] = {
                "name": adder.first_name or "User",
                "timezone": tz,
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "is_admin": True,
            }
            save_sessions(sessions)
            logger.info(
                f"Bot added to chat {chat_id} ({chat.title or chat_id}) "
                f"by {adder_id} ({adder.first_name}) — session auto-created"
            )


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start in private chat."""
    user = update.message.from_user
    chat_id = update.message.chat_id

    text = (
        "👋 Привет! Я помогу координировать еженедельный созвон.\n\n"
        "По умолчанию ваша временная зона: <code>Europe/Minsk</code>\n"
        "Чтобы изменить: <code>/tz Europe/Berlin</code>\n\n"
        "Для справки: /help"
    )
    await update.message.reply_text(text, parse_mode="HTML")


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
            "timezone": DEFAULT_TIMEZONE,
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "is_admin": len(sessions[chat_id]["members"]) == 0
        }

    # Sync this new timezone across all group sessions where the user is a member
    for s_chat_id, session_data in sessions.items():
        if user_id in session_data.get("members", {}):
            session_data["members"][user_id]["timezone"] = resolved_tz

    save_sessions(sessions)

    user_tzs = load_user_timezones()
    user_tzs[user_id] = resolved_tz
    save_user_timezones(user_tzs)

    await update.message.reply_text(f"✅ Сохранено: {resolved_tz}")


async def handle_mytime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mytime command."""
    user_id = str(update.message.from_user.id)

    user_tz_name = get_user_timezone(user_id)
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
            "<code>/trigger [HH:MM]</code> — запустить цикл созвона сейчас\n"
            "<code>/time 10:00 America/Vancouver</code> — обновить время созвона\n"
            "<code>/poll on</code> — включить еженедельные опросы\n"
            "<code>/poll off</code> — отключить еженедельные опросы\n"
        )

    text += (
        "\n<b>Примеры:</b>\n"
        "<code>/tz Europe/Berlin</code>\n"
        "<code>/tz America/Vancouver</code>\n"
        "<code>/mytime</code>"
    )

    await update.message.reply_text(text, parse_mode="HTML")


async def reschedule_jobs(app):
    """Update all scheduled jobs based on current settings."""
    if not hasattr(app, "scheduler"):
        return

    scheduler = app.scheduler
    settings = load_settings()

    # 1. Friday/Saturday Invite
    try:
        scheduler.remove_job("friday_invite")
    except:
        pass
    poll_day_str = settings.get("poll_day", "Friday")
    poll_time_str = settings.get("poll_time", "12:00")
    base_tz_name = settings.get("base_timezone", "Europe/Minsk")
    base_tz = pytz.timezone(base_tz_name)
    days = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
    day_of_week = days.get(poll_day_str.lower(), 4)
    hour, minute = map(int, poll_time_str.split(":"))
    scheduler.add_job(friday_invite_job, "cron", day_of_week=day_of_week, hour=hour, minute=minute, timezone=base_tz, args=[app], id="friday_invite", replace_existing=True)

    # 2. Reminder Check (every 5 minutes)
    try:
        scheduler.remove_job("reminder_check")
    except:
        pass
    scheduler.add_job(reminder_check_job, "interval", minutes=5, args=[app], id="reminder_check", replace_existing=True)

    # 3. Auto-confirm Check
    try:
        scheduler.remove_job("autoconfirm_check")
    except:
        pass
    scheduler.add_job(check_autoconfirm_job, "interval", seconds=60, args=[app], id="autoconfirm_check", replace_existing=True)

    logger.info("Scheduler updated with new settings")


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

    await reschedule_jobs(context.application)
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
    
    await reschedule_jobs(context.application)


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


def format_all_member_times(time_str: str, base_tz_name: str, members: dict, user_id_to_refresh: str = None) -> str:
    """Return a block showing time_str in each member's local timezone."""
    seen: dict = {}
    lines = []
    
    # Load global cache to verify/update timezones on the fly
    user_tzs = load_user_timezones()
    
    for uid, member in members.items():
        # Always prefer the timezone set via /tz (global cache) over the session record
        global_tz = user_tzs.get(str(uid))
        current_tz = member.get("timezone")

        if global_tz and global_tz != current_tz:
            member["timezone"] = global_tz
            current_tz = global_tz

        tz_name = current_tz or DEFAULT_TIMEZONE
        name = html.escape(member.get("name", "User"))
        if tz_name not in seen:
            seen[tz_name] = format_time_in_tz(time_str, base_tz_name, tz_name)
        lines.append(f"• {name}: {seen[tz_name]} ({tz_name})")
    return "\n".join(lines)


async def handle_private_change_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User clicked 'change choice' in private chat—show time options again."""
    query = update.callback_query
    await query.answer()

    sessions = load_sessions()
    user_id = str(query.from_user.id)

    # Callback data: "private_change_time_{group_chat_id}"
    parts = query.data.split("_", 3)
    group_chat_id = parts[3] if len(parts) > 3 else None

    if not group_chat_id or group_chat_id not in sessions or user_id not in sessions[group_chat_id]["members"]:
        await query.edit_message_text("❌ Сессия истекла. Попросите администратора отправить новый опрос.")
        return

    user_tz = sessions[group_chat_id]["members"][user_id]["timezone"] or DEFAULT_TIMEZONE

    settings = load_settings()
    base_time = settings["call_time"]
    base_tz_name = settings["base_timezone"]

    current_time = sessions[group_chat_id]["event"].get("current_time", base_time)
    current_local_time = format_time_in_tz(current_time, base_tz_name, user_tz)

    options = generate_time_options(base_time)
    tz_options = []
    for opt in options:
        local_time = format_time_in_tz(opt, base_tz_name, user_tz)
        tz_options.append((opt, local_time))

    text = (
        f"<b>Текущее время:</b> {current_local_time} ({user_tz})\n\n"
        f"<b>Выберите время или напишите своё</b> (в вашем часовом поясе):\n"
        f"<i>Примеры: 7:20 · 7.20 · 7 20 · 19:30</i>\n\n"
    )
    keyboard_buttons = []
    for base_opt, local_opt in tz_options:
        button_label = f"🕐 {local_opt}"
        button_data = f"time_{base_opt.replace(':', '')}_{group_chat_id}"
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
            responses = {uid: ("yes" if uid == user_id else "pending") for uid in sessions[chat_id]["members"].keys()}
            sessions[chat_id]["event"]["responses"] = responses
            
            # Check for immediate confirmation (e.g. if it's a 1-person group during testing)
            all_yes = all(r == "yes" for r in responses.values())
            if all_yes:
                sessions[chat_id]["event"]["status"] = "confirmed"
                status_text = "Принято (все подтвердили)"
            else:
                sessions[chat_id]["event"]["status"] = "proposed"
                status_text = "Ожидаем голоса"
        
        auto_confirm_hours = load_settings().get("auto_confirm_hours", 12)
        deadline_delta = timedelta(hours=auto_confirm_hours)
        sessions[chat_id]["event"]["deadline"] = (datetime.now(timezone.utc) + deadline_delta).isoformat()

        save_sessions(sessions)

        # Private feedback with change button
        settings = load_settings()
        base_tz = settings["base_timezone"]
        user_tz = sessions[chat_id]["members"][user_id]["timezone"]

        # Convert base time to user's local time for display
        local_time = format_time_in_tz(selected_time, base_tz, user_tz)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Изменить время", callback_data=f"private_change_time_{chat_id}")]
        ])
        await query.edit_message_text(
            text=(
                f"✅ Принято 👍\n\n"
                f"➡️ <b>{local_time}</b> ({user_tz})\n\n"
                f"{status_text}"
            ),
            parse_mode="HTML",
            reply_markup=keyboard
        )

# Notify group
        if chat_id in sessions:
            # Convert selected time to group message context
                author_name = sessions[chat_id]["members"][user_id]["name"]
                proposer_tz = sessions[chat_id]["members"][user_id]["timezone"]
                
                # Show both proposer's local time and base time
                proposer_local = format_time_in_tz(selected_time, base_tz, proposer_tz)
                
                tz_block = format_all_member_times(selected_time, base_tz, sessions[chat_id]["members"])
                if sessions[chat_id]["event"]["status"] == "confirmed":
                    group_text = (
                        f"✅ {html.escape(author_name)} установил новое время:\n\n"
                        f"{tz_block}"
                    )
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Изменить", callback_data="group_propose")]
                    ])
                else:
                    group_text = (
                        f"{html.escape(author_name)} предлагает новое время:\n\n"
                        f"{tz_block}\n\n"
                        f"Подходит?"
                    )
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Подходит", callback_data=f"group_yes_{chat_id}_{user_id}")],
                        [InlineKeyboardButton("❌ Не подходит", callback_data=f"group_no_{chat_id}_{user_id}")],
                        [InlineKeyboardButton("🔄 Предложить другое", callback_data="group_propose")],
                    ])

                try:
                    # Cleanup previous poll if it exists
                    if sessions[chat_id]["event"].get("last_poll_id"):
                        try:
                            await context.bot.delete_message(chat_id=chat_id, message_id=sessions[chat_id]["event"]["last_poll_id"])
                        except:
                            pass

                    msg = await context.bot.send_message(
                        chat_id=chat_id,
                        text=group_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    sessions[chat_id]["event"]["last_poll_id"] = msg.message_id
                    save_sessions(sessions)
                except Exception as e:
                    logger.error(f"Failed to notify group: {e}")
    else:
        # In group chat—user responds to proposal
        ensure_member(chat_id, user_id, query.from_user.first_name or "User", sessions)
        if query.data.startswith("group_yes"):
            sessions[chat_id]["event"]["responses"][user_id] = "yes"
            
            # Check for full confirmation
            all_yes = all(r == "yes" for r in sessions[chat_id]["event"]["responses"].values())
            if all_yes:
                sessions[chat_id]["event"]["status"] = "confirmed"

            save_sessions(sessions)
            await query.answer("✅ Спасибо!")

            vote_status = get_responses_text(sessions[chat_id]["event"]["responses"], sessions[chat_id]["members"])

            if sessions[chat_id]["event"]["status"] == "confirmed":
                confirmed_time = sessions[chat_id]["event"]["current_time"]
                settings = load_settings()
                base_tz = settings["base_timezone"]
                tz_block = format_all_member_times(confirmed_time, base_tz, sessions[chat_id]["members"])

                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)
                except:
                    pass

                text = (
                    f"✅ <b>Время подтверждено!</b>\n\n"
                    f"{tz_block}\n\n"
                    f"{vote_status}"
                )
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Изменить", callback_data="group_propose")]
                ])
                msg = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=keyboard)
                sessions[chat_id]["event"]["last_poll_id"] = msg.message_id
                save_sessions(sessions)
            else:
                original_text = query.message.text.split("\n\n✅")[0].split("\n\n❌")[0].split("\n\n⏳")[0].split("\n\n🔔")[0]
                text = f"{original_text}\n\n{vote_status}"
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Подходит", callback_data=f"group_yes_{chat_id}_{user_id}")],
                    [InlineKeyboardButton("❌ Не подходит", callback_data=f"group_no_{chat_id}_{user_id}")],
                    [InlineKeyboardButton("🔄 Предложить другое", callback_data="group_propose")],
                ])
                await query.edit_message_text(
                    text=text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )

        elif query.data.startswith("group_no"):
            sessions[chat_id]["event"]["responses"][user_id] = "no"
            sessions[chat_id]["event"]["status"] = "idle"  # Reject proposal immediately
            save_sessions(sessions)
            await query.answer("❌ Записано. Предложение отклонено.")

            # Edit message to update vote list and remove buttons
            original_text = query.message.text.split("\n\n✅")[0].split("\n\n❌")[0].split("\n\n⏳")[0].split("\n\n🔔")[0]
            vote_status = get_responses_text(sessions[chat_id]["event"]["responses"], sessions[chat_id]["members"])
            
            text = (
                f"❌ <b>Предложение отклонено</b>\n\n"
                f"{original_text}\n\n"
                f"{vote_status}"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Предложить другое", callback_data="group_propose")]
            ])
            await query.edit_message_text(
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )

        elif query.data == "group_change":
            # Just refresh the vote list
            vote_status = get_responses_text(sessions[chat_id]["event"]["responses"], sessions[chat_id]["members"])
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Подходит", callback_data=f"group_yes_{chat_id}_{user_id}")],
                [InlineKeyboardButton("❌ Не подходит", callback_data=f"group_no_{chat_id}_{user_id}")],
                [InlineKeyboardButton("🔄 Предложить другое", callback_data="group_propose")],
            ])
            await query.edit_message_text(
                text=query.message.text.split("\n\n✅")[0].split("\n\n❌")[0].split("\n\n⏳")[0] + f"\n\n{vote_status}",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await query.answer()

        elif query.data == "group_propose":
            # Trigger time proposal UI in private chat
            ensure_member(chat_id, user_id, query.from_user.first_name or "User", sessions)
            settings = load_settings()
            base_tz_name = settings["base_timezone"]
            user_tz = sessions[chat_id]["members"][user_id]["timezone"]

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
                f"<code>{base_time} {base_tz_name}</code>\n"
                f"<code>{current_local} {user_tz}</code>\n\n"
                f"<b>Выберите время или напишите своё</b> (в вашем часовом поясе):\n"
                f"<i>Примеры: 7:20 · 7.20 · 7 20 · 19:30</i>\n\n"
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
                pending = load_pending_proposals()
                pending[user_id] = chat_id
                save_pending_proposals(pending)
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

        # Auto-confirm
        event["status"] = "confirmed"
        confirmed_time = event.get("current_time", settings["call_time"])
        logger.info(f"Chat {chat_id}: Auto-confirmed at {confirmed_time}")

        # Delete old invite message and send clean confirmation
        if event.get("last_poll_id"):
            try:
                await app.bot.delete_message(chat_id=chat_id, message_id=event["last_poll_id"])
            except Exception as e:
                logger.warning(f"Failed to delete old invite in {chat_id}: {e}")

        vote_status = get_responses_text(event.get("responses", {}), session_data["members"])
        tz_block = format_all_member_times(confirmed_time, base_tz, session_data["members"])

        text = (
            f"✅ <b>Время автоматически подтверждено!</b>\n\n"
            f"🕒 <code>{confirmed_time} {base_tz}</code>\n\n"
            f"{tz_block}\n\n"
            f"{vote_status}"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Изменить", callback_data="group_propose")]
        ])
        try:
            msg = await app.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            event["last_poll_id"] = msg.message_id
        except Exception as e:
            logger.error(f"Failed to send auto-confirm message in {chat_id}: {e}")

    save_sessions(sessions)


async def reminder_check_job(app):
    """Periodic check (every 5 min): send 30-min and 5-min reminders based on confirmed call time."""
    logger.info("Reminder check job triggered")
    sessions = load_sessions()
    settings = load_settings()
    base_tz_name = settings["base_timezone"]
    base_tz = pytz.timezone(base_tz_name)

    now = datetime.now(timezone.utc)

    # Determine the call day: the day after poll_day (e.g. Saturday invite → Sunday call)
    _day_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
                "Friday": 4, "Saturday": 5, "Sunday": 6}
    poll_day_num = _day_map.get(settings.get("poll_day", "Saturday"), 5)
    call_day_num = (poll_day_num + 1) % 7  # Sunday = 6

    for chat_id, session_data in sessions.items():
        if int(chat_id) > 0:
            continue
        event = session_data.get("event", {})
        if event.get("status") != "confirmed":
            continue

        call_time_str = event.get("current_time", settings["call_time"])
        h, m = map(int, call_time_str.split(":"))
        now_base = now.astimezone(base_tz)

        # Find the next occurrence of call_day at call_time (never fire on the wrong weekday)
        days_until_call = (call_day_num - now_base.weekday()) % 7
        if days_until_call == 0:
            call_naive = now_base.replace(hour=h, minute=m, second=0, microsecond=0, tzinfo=None)
            call_dt = base_tz.localize(call_naive)
            if call_dt <= now_base:
                # Call time already passed today — next occurrence is next week
                call_dt = base_tz.localize(
                    (now_base + timedelta(days=7)).replace(
                        hour=h, minute=m, second=0, microsecond=0, tzinfo=None
                    )
                )
        else:
            call_dt = base_tz.localize(
                (now_base + timedelta(days=days_until_call)).replace(
                    hour=h, minute=m, second=0, microsecond=0, tzinfo=None
                )
            )

        minutes_until = (call_dt - now_base).total_seconds() / 60

        if minutes_until <= 0:
            continue

        # 30-min reminder (presence check)
        if not event.get("reminder_30_sent") and minutes_until <= 30:
            logger.info(f"Chat {chat_id}: sending 30-min reminder (call in {minutes_until:.0f} min)")

            if event.get("last_poll_id"):
                try:
                    await app.bot.delete_message(chat_id=chat_id, message_id=event["last_poll_id"])
                except:
                    pass

            tz_block = format_all_member_times(call_time_str, base_tz_name, session_data["members"])
            text = (
f"🔔 <b>Напоминание: Созвон через 30 минут!</b>\n\n"
                f"{tz_block}\n\n"
                f"Все готовы?"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⏳ +15 мин", callback_data="pres_delay_15")],
                [InlineKeyboardButton("⏳ +30 мин", callback_data="pres_delay_30")]
            ])
            msg = await app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=keyboard)
            event["last_poll_id"] = msg.message_id
            event["reminder_30_sent"] = True

        # 5-min reminder
        if not event.get("reminder_5_sent") and minutes_until <= 5:
            logger.info(f"Chat {chat_id}: sending 5-min reminder (call in {minutes_until:.0f} min)")

            if event.get("last_poll_id"):
                try:
                    await app.bot.delete_message(chat_id=chat_id, message_id=event["last_poll_id"])
                except:
                    pass

            responses = event.get("responses", {})
            vote_status = get_responses_text(responses, session_data["members"])

            tz_block = format_all_member_times(call_time_str, base_tz_name, session_data["members"])
            text = (
                f"⏰ <b>Созвон через 5 минут!</b>\n\n"
                f"{tz_block}\n\n"
                f"<b>Кто будет:</b>\n{vote_status or 'Все подтвердили!'}"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⏳ +15 мин", callback_data="pres_delay_15")],
                [InlineKeyboardButton("⏳ +30 мин", callback_data="pres_delay_30")]
            ])
            msg = await app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=keyboard)
            event["last_poll_id"] = msg.message_id
            event["reminder_5_sent"] = True

    save_sessions(sessions)


async def handle_presence_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle buttons from the 30-min reminder."""
    query = update.callback_query
    await query.answer()
    sessions = load_sessions()
    chat_id, user_id = str(query.message.chat_id), str(query.from_user.id)
    user_name = query.from_user.first_name or "User"

    # Handle delays
    delay_mins = 15 if "15" in query.data else 30
    settings = load_settings()
    base_tz = settings["base_timezone"]
    current_time = sessions[chat_id]["event"].get("current_time", settings["call_time"])
    
    # Calculate new time
    h, m = map(int, current_time.split(":"))
    new_dt = datetime(2026, 1, 1, h, m) + timedelta(minutes=delay_mins)
    new_time = new_dt.strftime("%H:%M")
    
    sessions[chat_id]["event"]["current_time"] = new_time
    sessions[chat_id]["event"]["reminder_5_sent"] = False
    save_sessions(sessions)
    
    # Generate timezone block for all members
    tz_block = format_all_member_times(new_time, base_tz, sessions[chat_id]["members"])
    
    # Update the message instead of replying
    text = (
        f"🔔 <b>Напоминание: Созвон скоро!</b>\n\n"
        f"⏳ {html.escape(user_name)} попросил задержаться на {delay_mins} мин.\n"
        f"🕒 Новое время: <code>{new_time} {base_tz}</code>\n\n"
        f"{tz_block}"
    )
    
    try:
        await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=None)
    except Exception as e:
        logger.error(f"Failed to update presence message: {e}")


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
        if int(chat_id) > 0:
            logger.info(f"Skipping private chat {chat_id}")
            continue

        try:
            # Cleanup previous message before resetting event
            old_poll_id = session_data.get("event", {}).get("last_poll_id")
            if old_poll_id:
                try:
                    await app.bot.delete_message(chat_id=chat_id, message_id=old_poll_id)
                except Exception as e:
                    logger.warning(f"Failed to delete old message in {chat_id}: {e}")

            # Reset event state
            deadline_delta = timedelta(hours=settings.get("auto_confirm_hours", 12))
            session_data["event"] = {
                "status": "proposed",
                "proposal_id": None,
                "current_time": base_time,
                "proposal_author": None,
                "deadline": (datetime.now(timezone.utc) + deadline_delta).isoformat(),
                "responses": {uid: "pending" for uid in session_data["members"].keys()},
                "reminder_30_sent": False,
                "reminder_5_sent": False,
            }
            save_sessions(sessions)

            tz_block = format_all_member_times(base_time, base_tz, session_data["members"])
            vote_status = get_responses_text(session_data["event"]["responses"], session_data["members"])

            text = (
                f"Созвон в воскресенье:\n\n"
                f"{tz_block}\n\n"
                f"Подходит?\n\n"
                f"{vote_status}"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Подходит", callback_data="fri_yes")],
                [InlineKeyboardButton("🔄 Предложить другое", callback_data="fri_propose")],
                [InlineKeyboardButton("❌ Не смогу", callback_data="fri_no")],
            ])

            msg = await app.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            session_data["event"]["last_poll_id"] = msg.message_id
            save_sessions(sessions)
            logger.info(f"Weekly invite sent to chat {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send weekly invite to {chat_id}: {e}")


async def handle_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /trigger — start the call scheduling flow on-demand (admin only)."""
    sessions = load_sessions()
    chat_id = str(update.message.chat_id)
    user_id = str(update.message.from_user.id)

    if int(chat_id) > 0:
        await update.message.reply_text("❌ Работает только в группах.")
        return

    # Auto-register group + user if this is the first time
    if chat_id not in sessions:
        ensure_member(chat_id, user_id, update.message.from_user.first_name or "User", sessions)
        sessions[chat_id]["members"][user_id]["is_admin"] = True
        save_sessions(sessions)
    elif user_id not in sessions[chat_id]["members"]:
        ensure_member(chat_id, user_id, update.message.from_user.first_name or "User", sessions)

    is_admin = sessions[chat_id]["members"][user_id].get("is_admin", False)
    if not is_admin:
        await update.message.reply_text("❌ Только администратор.")
        return

    settings = load_settings()
    session_data = sessions[chat_id]
    base_time = settings.get("call_time", "17:00")
    base_tz = settings.get("base_timezone", "Europe/Minsk")

    if context.args:
        parsed = parse_time_input(context.args[0])
        if parsed:
            base_time = parsed

    old_poll_id = session_data.get("event", {}).get("last_poll_id")

    deadline_delta = timedelta(hours=settings.get("auto_confirm_hours", 12))
    session_data["event"] = {
        "status": "proposed",
        "proposal_id": None,
        "current_time": base_time,
        "proposal_author": None,
        "deadline": (datetime.now(timezone.utc) + deadline_delta).isoformat(),
        "responses": {uid: "pending" for uid in session_data["members"].keys()},
        "reminder_30_sent": False,
        "reminder_5_sent": False,
    }
    save_sessions(sessions)

    if old_poll_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=old_poll_id)
        except:
            pass

    tz_block = format_all_member_times(base_time, base_tz, session_data["members"])
    vote_status = get_responses_text(session_data["event"]["responses"], session_data["members"])

    text = (
        f"Созвон в воскресенье:\n\n"
        f"{tz_block}\n\n"
        f"Подходит?\n\n"
        f"{vote_status}"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подходит", callback_data="fri_yes")],
        [InlineKeyboardButton("🔄 Предложить другое", callback_data="fri_propose")],
        [InlineKeyboardButton("❌ Не смогу", callback_data="fri_no")],
    ])

    msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    session_data["event"]["last_poll_id"] = msg.message_id
    save_sessions(sessions)


def get_responses_text(responses: dict, members: dict) -> str:
    """Generate a text summary of who voted what."""
    if not responses:
        return ""
    
    yes_votes = [members[uid]["name"] for uid, res in responses.items() if res == "yes" and uid in members]
    no_votes = [members[uid]["name"] for uid, res in responses.items() if res == "no" and uid in members]
    pending = [members[uid]["name"] for uid, res in responses.items() if res == "pending" and uid in members]
    
    lines = []
    if yes_votes:
        lines.append(f"✅ {', '.join(yes_votes)}")
    if no_votes:
        lines.append(f"❌ {', '.join(no_votes)}")
    if pending:
        lines.append(f"⏳ Ожидаем: {', '.join(pending)}")
    
    return "\n".join(lines)


async def handle_friday_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Friday invite button responses."""
    query = update.callback_query
    await query.answer()

    sessions = load_sessions()
    chat_id = str(query.message.chat_id)
    user_id = str(query.from_user.id)
    user_name = query.from_user.first_name or "User"

    # Auto-register user with default timezone if not in session
    ensure_member(chat_id, user_id, user_name, sessions)

    if query.data == "fri_yes":
        if chat_id in sessions:
            sessions[chat_id]["event"]["responses"][user_id] = "yes"

            # Check for full confirmation
            all_yes = all(r == "yes" for r in sessions[chat_id]["event"]["responses"].values())
            if all_yes:
                sessions[chat_id]["event"]["status"] = "confirmed"

        save_sessions(sessions)
        await query.answer("✅ Спасибо!")

        if sessions[chat_id]["event"]["status"] == "confirmed":
            confirmed_time = sessions[chat_id]["event"]["current_time"]
            settings = load_settings()
            base_tz = settings["base_timezone"]
            tz_block = format_all_member_times(confirmed_time, base_tz, sessions[chat_id]["members"])
            vote_status = get_responses_text(sessions[chat_id]["event"]["responses"], sessions[chat_id]["members"])

            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)
            except:
                pass

            text = (
                f"✅ <b>Время подтверждено!</b>\n\n"
                f"{tz_block}\n\n"
                f"{vote_status}"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Изменить", callback_data="fri_propose")]
            ])
            msg = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=keyboard)
            sessions[chat_id]["event"]["last_poll_id"] = msg.message_id
            save_sessions(sessions)
        else:
            original_text = query.message.text.split("\n\n✅")[0].split("\n\n❌")[0].split("\n\n⏳")[0].split("\n\n🔔")[0]
            vote_status = get_responses_text(sessions[chat_id]["event"]["responses"], sessions[chat_id]["members"])
            text = f"{original_text}\n\n{vote_status}"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Подходит", callback_data="fri_yes")],
                [InlineKeyboardButton("🔄 Предложить другое", callback_data="fri_propose")],
                [InlineKeyboardButton("❌ Не смогу", callback_data="fri_no")],
            ])
            await query.edit_message_text(
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )

    elif query.data == "fri_no":
        if chat_id in sessions:
            sessions[chat_id]["event"]["responses"][user_id] = "no"
            sessions[chat_id]["event"]["status"] = "idle"  # Reject proposal immediately
        save_sessions(sessions)
        await query.answer("❌ Записано. Опрос отклонен.")

        # Edit message to update vote list and remove buttons
        original_text = query.message.text.split("\n\n✅")[0].split("\n\n❌")[0].split("\n\n⏳")[0].split("\n\n🔔")[0]
        vote_status = get_responses_text(sessions[chat_id]["event"]["responses"], sessions[chat_id]["members"])
        
        text = (
            f"❌ <b>Опрос отклонен</b>\n\n"
            f"{original_text}\n\n"
            f"{vote_status}"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Предложить новое время", callback_data="fri_propose")]
        ])
        await query.edit_message_text(
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    elif query.data == "fri_change":
        # Just refresh the vote list if it was stuck
        vote_status = get_responses_text(sessions[chat_id]["event"]["responses"], sessions[chat_id]["members"])
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Подходит", callback_data="fri_yes")],
            [InlineKeyboardButton("🔄 Предложить другое", callback_data="fri_propose")],
            [InlineKeyboardButton("❌ Не смогу", callback_data="fri_no")],
        ])
        await query.edit_message_text(
            text=query.message.text.split("\n\n✅")[0].split("\n\n❌")[0].split("\n\n⏳")[0] + f"\n\n{vote_status}",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await query.answer()

    elif query.data == "fri_propose":
        # Send time options in private chat
        user_tz = sessions[chat_id]["members"][user_id]["timezone"]
        settings = load_settings()
        base_time = settings["call_time"]
        base_tz_name = settings["base_timezone"]

        options = generate_time_options(base_time)
        tz_options = []
        for opt in options:
            local_time = format_time_in_tz(opt, base_tz_name, user_tz)
            tz_options.append((opt, local_time))

        current_local = format_time_in_tz(base_time, base_tz_name, user_tz)
        text = (
            f"<b>Текущее время:</b> {current_local} ({user_tz})\n\n"
            f"<b>Выберите время или напишите своё</b> (в вашем часовом поясе):\n"
            f"<i>Примеры: 7:20 · 7.20 · 7 20 · 19:30</i>\n\n"
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
            pending = load_pending_proposals()
            pending[user_id] = chat_id
            save_pending_proposals(pending)
            await query.answer("Отправил вам варианты в личное сообщение.")
        except Exception as e:
            logger.error(f"Failed to send private message: {e}")
            await query.answer("❌ Ошибка. Попробуйте еще раз.", alert=True)


async def handle_time_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle free-form time typed in private chat as a proposal (e.g. '7:20', '7.20', '7 20')."""
    if not update.message or update.message.chat.type != "private":
        return

    text = (update.message.text or "").strip()
    user_id = str(update.message.from_user.id)

    time_str = parse_time_input(text)
    if not time_str:
        return  # Not a time input — ignore silently

    pending = load_pending_proposals()
    group_chat_id = pending.get(user_id)
    if not group_chat_id:
        return  # User isn't mid-proposal — ignore silently

    sessions = load_sessions()
    settings = load_settings()
    base_tz_name = settings["base_timezone"]

    if group_chat_id not in sessions:
        await update.message.reply_text("❌ Сессия истекла. Попросите администратора отправить новый опрос.")
        return

    user_tz_name = (
        sessions[group_chat_id].get("members", {}).get(user_id, {}).get("timezone")
        or get_user_timezone(user_id)
        or DEFAULT_TIMEZONE
    )

    # Convert typed time (user's local tz) → base timezone
    try:
        user_tz = pytz.timezone(user_tz_name)
        base_tz_obj = pytz.timezone(base_tz_name)
        h, mn = map(int, time_str.split(":"))
        dt_user = user_tz.localize(datetime(2026, 5, 5, h, mn))
        base_time_str = dt_user.astimezone(base_tz_obj).strftime("%H:%M")
    except Exception as e:
        logger.error(f"Time text input conversion error: {e}")
        await update.message.reply_text("❌ Не удалось конвертировать время.")
        return

    # Apply proposal
    sessions[group_chat_id]["event"]["current_time"] = base_time_str
    sessions[group_chat_id]["event"]["proposal_author"] = user_id
    responses = {uid: ("yes" if uid == user_id else "pending") for uid in sessions[group_chat_id]["members"].keys()}
    sessions[group_chat_id]["event"]["responses"] = responses

    # Check for immediate confirmation: all members voted 'yes'
    all_yes = all(r == "yes" for r in responses.values())

    if all_yes:
        sessions[group_chat_id]["event"]["status"] = "confirmed"
        status_text = "Принято (все подтвердили)"
    else:
        sessions[group_chat_id]["event"]["status"] = "proposed"
        status_text = "Уведомил всех"

    auto_confirm_hours = settings.get("auto_confirm_hours", 12)
    deadline_delta = timedelta(hours=auto_confirm_hours)
    sessions[group_chat_id]["event"]["deadline"] = (datetime.now(timezone.utc) + deadline_delta).isoformat()

    save_sessions(sessions)

    # Clear pending proposal
    pending.pop(user_id, None)
    save_pending_proposals(pending)

    # Private feedback
    local_time = format_time_in_tz(base_time_str, base_tz_name, user_tz_name)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Изменить время", callback_data=f"private_change_time_{group_chat_id}")]
    ])
    await update.message.reply_text(
        f"✅ Принято 👍\n\n"
        f"➡️ <b>{local_time}</b> ({user_tz_name})\n\n"
        f"{status_text}",
        parse_mode="HTML",
        reply_markup=keyboard
    )

    # Notify group
    author_name = sessions[group_chat_id]["members"].get(user_id, {}).get("name", "User")
    tz_block = format_all_member_times(base_time_str, base_tz_name, sessions[group_chat_id]["members"])

    if sessions[group_chat_id]["event"]["status"] == "confirmed":
        group_text = (
            f"✅ {html.escape(author_name)} установил новое время:\n\n"
            f"{tz_block}"
        )
        group_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Изменить", callback_data="group_propose")]
        ])
    else:
        group_text = (
            f"{html.escape(author_name)} предлагает новое время:\n\n"
            f"{tz_block}\n\n"
            f"Подходит?"
        )
        group_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Подходит", callback_data=f"group_yes_{group_chat_id}_{user_id}")],
            [InlineKeyboardButton("❌ Не подходит", callback_data=f"group_no_{group_chat_id}_{user_id}")],
            [InlineKeyboardButton("🔄 Предложить другое", callback_data="group_propose")],
        ])

    try:
        # Cleanup previous poll if it exists
        if sessions[group_chat_id]["event"].get("last_poll_id"):
            try:
                await context.bot.delete_message(chat_id=group_chat_id, message_id=sessions[group_chat_id]["event"]["last_poll_id"])
            except:
                pass

        msg = await context.bot.send_message(
            chat_id=group_chat_id,
            text=group_text,
            parse_mode="HTML",
            reply_markup=group_keyboard
        )
        sessions[group_chat_id]["event"]["last_poll_id"] = msg.message_id
        save_sessions(sessions)
    except Exception as e:
        logger.error(f"Failed to notify group from text proposal: {e}")


async def set_bot_commands(app):
    """Set bot commands for the UI."""
    commands = [
        BotCommand("tz", "Установить временную зону (Telegram limitation: ASCII only)"),
        BotCommand("mytime", "Показать ваше время"),
        BotCommand("help", "Список команд"),
        BotCommand("trigger", "Запустить цикл созвона сейчас (администратор)"),
        BotCommand("time", "Обновить время созвона (администратор)"),
        BotCommand("poll", "Включить/отключить опросы"),
    ]
    await app.bot.set_my_commands(commands)


async def post_init(app):
    """Called after bot starts."""
    await set_bot_commands(app)

    scheduler = AsyncIOScheduler()
    scheduler.start()

    settings = load_settings()
    base_tz_name = settings.get("base_timezone", "Europe/Minsk")
    base_tz = pytz.timezone(base_tz_name)

    # Schedule Friday invite (cron)
    poll_day_str = settings.get("poll_day", "Friday")
    poll_time_str = settings.get("poll_time", "12:00")
    days = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
    day_of_week = days.get(poll_day_str.lower(), 4)
    hour, minute = map(int, poll_time_str.split(":"))
    scheduler.add_job(
        friday_invite_job,
        "cron",
        day_of_week=day_of_week,
        hour=hour,
        minute=minute,
        timezone=base_tz,
        args=[app],
        id="friday_invite",
        replace_existing=True
    )
    logger.info(f"Friday invite scheduled for {poll_day_str} {poll_time_str}")

    # Schedule reminder check (every 5 minutes)
    scheduler.add_job(
        reminder_check_job,
        "interval",
        minutes=5,
        args=[app],
        id="reminder_check",
        replace_existing=True
    )

    # Schedule auto-confirm check (every 60 seconds)
    scheduler.add_job(
        check_autoconfirm_job,
        "interval",
        seconds=60,
        args=[app],
        id="autoconfirm_check",
        replace_existing=True
    )

    logger.info("Scheduler initialized")
    app.scheduler = scheduler


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Auto-register any user who sends a message in a known group."""
    if not update.message or not update.message.from_user:
        return
    chat_id = str(update.message.chat_id)
    if int(chat_id) > 0:
        return
    sessions = load_sessions()
    if chat_id not in sessions:
        return
    user_id = str(update.message.from_user.id)
    if user_id not in sessions[chat_id]["members"]:
        ensure_member(chat_id, user_id, update.message.from_user.first_name or "User", sessions)
        save_sessions(sessions)


def main():
    load_dotenv(dotenv_path=".env.local")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in .env.local")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("tz", handle_timezone))
    app.add_handler(CommandHandler("mytime", handle_mytime))
    app.add_handler(CommandHandler("help", handle_help))
    app.add_handler(CommandHandler("trigger", handle_trigger))
    app.add_handler(CommandHandler("time", handle_time_command))
    app.add_handler(CommandHandler("poll", handle_poll_on))

    # Auto-register when bot is added to a group
    app.add_handler(ChatMemberHandler(handle_my_chat_member, chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER))

    # Callback handlers
    app.add_handler(CallbackQueryHandler(handle_private_change_time, pattern="^private_change_time_"))
    app.add_handler(CallbackQueryHandler(handle_friday_response, pattern="^fri_"))
    app.add_handler(CallbackQueryHandler(handle_proposal_yes, pattern="^time_"))
    app.add_handler(CallbackQueryHandler(handle_proposal_yes, pattern="^group_"))
    app.add_handler(CallbackQueryHandler(handle_presence_callback, pattern="^pres_"))

    # Free-text time input in private chat (e.g. "7:20", "7.20", "7 20")
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND, handle_time_text_input))

    # Auto-register group members when they send any message (low priority, group 1)
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & ~filters.COMMAND, handle_group_message), group=1)

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
