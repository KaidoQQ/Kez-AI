import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from core.loader import db
from core.logger import logger
from core.i18n import tr
from core.constants.const import (
    PROMPTS,
    WEEKDAYS_RU,
    TIME_UNITS,
    NUMBER_WORDS,
    _NUMBER,
    _UNIT,
    RELATIVE_PATTERN,
    HALF_HOUR_PATTERN,
    CLOCK_PATTERN,
    TOMORROW_PATTERN,
    CLEANUP_PATTERN
)
from app.backend.utils.llm_fallback import generate_response_with_fallback


@dataclass
class ReminderRequest:
    """Разобранный запрос на напоминание."""
    due_at: datetime
    text: str


def _unit_for(raw_unit: str) -> str:
    for pattern, unit in TIME_UNITS:
        if re.fullmatch(pattern, raw_unit, re.IGNORECASE):
            return unit
    return "minutes"


def _clean_reminder_text(text: str, removed_spans: list[tuple[int, int]]) -> str:
    """Убирает из запроса время и служебные слова, оставляя суть напоминания."""
    chars: list[str] = list(text)
    for start, end in removed_spans:
        for i in range(start, end):
            chars[i] = " "
    remaining: str = CLEANUP_PATTERN.sub(" ", "".join(chars))
    remaining = re.sub(r"\s+", " ", remaining).strip(" ,.:;-!")
    return remaining


def parse_reminder_locally(text: str, now: datetime) -> ReminderRequest | None:
    """
    Быстрый разбор без LLM: «через 10 минут ...», «на полчаса», «в 18:30 ...», «завтра в 9 ...».
    Возвращает None, если время не распознано.
    """
    spans: list[tuple[int, int]] = []
    due_at: datetime | None = None
    is_timer: bool = bool(re.search(r"\b(таймер|timer)\b", text, re.IGNORECASE))

    if half := HALF_HOUR_PATTERN.search(text):
        due_at = now + timedelta(minutes=30)
        spans.append(half.span())
    elif relative := RELATIVE_PATTERN.search(text):
        raw_amount: str | None = relative.group("amount") or relative.group("amount2")
        raw_unit: str = relative.group("unit") or relative.group("unit2")
        if raw_amount is None:
            amount: float = 1
        elif raw_amount.lower() in NUMBER_WORDS:
            amount = NUMBER_WORDS[raw_amount.lower()]
        else:
            amount = float(raw_amount.replace(",", "."))
        due_at = now + timedelta(**{_unit_for(raw_unit): amount})
        spans.append(relative.span())
    elif clock := CLOCK_PATTERN.search(text):
        hour: int = int(clock.group(1) or clock.group(3))
        minute: int = int(clock.group(2) or 0)
        if hour > 23 or minute > 59:
            return None
        due_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        spans.append(clock.span())
        if tomorrow := TOMORROW_PATTERN.search(text):
            due_at += timedelta(days=1)
            spans.append(tomorrow.span())
        elif due_at <= now:
            due_at += timedelta(days=1)

    if due_at is None:
        return None

    reminder_text: str = _clean_reminder_text(text, spans)
    if not reminder_text:
        reminder_text = tr("reminder.timer_text") if is_timer else tr("reminder.default_text")
    return ReminderRequest(due_at=due_at, text=reminder_text)


async def parse_reminder_with_llm(text: str, now: datetime) -> ReminderRequest | None:
    """Разбор сложных формулировок («в пятницу вечером», «послезавтра в обед») через LLM."""
    template: str = PROMPTS.get("reminder_parse", "")
    if not template:
        return None
    prompt: str = (
        template.replace("{NOW}", now.strftime("%Y-%m-%dT%H:%M:%S"))
        .replace("{WEEKDAY}", WEEKDAYS_RU[now.weekday()])
        .replace("{USER_MESSAGE}", text)
    )
    raw_response: str = await generate_response_with_fallback(prompt)
    cleaned: str = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_response.strip(), flags=re.MULTILINE).strip()
    try:
        data: dict = json.loads(cleaned)
        due_raw: str = str(data.get("due", "")).strip()
        if not due_raw:
            return None
        due_at: datetime = datetime.fromisoformat(due_raw).replace(tzinfo=None)
        return ReminderRequest(due_at=due_at, text=str(data.get("text", "")).strip() or tr("reminder.default_text"))
    except (json.JSONDecodeError, ValueError, AttributeError) as e:
        logger.error(f"Не удалось разобрать ответ LLM для напоминания: {e}")
        return None


def format_due(due_at: datetime, now: datetime) -> str:
    """Человекочитаемое время срабатывания: «сегодня в 18:30», «завтра в 09:00», «25.10 в 12:00»."""
    time_str: str = due_at.strftime("%H:%M")
    if due_at.date() == now.date():
        delta: timedelta = due_at - now
        if delta < timedelta(hours=1):
            minutes: int = max(1, round(delta.total_seconds() / 60))
            return tr("reminder.due_minutes", minutes=minutes, time=time_str)
        return tr("reminder.due_today", time=time_str)
    if due_at.date() == (now + timedelta(days=1)).date():
        return tr("reminder.due_tomorrow", time=time_str)
    # Кириллица в strftime на Windows падает с UnicodeEncodeError — собираем строку вручную
    return tr("reminder.due_date", date=due_at.strftime("%d.%m"), time=time_str)


async def create_reminder_from_request(user_text: str, chat_id: int | None) -> str:
    """
    Пайплайн напоминаний: разбирает время (локально, затем LLM), сохраняет в БД
    и возвращает ответ Kez для пользователя.
    """
    now: datetime = datetime.now()

    if re.search(r"\b(мои напоминания|какие напоминания|список напоминаний|my reminders)\b", user_text, re.IGNORECASE):
        pending: list[dict] = await db.get_pending_reminders()
        if not pending:
            return tr("reminder.none")
        lines: list[str] = [f"- **{format_due(r['due_at'], now)}** — {r['text_content']}" for r in pending]
        return tr("reminder.list_header") + "\n" + "\n".join(lines)

    request: ReminderRequest | None = parse_reminder_locally(user_text, now)
    if request is None:
        request = await parse_reminder_with_llm(user_text, now)
    if request is None:
        return tr("reminder.ask_time")
    if request.due_at <= now:
        return tr("reminder.in_past")

    reminder_id = await db.add_reminder(chat_id, request.text, request.due_at)
    if reminder_id is None:
        return tr("reminder.save_failed")
    return tr("reminder.created", when=format_due(request.due_at, now), text=request.text)
