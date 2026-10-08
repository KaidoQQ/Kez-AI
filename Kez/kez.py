from google import genai
from google.genai.errors import APIError
from core.logger import logger
from core.const import MODELS_FALLBACK, PROMPTS
from Kez.prepare import _load_all_prompts, _get_client

class KezAgent:
    def __init__(self, api: str,):
        #TODO написть стартовые функции для начала работы с кезом
        self.prompts = PROMPTS
        self.models = MODELS_FALLBACK
        self.security = PROMPTS.get("lg_secur")

    async def get_normal_prompt(prompt: str) -> str | None:
        match prompt:
            case "foto":
                ...
            case "micro":
                ...
            case "msg":
                ...
            case "web":
                ...
            case _:
                logger.error("Промпт не удалось определить")