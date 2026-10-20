import asyncio
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google import genai
from core.logger import logger
from core.constants.const import PROMPTS, PROMPTS_DIR
from core.constants.image_const import (
    CACHE_IMAGES_DIR,
    FALLBACK_IMAGE_MODELS,
    DEFAULT_ASPECT_RATIO,
    DEFAULT_NUMBER_OF_IMAGES,
    DEFAULT_OUTPUT_MIME_TYPE,
)
from Kez.prepare import _get_client
from app.backend.utils.llm_fallback import generate_response_with_fallback
from app.backend.utils.image_cache import ensure_cache_directories


@dataclass
class ImageGenerationResult:
    """Результат генерации изображения."""
    success: bool
    image_path: str = ""
    original_prompt: str = ""
    enhanced_prompt: str = ""
    error_message: str = ""


def get_image_enhancement_template() -> str:
    """
    Загружает шаблон промпта для улучшения пользовательского описания картинки на английском языке.
    """
    template: str = PROMPTS.get("image_generation", "")
    if template:
        return template

    try:
        prompt_file: Path = PROMPTS_DIR / "image_generation.txt"
        if prompt_file.exists():
            with open(prompt_file, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception as e:
        logger.error(f"Не удалось прочитать image_generation.txt: {e}")

    return (
        "You are an expert prompt engineer. Expand this request into an ultra-detailed English image prompt "
        "for Google Imagen 3 (photorealistic/artistic, 8k, vibrant lighting). Return only the prompt:\n{USER_IMAGE_REQUEST}"
    )


async def enhance_image_prompt(raw_prompt: str) -> str:
    """
    Преобразует пользовательский запрос в детальный художественный промпт на английском языке.
    """
    try:
        template: str = get_image_enhancement_template()
        full_query: str = template.replace("{USER_IMAGE_REQUEST}", raw_prompt.strip())
        logger.info(f"Запуск улучшения промпта для Imagen: '{raw_prompt}'")
        enhanced: str = await generate_response_with_fallback(full_query)
        cleaned_prompt: str = enhanced.strip().strip('"').strip("'")
        if cleaned_prompt:
            logger.info(f"Улучшенный промпт: '{cleaned_prompt}'")
            return cleaned_prompt
    except Exception as e:
        logger.error(f"Ошибка при улучшении промпта для генерации: {e}")

    return raw_prompt


async def _generate_with_pollinations(prompt: str, saved_path: Path) -> bool:
    """
    Резервный высококачественный генератор изображений (Pollinations AI).
    Используется автоматически, если на ключе Google API исчерпана квота (429/404).
    """
    import urllib.parse
    import httpx
    try:
        logger.info(f"Запуск резервной генерации изображения через Pollinations AI...")
        encoded_prompt: str = urllib.parse.quote(prompt[:400])
        url: str = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&enhance=true"

        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as http_client:
            resp = await http_client.get(url)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(saved_path, "wb") as f:
                    f.write(resp.content)
                logger.info(f"Резервное изображение успешно сгенерировано и сохранено в {saved_path}")
                return True
            else:
                logger.warning(f"Pollinations вернул статус {resp.status_code}")
    except Exception as e:
        logger.error(f"Ошибка при вызове резервного генератора Pollinations: {e}")

    return False


async def generate_image(raw_prompt: str, chat_id: int | None = None) -> ImageGenerationResult:
    """
    Основной пайплайн генерации изображений:
    1. Улучшает и переводит промпт пользователя на детальный английский язык.
    2. Вызывает Google Gemini / Imagen API (с цепочкой fallback-моделей).
    3. При исчерпании квоты Google (429 / 404) автоматически подключает резервный генератор.
    4. Сохраняет результат в кэш фронтенда (`app/frontend/cache/images/`).
    5. Возвращает ImageGenerationResult.
    """
    try:
        ensure_cache_directories()
        client: genai.Client = _get_client()
    except Exception as e:
        logger.error(f"Не удалось инициализировать клиент или кэш для генерации изображений: {e}")
        return ImageGenerationResult(
            success=False,
            original_prompt=raw_prompt,
            error_message="Не удалось подключиться к сервису генерации изображений."
        )

    enhanced_prompt: str = await enhance_image_prompt(raw_prompt)

    timestamp_str: str = str(int(time.time()))
    unique_suffix: str = uuid.uuid4().hex[:6]
    chat_prefix: str = f"chat{chat_id}_" if chat_id else ""
    filename: str = f"{chat_prefix}{timestamp_str}_{unique_suffix}.png"
    saved_path: Path = CACHE_IMAGES_DIR / filename

    # 1. Попытка генерации через модели Google Gemini / Imagen
    for model_name in FALLBACK_IMAGE_MODELS:
        try:
            logger.info(f"Генерация фото через модель {model_name}...")
            
            # Если это модель семейства gemini-*-image (через generate_content)
            if "gemini" in model_name:
                response = await client.aio.models.generate_content(
                    model=model_name,
                    contents=enhanced_prompt,
                )
                if response and response.candidates:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, "inline_data") and part.inline_data:
                            img_bytes = part.inline_data.data
                            with open(saved_path, "wb") as f:
                                f.write(img_bytes)
                            logger.info(f"Изображение успешно получено от {model_name} и сохранено в {saved_path}")
                            return ImageGenerationResult(
                                success=True,
                                image_path=str(saved_path),
                                original_prompt=raw_prompt,
                                enhanced_prompt=enhanced_prompt,
                            )
            else:
                # Старый вызов generate_images для imagen
                result = await client.aio.models.generate_images(
                    model=model_name,
                    prompt=enhanced_prompt,
                    config=dict(
                        number_of_images=DEFAULT_NUMBER_OF_IMAGES,
                        output_mime_type=DEFAULT_OUTPUT_MIME_TYPE,
                        aspect_ratio=DEFAULT_ASPECT_RATIO,
                    ),
                )
                if result and result.generated_images:
                    gen_img = result.generated_images[0]
                    img_bytes: bytes = gen_img.image.image_bytes
                    with open(saved_path, "wb") as f:
                        f.write(img_bytes)

                    logger.info(f"Изображение успешно сгенерировано через {model_name} и сохранено в {saved_path}")
                    return ImageGenerationResult(
                        success=True,
                        image_path=str(saved_path),
                        original_prompt=raw_prompt,
                        enhanced_prompt=enhanced_prompt,
                    )
        except Exception as e:
            logger.warning(f"Модель {model_name} не смогла сгенерировать изображение: {e}")

    # 2. Если модели Google недоступны или лимит квоты исчерпан (Free Tier), подключаем резервный генератор
    logger.info("Активация надежного резервного генератора изображений...")
    pollinations_ok: bool = await _generate_with_pollinations(enhanced_prompt, saved_path)
    if pollinations_ok and saved_path.exists():
        return ImageGenerationResult(
            success=True,
            image_path=str(saved_path),
            original_prompt=raw_prompt,
            enhanced_prompt=enhanced_prompt,
        )

    logger.error("Все основные и резервные генераторы вернули ошибку.")
    return ImageGenerationResult(
        success=False,
        original_prompt=raw_prompt,
        enhanced_prompt=enhanced_prompt,
        error_message="К сожалению, не удалось создать изображение прямо сейчас. Попробуй изменить запрос!"
    )


IMAGE_EDIT_MIME_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


async def edit_image(source_path: str, instruction: str, chat_id: int | None = None) -> ImageGenerationResult:
    """
    Пайплайн редактирования изображения («сделай этот рисунок в стиле аниме»):
    отправляет исходную картинку + инструкцию в Gemini image-модели (генерация по изображению)
    и сохраняет результат в кэш фронтенда.
    """
    from google.genai import types

    source: Path = Path(source_path)
    mime_type: str | None = IMAGE_EDIT_MIME_TYPES.get(source.suffix.lower())
    if not source.is_file() or mime_type is None:
        return ImageGenerationResult(
            success=False,
            original_prompt=instruction,
            error_message="Не нашёл картинку для редактирования. Прикрепи изображение или сначала попроси меня что-нибудь нарисовать!"
        )

    try:
        ensure_cache_directories()
        client: genai.Client = _get_client()
    except Exception as e:
        logger.error(f"Не удалось инициализировать клиент для редактирования изображения: {e}")
        return ImageGenerationResult(success=False, original_prompt=instruction, error_message="Сервис изображений недоступен.")

    chat_prefix: str = f"chat{chat_id}_" if chat_id else ""
    saved_path: Path = CACHE_IMAGES_DIR / f"{chat_prefix}edit_{int(time.time())}_{uuid.uuid4().hex[:6]}.png"
    image_part = types.Part.from_bytes(data=source.read_bytes(), mime_type=mime_type)
    edit_prompt: str = (
        f"Edit this image according to the instruction, keep the main subject and composition recognizable. "
        f"Instruction: {instruction}"
    )

    for model_name in [m for m in FALLBACK_IMAGE_MODELS if "gemini" in m]:
        try:
            logger.info(f"Редактирование изображения через модель {model_name}...")
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=[image_part, edit_prompt],
                config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
            )
            if response and response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        saved_path.write_bytes(part.inline_data.data)
                        logger.info(f"Отредактированное изображение сохранено: {saved_path}")
                        return ImageGenerationResult(
                            success=True,
                            image_path=str(saved_path),
                            original_prompt=instruction,
                            enhanced_prompt=edit_prompt,
                        )
        except Exception as e:
            logger.warning(f"Модель {model_name} не смогла отредактировать изображение: {e}")

    return ImageGenerationResult(
        success=False,
        original_prompt=instruction,
        error_message="Не получилось перерисовать картинку — модели редактирования сейчас недоступны. Попробуй позже!"
    )
