from typing import Any

from google import genai
from core.logger import logger
from core.const import MODELS_FALLBACK, PROMPTS
from Kez.prepare import _get_client
from app.backend.piplines.start.routing import route_intent, IntentType, RoutingResult
from app.backend.piplines.start.memory import get_memory


class KezAgent:
    """
    Класс-оркестратор Kez AI Companion:
    Управляет сессией модели, роутингом намерений и передачей задач в специализированные пайплайны.
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

    async def generate_reply(self, user_text: str, chat_id: int) -> str:
        """
        Главный метод обработки сообщения пользователя:
        1. Определяет намерение через пайплайн роутинга (route_intent).
        2. Перенаправляет запрос в соответствующий пайплайн (память, веб-поиск, генерация фото, работа с файлом).
        """
        try:
            decision: RoutingResult = await route_intent(user_text)
            logger.info(f"KezAgent получил интент: {decision.intent.value} с уверенностью {decision.confidence}")

            match decision.intent:
                case IntentType.CHAT:
                    # Если сработал мгновенный ответ по правилам (привет, как дела, кто ты и т.д.)
                    direct_reply: str | None = decision.extracted_data.get("direct_reply")
                    if direct_reply:
                        return direct_reply

                    # Иначе запуск диалогового пайплайна с памятью последних 10 сообщений
                    return await get_memory(user_text, chat_id)

                case IntentType.WEB_SEARCH:
                    search_query: str = str(decision.extracted_data.get("query", user_text))
                    logger.info(f"Интент WEB_SEARCH: поисковый запрос '{search_query}'")
                    # Заглушка до реализации пайплайна DuckDuckGo поиска
                    return f"🔎 [Web Search]: Я поняла, что нужно поискать в интернете: '{search_query}'. Скоро здесь будет подключен поиск DuckDuckGo!"

                case IntentType.PHOTO:
                    image_prompt: str = str(decision.extracted_data.get("prompt", user_text))
                    logger.info(f"Интент PHOTO: промпт для генерации '{image_prompt}'")
                    # Заглушка до подключения пайплайна генерации изображений
                    return f"🎨 [Photo]: Запрос на создание фото: '{image_prompt}'. Подготовка пайплайна генерации изображений..."

                case IntentType.FILE:
                    raw_req: str = str(decision.extracted_data.get("raw_request", user_text))
                    logger.info(f"Интент FILE: работа с файлом '{raw_req}'")
                    # Заглушка до подключения пайплайна работы с файлами
                    return f"📁 [File]: Запрос на обработку файла: '{raw_req}'. Пайплайн файловой обработки в разработке."

                case _:
                    logger.warning(f"Неизвестный интент {decision.intent}, откат к диалогу с памятью.")
                    return await get_memory(user_text, chat_id)

        except Exception as e:
            logger.error(f"Ошибка в генерации ответа KezAgent: {e}")
            return "Ой, у меня что-то пошло не так при обработке сообщения... Чирик! 🐦"