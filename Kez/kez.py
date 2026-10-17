from typing import Any, AsyncGenerator
from dataclasses import dataclass

from google import genai
from core.logger import logger
from core.constants.const import MODELS_FALLBACK, PROMPTS
from Kez.prepare import _get_client
from app.backend.piplines.start.routing import route_intent, IntentType, RoutingResult
from app.backend.piplines.start.memory import get_memory, get_memory_stream
from app.backend.piplines.start.web_search import web_search
from app.backend.piplines.start.image_gen import generate_image, ImageGenerationResult


@dataclass
class StreamEvent:
    """Событие потокового ответа агента."""
    event_type: str  # 'token' | 'image' | 'error' | 'done'
    text: str = ""
    image_path: str = ""
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

    async def generate_reply_stream(self, user_text: str, chat_id: int) -> AsyncGenerator[StreamEvent, None]:
        """
        Главный потоковый метод обработки сообщения пользователя:
        1. Определяет намерение через пайплайн роутинга (route_intent).
        2. Если CHAT -> стримит чанки ответа по словам/токенам.
        3. Если PHOTO -> запускает пайплайн генерации изображений и выдает StreamEvent(event_type='image').
        4. Если WEB_SEARCH / FILE -> выполняет задачу и выдает чанки/событие.
        """
        try:
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
                    yield StreamEvent(event_type="token", text=f"📁 [File]: Запрос на обработку файла: '{raw_req}'. Пайплайн файловой обработки в разработке.")

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
            elif event.text:
                collected_parts.append(event.text)
        return "".join(collected_parts)