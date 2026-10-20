import json
import re
from typing import Any

from core.loader import db
from core.logger import logger
from core.constants.const import PROMPTS
from app.backend.utils.llm_fallback import generate_response_with_fallback

# Дешёвый предфильтр: LLM вызывается только если пользователь говорит о себе
SELF_DISCLOSURE_PATTERN: re.Pattern = re.compile(
    r"\b(я|мне|меня|мой|моя|моё|мое|мои|у меня|i|i'm|i am|my|me|mine)\b", re.IGNORECASE
)
MIN_MESSAGE_LENGTH: int = 12
MAX_FACT_LENGTH: int = 200


def should_extract_facts(user_text: str) -> bool:
    """True, если сообщение похоже на рассказ пользователя о себе."""
    text: str = user_text.strip()
    return len(text) >= MIN_MESSAGE_LENGTH and not text.endswith("?") and bool(SELF_DISCLOSURE_PATTERN.search(text))


def parse_facts_response(raw_response: str) -> list[str]:
    """Достаёт список фактов из JSON-ответа модели (терпимо к ```json-обёртке)."""
    cleaned: str = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_response.strip(), flags=re.MULTILINE).strip()
    try:
        data: Any = json.loads(cleaned)
    except json.JSONDecodeError:
        return []
    facts: Any = data.get("facts", []) if isinstance(data, dict) else []
    if not isinstance(facts, list):
        return []
    return [str(f).strip()[:MAX_FACT_LENGTH] for f in facts if str(f).strip()]


def format_user_facts(facts: list[dict[str, Any]]) -> str:
    """Форматирует факты для подстановки в профиль пользователя в промпте памяти."""
    if not facts:
        return ""
    lines: list[str] = [f"- {fact.get('fact', '')}" for fact in facts]
    return "Что Kez помнит о пользователе из прошлых разговоров:\n" + "\n".join(lines)


async def extract_and_store_facts(user_text: str) -> list[str]:
    """
    Фоновый пайплайн долгосрочной памяти:
    1. Предфильтр (сообщение о себе).
    2. LLM извлекает новые факты с учётом уже известных.
    3. Новые факты сохраняются в user_facts (дубликаты пропускаются).
    """
    from core.settings import settings
    if not settings.learn_facts or not should_extract_facts(user_text):
        return []

    known_facts: list[dict[str, Any]] = await db.get_user_facts()
    known_text: str = "\n".join(f"- {f['fact']}" for f in known_facts) or "(пока ничего)"

    template: str = PROMPTS.get("fact_extraction", "")
    if not template:
        logger.warning("Промпт 'fact_extraction' не найден, извлечение фактов пропущено.")
        return []

    prompt: str = template.replace("{KNOWN_FACTS}", known_text).replace("{USER_MESSAGE}", user_text)
    raw_response: str = await generate_response_with_fallback(prompt)
    new_facts: list[str] = parse_facts_response(raw_response)
    if new_facts:
        await db.add_user_facts(new_facts)
        logger.info(f"Kez запомнил новые факты: {new_facts}")
    return new_facts
