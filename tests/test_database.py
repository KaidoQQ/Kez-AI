"""
Тесты SQL-слоя на настоящем PostgreSQL (DATABASE_URL).
В CI база поднимается сервисом GitHub Actions; локально — `docker-compose up -d db`.
Если база недоступна, тесты пропускаются.
"""
import asyncio
from datetime import datetime, timedelta

import pytest

from core.loader import db

TEST_PREFIX: str = "__kez_test__"



@pytest.fixture(scope="module")
def database():
    async def setup():
        await asyncio.wait_for(db.connect(), 5)
        await db.create_tables()

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(setup())
    except Exception as e:
        loop.close()
        pytest.skip(f"PostgreSQL недоступен: {e}")

    yield loop

    async def teardown():
        await db.execute("DELETE FROM user_facts WHERE fact LIKE $1", f"{TEST_PREFIX}%")
        await db.execute("DELETE FROM reminders WHERE text_content LIKE $1", f"{TEST_PREFIX}%")
        await db.execute("DELETE FROM history_chats WHERE title LIKE $1", f"{TEST_PREFIX}%")
        await db.close()

    loop.run_until_complete(teardown())
    loop.close()


def test_chat_and_messages(database):
    async def scenario():
        chat_id = await db.create_chat(f"{TEST_PREFIX}chat")
        await db.add_message_to_chat(chat_id, "user", "Привет, Kez!")
        await db.add_message_to_chat(chat_id, "ai", "Чирик! [IMAGE:/tmp/a.png]")
        return await db.get_chat_messages(chat_id)

    messages = database.run_until_complete(scenario())
    assert [m["sender_type"] for m in messages] == ["user", "ai"]


def test_full_text_search(database):
    async def scenario():
        chat_id = await db.create_chat(f"{TEST_PREFIX}search")
        await db.add_message_to_chat(chat_id, "user", "Мой попугай Кеша любит семечки")
        full = await db.search_messages("попугай")
        partial = await db.search_messages("семеч")
        special = await db.search_messages("100%_")
        return chat_id, full, partial, special

    chat_id, full, partial, special = database.run_until_complete(scenario())
    assert any(r["chat_id"] == chat_id for r in full)
    assert any(r["chat_id"] == chat_id for r in partial)   # ILIKE по части слова
    assert special == []                                    # % и _ экранируются


def test_user_facts_deduplicated(database):
    fact = f"{TEST_PREFIX}Есть попугай Кеша"

    async def scenario():
        added = await db.add_user_facts([fact, fact])
        added_again = await db.add_user_facts([fact])
        facts = [f for f in await db.get_user_facts() if f["fact"] == fact]
        deleted = await db.delete_user_fact(facts[0]["id"])
        return added, added_again, len(facts), deleted

    assert database.run_until_complete(scenario()) == (1, 0, 1, True)


def test_reminders_lifecycle(database):
    async def scenario():
        now = datetime.now()
        due_id = await db.add_reminder(None, f"{TEST_PREFIX}пора", now - timedelta(seconds=1))
        future_id = await db.add_reminder(None, f"{TEST_PREFIX}потом", now + timedelta(hours=1))

        due_ids = {r["id"] for r in await db.get_due_reminders(now)}
        pending_ids = {r["id"] for r in await db.get_pending_reminders()}
        await db.mark_reminder_done(due_id)
        due_after = {r["id"] for r in await db.get_due_reminders(now)}
        return due_id, future_id, due_ids, pending_ids, due_after

    due_id, future_id, due_ids, pending_ids, due_after = database.run_until_complete(scenario())
    assert due_id in due_ids and future_id not in due_ids
    assert {due_id, future_id} <= pending_ids
    assert due_id not in due_after


def test_reminder_survives_chat_deletion(database):
    """ON DELETE SET NULL: напоминание остаётся, даже если чат удалён."""
    async def scenario():
        chat_id = await db.create_chat(f"{TEST_PREFIX}temp")
        reminder_id = await db.add_reminder(chat_id, f"{TEST_PREFIX}важное", datetime.now() + timedelta(days=1))
        await db.delete_chat(chat_id)
        return reminder_id, await db.get_pending_reminders()

    reminder_id, pending = database.run_until_complete(scenario())
    reminder = next(r for r in pending if r["id"] == reminder_id)
    assert reminder["chat_id"] is None
