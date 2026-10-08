import os
from pathlib import Path

from dotenv import load_dotenv
from core.logger import logger
from Kez.prepare import _load_all_prompts

MODELS_FALLBACK = [
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash"
]

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

AI = os.getenv("GEMINI_API_KEY")

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


PROMPTS: dict[str, str] = _load_all_prompts(PROMPTS_DIR)
