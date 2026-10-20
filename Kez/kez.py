import asyncio
import re
from pathlib import Path
from typing import Any, AsyncGenerator
from dataclasses import dataclass

from google import genai
from core.logger import logger
from core.constants.const import MODELS_FALLBACK, PROMPTS, IMAGE_EDIT_VERBS_PATTERN
from core.loader import db
from Kez.prepare import _get_client
from app.backend.piplines.start.routing import route_intent, IntentType, RoutingResult
from app.backend.piplines.start.memory import get_memory, get_memory_stream
from app.backend.piplines.start.web_search import web_search
from app.backend.piplines.start.image_gen import generate_image, edit_image, ImageGenerationResult, IMAGE_EDIT_MIME_TYPES
from app.backend.piplines.start.reminders import create_reminder_from_request
from app.backend.piplines.start.facts import extract_and_store_facts
from app.backend.utils.markers import find_last_image
from app.backend.piplines.start.file_processing import (
    analyze_file_stream,
    export_file_from_request,
    is_read_request,
    FileExportResult,
)


# «Сделай описание этой картинки» — это анализ, а не редактирование
DESCRIBE_REQUEST_PATTERN: re.Pattern = re.compile(
    r"(опиши|описани|что на|что тут|расскажи|прочитай|распознай|describe|what is|what's)", re.IGNORECASE
)


@dataclass
class StreamEvent:
    """Событие потокового ответа агента."""
    event_type: str  # 'token' | 'image' | 'file' | 'error' | 'done'
    text: str = ""
    image_path: str = ""
    file_path: str = ""
    prompt: str = ""


class KezAgent:
    """
    Класс-оркестратор Kez AI Companion:
    Управляет сессией модели, роутингом намерений и передачей задач в специализированные пайплайны.
    Поддерживает как классический ответ (generate_reply), так и потоковый стриминг (generate_reply_stream).
    """

    def __init__(self) -> None:
        try:
            self.kez: genai.Client = _get_client()
        except Exception as e:
            logger.error(f"Не удалось инициализировать клиент Gemini в KezAgent: {e}")
            self.kez = None

        self.prompts: dict[str, str] = PROMPTS
        self.models: list[str] = MODELS_FALLBACK
        self.security: str | None = PROMPTS.get("lg.protect") or PROMPTS.get("lg_secur")
        # Ссылки на фоновые задачи (извлечение фактов), чтобы их не собрал GC
        self._background_tasks: set[asyncio.Task] = set()

    def _learn_facts_in_background(self, user_text: str) -> None:
        """Запускает извлечение фактов о пользователе, не задерживая ответ."""
        task: asyncio.Task = asyncio.create_task(extract_and_store_facts(user_text))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _edit_image_events(self, source_path: str, instruction: str, chat_id: int) -> AsyncGenerator[StreamEvent, None]:
        yield StreamEvent(event_type="token", text="🖌️ Чирик! Беру кисточку и перерисовываю... ✨\n")
        edit_res: ImageGenerationResult = await edit_image(source_path, instruction, chat_id)
        if edit_res.success and edit_res.image_path:
            yield StreamEvent(
                event_type="image",
                image_path=edit_res.image_path,
                prompt=instruction,
                text="Готово! Вот обновлённая версия. 🐦🎨"
            )
        else:
            yield StreamEvent(event_type="token", text=f"\n❌ {edit_res.error_message}")

    async def generate_reply_stream(
        self, user_text: str, chat_id: int, attachment_paths: list[str] | str | None = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Главный потоковый метод обработки сообщения пользователя:
        1. Определяет намерение через пайплайн роутинга (route_intent).
        2. Если CHAT -> стримит чанки ответа по словам/токенам.
        3. Если PHOTO -> запускает пайплайн генерации изображений и выдает StreamEvent(event_type='image').
        4. Если WEB_SEARCH / FILE -> выполняет задачу и выдает чанки/событие.
        5. Если REMINDER -> создаёт напоминание; IMAGE_EDIT -> перерисовывает последнюю картинку.
        """
        if isinstance(attachment_paths, str):
            attachment_paths = [attachment_paths]
        attachments: list[str] = list(attachment_paths or [])

        try:
            if attachments:
                # Одна картинка + просьба её изменить -> редактирование изображения
                single: Path = Path(attachments[0])
                if (
                    len(attachments) == 1
                    and single.suffix.lower() in IMAGE_EDIT_MIME_TYPES
                    and IMAGE_EDIT_VERBS_PATTERN.search(user_text)
                    and not DESCRIBE_REQUEST_PATTERN.search(user_text)
                ):
                    async for event in self._edit_image_events(str(single), user_text, chat_id):
                        yield event
                    return

                # Остальные вложения уходят в пайплайн анализа, минуя роутер
                logger.info(f"KezAgent (Stream) анализирует вложения: {attachments}")
                async for chunk in analyze_file_stream(attachments, user_text):
                    yield StreamEvent(event_type="token", text=chunk)
                return

            self._learn_facts_in_background(user_text)

            decision: RoutingResult = await route_intent(user_text)
            logger.info(f"KezAgent (Stream) получил интент: {decision.intent.value} (уверенность: {decision.confidence})")

            match decision.intent:
                case IntentType.CHAT:
                    direct_reply: str | None = decision.extracted_data.get("direct_reply")
                    if direct_reply:
                        yield StreamEvent(event_type="token", text=direct_reply)
                        return

                    stream_failed: bool = True
                    async for chunk in get_memory_stream(user_text, chat_id):
                        stream_failed = False
                        yield StreamEvent(event_type="token", text=chunk)

                    if stream_failed:
                        # Fallback к обычному вызову если стрим ничего не отдал
                        logger.warning("Стрим не вернул чанков, пробуем стандартный generate_reply.")
                        fallback_text: str = await get_memory(user_text, chat_id)
                        yield StreamEvent(event_type="token", text=fallback_text)

                case IntentType.PHOTO:
                    image_prompt: str = str(decision.extracted_data.get("prompt", user_text))
                    logger.info(f"Интент PHOTO в стриме: промпт '{image_prompt}'")
                    yield StreamEvent(event_type="token", text="🎨 Чирик! Настраиваю палитру и рисую... Это займет пару секунд! ✨\n")

                    img_res: ImageGenerationResult = await generate_image(image_prompt, chat_id)
                    if img_res.success and img_res.image_path:
                        yield StreamEvent(
                            event_type="image",
                            image_path=img_res.image_path,
                            prompt=img_res.original_prompt,
                            text=f"Вот твой рисунок по запросу: «{img_res.original_prompt}»! 🐦🎨"
                        )
                    else:
                        err_text: str = img_res.error_message or "Не удалось нарисовать картинку... Попробуй ещё разок!"
                        yield StreamEvent(event_type="token", text=f"\n❌ {err_text}")

                case IntentType.WEB_SEARCH:
                    search_query: str = str(decision.extracted_data.get("query", user_text))
                    logger.info(f"Интент WEB_SEARCH: поисковый запрос '{search_query}'")
                    search_result: str = await web_search(search_query)
                    yield StreamEvent(event_type="token", text=search_result)

                case IntentType.FILE:
                    raw_req: str = str(decision.extracted_data.get("raw_request", user_text))
                    logger.info(f"Интент FILE: работа с файлом '{raw_req}'")
                    if is_read_request(raw_req):
                        yield StreamEvent(
                            event_type="token",
                            text="📎 Чирик! Прикрепи файл через кнопку со скрепкой слева от поля ввода и напиши, что с ним сделать — я прочитаю! 🐦"
                        )
                        return

                    yield StreamEvent(event_type="token", text="📝 Чирик! Собираю документ по пёрышку... ✨\n")
                    export_res: FileExportResult = await export_file_from_request(raw_req, chat_id)
                    if export_res.success:
                        yield StreamEvent(
                            event_type="file",
                            file_path=export_res.file_path,
                            text=f"Готово! Документ ({export_res.export_format.upper()}) сохранён. 🐦📄"
                        )
                    else:
                        yield StreamEvent(event_type="token", text=f"\n❌ {export_res.error_message}")

                case IntentType.REMINDER:
                    raw_reminder: str = str(decision.extracted_data.get("raw_request", user_text))
                    reminder_reply: str = await create_reminder_from_request(raw_reminder, chat_id)
                    yield StreamEvent(event_type="token", text=reminder_reply)

                case IntentType.IMAGE_EDIT:
                    instruction: str = str(decision.extracted_data.get("instruction", user_text))
                    last_image: str | None = find_last_image(await db.get_chat_messages(chat_id))
                    if not last_image:
                        yield StreamEvent(
                            event_type="token",
                            text="Хм, в этом чате ещё нет картинок. 🐦 Попроси меня что-нибудь нарисовать или прикрепи изображение скрепкой!"
                        )
                        return
                    async for event in self._edit_image_events(last_image, instruction, chat_id):
                        yield event

                case _:
                    logger.warning(f"Неизвестный интент {decision.intent}, откат к диалогу с памятью.")
                    async for chunk in get_memory_stream(user_text, chat_id):
                        yield StreamEvent(event_type="token", text=chunk)

        except Exception as e:
            logger.error(f"Ошибка в generate_reply_stream KezAgent: {e}")
            yield StreamEvent(event_type="error", text="Ой, у меня что-то пошло не так при обработке сообщения... Чирик! 🐦")

    async def generate_reply(self, user_text: str, chat_id: int) -> str:
        """
        Классический синхронный метод обработки сообщения (сборка из стрима).
        """
        collected_parts: list[str] = []
        async for event in self.generate_reply_stream(user_text, chat_id):
            if event.event_type == "image":
                collected_parts.append(f"\n[IMAGE:{event.image_path}]\n{event.text}")
            elif event.event_type == "file":
                collected_parts.append(f"\n[FILE:{event.file_path}]\n{event.text}")
            elif event.text:
                collected_parts.append(event.text)
        return "".join(collected_parts)