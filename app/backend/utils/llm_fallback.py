"""Shared utility for interacting with Gemini API models with automatic fallback chain."""

from google import genai
from core.logger import logger
from core.constants.const import MODELS_FALLBACK
from Kez.prepare import _get_client


async def generate_response_with_fallback(prompt: str) -> str:
    """
    Отправляет промпт в Gemini API с перебором fallback-моделей.
    
    :param prompt: Текст промпта для модели.
    :return: Сгенерированный строковый ответ либо пустая строка при ошибке.
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


async def generate_stream_with_fallback(prompt: str | list):
    """
    Асинхронный генератор для потоковой передачи ответа модели (стриминг).
    prompt может быть строкой или списком частей (текст + файлы/аудио).
    Перебирает fallback-модели в случае сбоя при запуске стрима.
    Выдает чанки текста (str).
    """
    try:
        client: genai.Client = _get_client()
    except Exception as e:
        logger.error(f"Не удалось инициализировать клиент Gemini для стриминга: {e}")
        return

    for model_name in MODELS_FALLBACK:
        try:
            logger.info(f"Попытка стриминг-генерации через модель {model_name}...")
            response_stream = await client.aio.models.generate_content_stream(
                model=model_name,
                contents=prompt,
            )
            got_any_chunk: bool = False
            async for chunk in response_stream:
                if chunk and chunk.text:
                    got_any_chunk = True
                    yield chunk.text

            if got_any_chunk:
                logger.info(f"Стриминг успешно завершен через модель {model_name}.")
                return
            logger.warning(f"Модель {model_name} не вернула текстовых чанков в стриме.")
        except Exception as e:
            logger.error(f"Ошибка стриминга через модель {model_name}: {e}")

    logger.error("Все fallback-модели завершились ошибкой при стриминге.")

