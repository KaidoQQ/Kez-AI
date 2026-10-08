from pathlib import Path

from google import genai
from google.genai.errors import APIError
from core.logger import logger
from info.const import AI


async def _get_client() -> genai.Client:
    """Creates and returns a Gemini API client."""
    api_key = AI
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured. Add it to the .env file.")
    return genai.Client(api_key=api_key)

def _load_all_prompts(directory: Path) -> dict[str, str]:
    """
    Читает все .txt файлы из указанной директории и сохраняет их в словарь.
    """
    prompts_dict: dict[str, str] = {}
    
    if not directory.exists():
        logger.warning(f"Директория с промптами не найдена, создаю: {directory}")
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Не удалось создать директорию {directory}: {e}")
        return prompts_dict

    for filepath in directory.glob("*.txt"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                prompts_dict[filepath.stem] = f.read().strip()
        except Exception as e:
            logger.error(f"Ошибка при чтении промпта {filepath.name}: {e}")

    return prompts_dict
