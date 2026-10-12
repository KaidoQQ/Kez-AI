import json
import random
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from google import genai
from core.logger import logger
from core.const import (
    MODELS_FALLBACK,
    PROMPTS,
    PROMPTS_DIR,
    PHOTO_PATTERNS,
    FILE_PATTERNS,
    WEB_SEARCH_PATTERNS,
    QUICK_CONVERSATION_RESPONSES,
)
from Kez.prepare import _get_client


class IntentType(str, Enum):
    """Типы интентов для маршрутизации запросов пользователя."""
    CHAT = "chat"               # Обычный разговор, диалог
    WEB_SEARCH = "web_search"   # Поиск информации в интернете
    PHOTO = "photo"             # Запрос на создание / генерацию фото
    FILE = "file"               # Запрос на создание, сохранение или работу с файлом


@dataclass
class RoutingResult:
    """Результат работы маршрутизатора."""
    intent: IntentType
    confidence: float
    extracted_data: dict[str, Any]


def classify_intent_by_rules(text: str) -> RoutingResult | None:
    """
    Быстрая классификация интента по правилам и ключевым словам без обращения к сети.
    Возвращает RoutingResult при уверенном совпадении или None.
    """
    cleaned_text: str = text.strip()
    if not cleaned_text:
        return RoutingResult(intent=IntentType.CHAT, confidence=1.0, extracted_data={})

    # Сначала проверяем быстрые разговорные фразы (привет, как дела, кто ты и т.д.)
    for pattern, responses in QUICK_CONVERSATION_RESPONSES:
        if pattern.search(cleaned_text):
            chosen_reply: str = random.choice(responses)
            logger.info(f"Сработало мгновенное правило диалога Kez: '{cleaned_text}'")
            return RoutingResult(
                intent=IntentType.CHAT,
                confidence=1.0,
                extracted_data={"direct_reply": chosen_reply}
            )

    for pattern in PHOTO_PATTERNS:
        match = pattern.search(cleaned_text)
        if match:
            prompt_query: str = cleaned_text[match.end():].strip(" :,-")
            return RoutingResult(
                intent=IntentType.PHOTO,
                confidence=0.95,
                extracted_data={"prompt": prompt_query or cleaned_text}
            )

    for pattern in FILE_PATTERNS:
        match = pattern.search(cleaned_text)
        if match:
            return RoutingResult(
                intent=IntentType.FILE,
                confidence=0.95,
                extracted_data={"raw_request": cleaned_text}
            )

    for pattern in WEB_SEARCH_PATTERNS:
        match = pattern.search(cleaned_text)
        if match:
            query_part: str = cleaned_text[match.end():].strip(" :,-")
            return RoutingResult(
                intent=IntentType.WEB_SEARCH,
                confidence=0.95,
                extracted_data={"query": query_part or cleaned_text}
            )

    return None


def get_routing_prompt_template() -> str:
    """
    Возвращает шаблон промпта роутинга из PROMPTS или напрямую из файла.
    """
    template: str = PROMPTS.get("routing", "")
    if template:
        return template

    logger.warning("Промпт 'routing' не найден в PROMPTS, пробуем загрузить из файла.")
    try:
        routing_file: Path = PROMPTS_DIR / "routing.txt"
        if routing_file.exists():
            with open(routing_file, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception as e:
        logger.error(f"Не удалось прочитать файл промпта роутинга: {e}")

    logger.error("Файл промпта роутинга не найден, используется аварийный шаблон.")
    return (
        "Classify intent as JSON: {\"intent\": \"chat\"|\"web_search\"|\"photo\"|\"file\", "
        "\"confidence\": 0.8, \"extracted_data\": {}}\nMessage: {USER_MESSAGE}"
    )


async def classify_intent_by_llm(text: str) -> RoutingResult:
    """
    Классификация интента через Gemini API с fallback-моделями для сложных/неоднозначных запросов.
    """
    try:
        client: genai.Client = _get_client()
    except Exception as e:
        logger.error(f"Не удалось получить Gemini клиент для роутинга: {e}")
        return RoutingResult(intent=IntentType.CHAT, confidence=0.5, extracted_data={})

    template: str = get_routing_prompt_template()
    prompt: str = template.replace("{USER_MESSAGE}", text)

    for model_name in MODELS_FALLBACK:
        try:
            logger.info(f"Роутинг через модель {model_name}...")
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if response and response.text:
                raw_response: str = response.text.strip()
                cleaned_json: str = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_response, flags=re.MULTILINE).strip()
                parsed_data: dict[str, Any] = json.loads(cleaned_json)

                intent_str: str = str(parsed_data.get("intent", "chat")).lower()
                valid_intents: dict[str, IntentType] = {i.value: i for i in IntentType}
                resolved_intent: IntentType = valid_intents.get(intent_str, IntentType.CHAT)

                confidence_val: float = float(parsed_data.get("confidence", 0.8))
                extracted_info: dict[str, Any] = parsed_data.get("extracted_data", {})
                if not isinstance(extracted_info, dict):
                    extracted_info = {}

                logger.info(f"Успешный роутинг моделью {model_name}: {resolved_intent.value}")
                return RoutingResult(
                    intent=resolved_intent,
                    confidence=confidence_val,
                    extracted_data=extracted_info
                )
            logger.warning(f"Модель {model_name} вернула пустой ответ при роутинге.")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON ответа роутера ({model_name}): {e}")
        except Exception as e:
            logger.error(f"Ошибка при вызове модели {model_name} в роутере: {e}")

    logger.warning("Все fallback-модели роутера не сработали. Возвращен дефолтный интент CHAT.")
    return RoutingResult(intent=IntentType.CHAT, confidence=0.5, extracted_data={})


async def route_intent(user_text: str) -> RoutingResult:
    """
    Главная точка входа пайплайна роутинга:
    1. Сначала пробует быструю классификацию по правилам (0 мс задержки).
    2. Если интент неоднозначен, передаёт запрос LLM.
    """
    rule_result: RoutingResult | None = classify_intent_by_rules(user_text)
    if rule_result is not None:
        logger.info(f"Интент определен по правилам: {rule_result.intent.value} (уверенность: {rule_result.confidence})")
        return rule_result

    logger.info(f"Интент не определен правилами, отправка на анализ LLM: '{user_text}'")
    return await classify_intent_by_llm(user_text)
