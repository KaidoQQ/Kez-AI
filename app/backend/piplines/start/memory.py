from pathlib import Path
from typing import Any

from google import genai
from core.loader import db
from core.logger import logger
from core.const import PROMPTS, MODELS_FALLBACK, PROMPTS_DIR
from Kez.prepare import _get_client


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


def build_memory_prompt(template: str, history_text: str, user_text: str) -> str:
    """
    Подставляет историю сообщений и входящее сообщение пользователя в шаблон промпта.
    """
    if not template:
        logger.error("Шаблон промпта памяти пуст.")
        return f"Предыдущие сообщения:\n{history_text}\n\nНовое сообщение пользователя:\n{user_text}"

    return (
        template.replace("{PREVIOUS_10_MESSAGES}", history_text)
        .replace("{LATEST_USER_MESSAGE}", user_text)
    )


async def generate_response_with_fallback(prompt: str) -> str:
    """
    Отправляет промпт в Gemini API с перебором fallback-моделей.
    """
    try:
        client: genai.Client = _get_client()
    except Exception as e:
        logger.error(f"Не удалось инициализировать клиент Gemini: {e}")
        return ""

    for model_name in MODELS_FALLBACK:
        try:
            logger.info(f"Попытка генерации ответа через модель {model_name}...")
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if response and response.text:
                logger.info(f"Успешный ответ от модели {model_name}.")
                return response.text.strip()
            logger.warning(f"Модель {model_name} вернула пустой ответ.")
        except Exception as e:
            logger.error(f"Ошибка при вызове модели {model_name}: {e}")

    logger.error("Все доступные fallback-модели не смогли сгенерировать ответ.")
    return ""


async def get_memory(user_text: str, chat_id: int) -> str:
    """
    Основной пайплайн памяти:
    1. Запрашивает последние сообщения чата из базы данных.
    2. Извлекает последние 10 сообщений.
    3. Форматирует историю и подставляет в шаблон промпта памяти.
    4. Генерирует и возвращает ответ ассистента.
    """
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

    final_prompt: str = build_memory_prompt(prompt_template, formatted_history, user_text)

    return await generate_response_with_fallback(final_prompt)

    

