from pathlib import Path
from typing import Any

from core.loader import db
from core.logger import logger
from core.constants.const import PROMPTS, PROMPTS_DIR
from app.backend.utils.llm_fallback import generate_response_with_fallback


def format_chat_history(messages: list[dict[str, Any]]) -> str:
    """
    Форматирует сообщения из базы данных в читаемую историю диалога для промпта.
    """
    if not messages:
        return "История предыдущего общения пуста."

    formatted_lines: list[str] = []
    for msg in messages:
        sender_raw: str = str(msg.get("sender_type", "user")).lower()
        sender_label: str = "User" if sender_raw == "user" else "Kez"
        text: str = str(msg.get("text_content", "")).strip()
        formatted_lines.append(f"{sender_label}: {text}")

    return "\n".join(formatted_lines)


def format_user_profile(user_info: dict[str, Any] | None) -> str:
    """
    Форматирует данные профиля пользователя для промпта LLM.
    """
    if not user_info:
        return "Информация о пользователе пока неизвестна."

    full_name: str = str(user_info.get("full_name", "")).strip() or "Не указано"
    birth: Any = user_info.get("birth", "")
    birth_str: str = str(birth).strip() if birth else "Не указано"
    interests: str = str(user_info.get("interests", "")).strip() or "Не указано"

    return f"Имя: {full_name}\nВозраст / дата рождения: {birth_str}\nИнтересы и увлечения: {interests}"


def build_memory_prompt(template: str, history_text: str, user_text: str, profile_text: str = "") -> str:
    """
    Подставляет профиль пользователя, историю сообщений и входящее сообщение пользователя в шаблон промпта.
    """
    if not template:
        logger.error("Шаблон промпта памяти пуст.")
        return f"Профиль:\n{profile_text}\n\nПредыдущие сообщения:\n{history_text}\n\nНовое сообщение пользователя:\n{user_text}"

    return (
        template.replace("{USER_PROFILE_INFO}", profile_text or "Информация о пользователе пока неизвестна.")
        .replace("{PREVIOUS_10_MESSAGES}", history_text)
        .replace("{LATEST_USER_MESSAGE}", user_text)
    )


async def get_memory(user_text: str, chat_id: int) -> str:
    """
    Основной пайплайн памяти:
    1. Запрашивает профиль пользователя из user_info.
    2. Запрашивает последние сообщения чата из базы данных.
    3. Извлекает последние 10 сообщений.
    4. Форматирует историю и подставляет профиль в шаблон промпта памяти.
    5. Генерирует и возвращает ответ ассистента.
    """
    try:
        user_info: dict[str, Any] | None = await db.get_user_info()
    except Exception as e:
        logger.error(f"Ошибка при получении профиля пользователя из базы данных: {e}")
        user_info = None

    profile_text: str = format_user_profile(user_info)

    # Долгосрочная память: факты, которые Kez узнал о пользователе из разговоров
    from app.backend.piplines.start.facts import format_user_facts
    facts_text: str = format_user_facts(await db.get_user_facts())
    if facts_text:
        profile_text = f"{profile_text}\n\n{facts_text}"

    try:
        messages: list[dict[str, Any]] = await db.get_chat_messages(chat_id)
    except Exception as e:
        logger.error(f"Ошибка при получении истории чата {chat_id} из базы данных: {e}")
        messages = []

    # Берём до 10 последних сообщений в хронологическом порядке
    messages_latest: list[dict[str, Any]] = messages[-10:] if len(messages) > 10 else messages
    formatted_history: str = format_chat_history(messages_latest)

    prompt_template: str = PROMPTS.get("memory", "")
    if not prompt_template:
        logger.warning("Промпт 'memory' не найден в PROMPTS, пробуем загрузить напрямую из файла.")
        try:
            memory_prompt_path: Path = PROMPTS_DIR / "memory.txt"
            if memory_prompt_path.exists():
                with open(memory_prompt_path, "r", encoding="utf-8") as f:
                    prompt_template = f.read().strip()
        except Exception as e:
            logger.error(f"Не удалось прочитать файл промпта памяти: {e}")

    final_prompt: str = build_memory_prompt(prompt_template, formatted_history, user_text, profile_text)

    return await generate_response_with_fallback(final_prompt)


async def get_memory_stream(user_text: str, chat_id: int):
    """
    Потоковый пайплайн памяти (стриминг):
    1. Запрашивает профиль пользователя из базы.
    2. Извлекает последние 10 сообщений.
    3. Подставляет всё в промпт памяти.
    4. Выдает чанки ответа через асинхронный генератор.
    """
    try:
        user_info: dict[str, Any] | None = await db.get_user_info()
    except Exception as e:
        logger.error(f"Ошибка при получении профиля пользователя из БД: {e}")
        user_info = None

    profile_text: str = format_user_profile(user_info)

    # Долгосрочная память: факты, которые Kez узнал о пользователе из разговоров
    from app.backend.piplines.start.facts import format_user_facts
    facts_text: str = format_user_facts(await db.get_user_facts())
    if facts_text:
        profile_text = f"{profile_text}\n\n{facts_text}"

    try:
        messages: list[dict[str, Any]] = await db.get_chat_messages(chat_id)
    except Exception as e:
        logger.error(f"Ошибка при получении истории чата {chat_id} из БД: {e}")
        messages = []

    messages_latest: list[dict[str, Any]] = messages[-10:] if len(messages) > 10 else messages
    formatted_history: str = format_chat_history(messages_latest)

    prompt_template: str = PROMPTS.get("memory", "")
    if not prompt_template:
        try:
            memory_prompt_path: Path = PROMPTS_DIR / "memory.txt"
            if memory_prompt_path.exists():
                with open(memory_prompt_path, "r", encoding="utf-8") as f:
                    prompt_template = f.read().strip()
        except Exception as e:
            logger.error(f"Не удалось прочитать memory.txt: {e}")

    final_prompt: str = build_memory_prompt(prompt_template, formatted_history, user_text, profile_text)

    from app.backend.utils.llm_fallback import generate_stream_with_fallback
    async for chunk in generate_stream_with_fallback(final_prompt):
        yield chunk


    

