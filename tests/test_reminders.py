from datetime import datetime, timedelta

import pytest

from app.backend.piplines.start.reminders import parse_reminder_locally, format_due

NOW = datetime(2026, 10, 20, 14, 0, 0)


@pytest.mark.parametrize("text, delta, reminder_text", [
    ("напомни через 10 минут проверить духовку", timedelta(minutes=10), "проверить духовку"),
    ("напомни мне через 2 часа позвонить маме", timedelta(hours=2), "позвонить маме"),
    ("напомни через минуту выпить воды", timedelta(minutes=1), "выпить воды"),
    ("поставь таймер на 5 минут", timedelta(minutes=5), "Таймер"),
    ("напомни через полчаса выключить чайник", timedelta(minutes=30), "выключить чайник"),
    ("remind me in 3 hours to stretch", timedelta(hours=3), "stretch"),
])
def test_relative_reminders(text, delta, reminder_text):
    request = parse_reminder_locally(text, NOW)
    assert request is not None
    assert request.due_at == NOW + delta
    assert request.text == reminder_text


def test_clock_time_today_and_tomorrow():
    later = parse_reminder_locally("напомни в 18:30 забрать посылку", NOW)
    assert later.due_at == NOW.replace(hour=18, minute=30)
    assert later.text == "забрать посылку"

    passed = parse_reminder_locally("напомни в 9:15 сделать зарядку", NOW)
    assert passed.due_at == (NOW + timedelta(days=1)).replace(hour=9, minute=15)

    tomorrow = parse_reminder_locally("напомни завтра в 20:00 полить цветы", NOW)
    assert tomorrow.due_at == (NOW + timedelta(days=1)).replace(hour=20, minute=0)
    assert tomorrow.text == "полить цветы"


def test_birthday_is_not_a_duration():
    # «на день рождения» — не «на 1 день», время не распознано -> уйдёт в LLM
    assert parse_reminder_locally("напомни купить подарок на день рождения", NOW) is None


def test_format_due():
    assert format_due(NOW + timedelta(minutes=10), NOW) == "через 10 мин (в 14:10)"
    assert format_due(NOW.replace(hour=19), NOW) == "сегодня в 19:00"
    assert format_due(NOW + timedelta(days=1), NOW) == "завтра в 14:00"
    assert format_due(NOW + timedelta(days=5), NOW) == "25.10 в 14:00"
