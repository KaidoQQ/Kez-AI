import os
from pathlib import Path
import re
from typing import Pattern

from dotenv import load_dotenv
from core.logger import logger
from Kez.prepare import _load_all_prompts

# Список актуальных моделей с префиксом models/
MODELS_FALLBACK: list[str] = [
    "models/gemini-2.5-flash",
    "models/gemini-3.5-flash",
    "models/gemini-2.5-flash-lite",
    "models/gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

AI: str | None = os.getenv("GEMINI_API_KEY")

PROMPTS_DIR: Path = Path(__file__).resolve().parent.parent / "Kez" / "prompts"
if not PROMPTS_DIR.exists():
    PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

PROMPTS: dict[str, str] = _load_all_prompts(PROMPTS_DIR)

# Паттерны для фото
PHOTO_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(сделай|создай|сгенерируй|нарисуй|покажи)\s+(фото|картинк|изображени|арт|пикчу|снимок)", re.IGNORECASE),
    re.compile(r"\b(фотографи|нарисуй|сгенерируй фото|сделай фото)\b", re.IGNORECASE),
    re.compile(r"\b(generate photo|draw picture|create image|draw a|generate image)\b", re.IGNORECASE),
]

# Паттерны для файлов
FILE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(сохрани|экспортируй|запиши|выгрузи|сделай|создай)\s+(в\s+)?(файл|документ|таблиц|отчет|txt|pdf|csv|json)\b", re.IGNORECASE),
    re.compile(r"\b(прикрепи файл|скинь файл|открой файл|прочитай файл)\b", re.IGNORECASE),
    re.compile(r"\b(save to file|export to|create file|save file|read file)\b", re.IGNORECASE),
]

# Паттерны для веб-поиска
WEB_SEARCH_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(найди в инете|найди в интернете|погугли|загугли|поиск в сети|поищи в интернете)\b", re.IGNORECASE),
    re.compile(r"\b(новости\s+(сегодня|вчера|за неделю|за последний)|свежие новости|курс (доллара|евро|биткоина|валют))\b", re.IGNORECASE),
    re.compile(r"\b(search online|google this|find on the web|look up online|latest news)\b", re.IGNORECASE),
]

# Быстрые шаблоны с готовыми ответами в стиле Kez (птичий стиль)
# Мгновенный ответ без задержки и обращения к LLM
QUICK_CONVERSATION_RESPONSES: list[tuple[re.Pattern, list[str]]] = [
    (
        re.compile(r"^(привет|хай|ку|здравствуй|здравствуйте|добрый день|добрый вечер|доброе утро|салам|йоу|hello|hi|hey)\b[\s!.,?~]*$", re.IGNORECASE),
        [
            "Чирик-чирик! 🐦 Привет, мой пернатый друг! Как твоё настроение сегодня?",
            "Фррр-чик! Приветик! Я тут как раз чистил перышки. Что у нас на повестке дня?",
            "Чирик! Рад тебя слышать! О чём пощебечем сегодня? ✨",
        ]
    ),
    (
        re.compile(r"^(как дела|как ты|как жизнь|как поживаешь|что нового|как делишки|how are you|how is it going)\b[\s!.,?~]*$", re.IGNORECASE),
        [
            "Всё чик-чирик! 🐦 Гнёздышко тёплое, пёрышки начищены, готов к любым интересным задачкам! А ты как сам?",
            "Чирик! Настроение парить под облаками! Как твои успехи сегодня?",
            "Пока не поймал самого вкусного цифрового червячка, но полон энергии! Что у тебя новенького?",
        ]
    ),
    (
        re.compile(r"^(кто ты|ты кто|расскажи о себе|что ты такое|как тебя зовут|who are you)\b[\s!.,?~]*$", re.IGNORECASE),
        [
            "Я Kez — твоя верная цифровая птица и умный AI-компаньон! 🐦 Умею общаться, искать всё в интернете, помнить наш разговор и поднимать настроение. Чирик!",
            "Чирик! Я Kez — пернатый ассистент прямо на твоём экране. Помогаю с делами, ищу информацию и всегда готов поддержать беседу! ✨",
        ]
    ),
    (
        re.compile(r"^(откуда ты|где ты живешь|где твой дом|где ты родился|where are you from)\b[\s!.,?~]*$", re.IGNORECASE),
        [
            "Я родом из облачных серверов и аккуратных строчек кода, но моё самое уютное гнёздышко — прямо здесь, в твоём приложении! 🐦",
            "Мои крылья летают по цифровым проводам, а свиваю гнездо прямо у тебя на экране! Чирик! ✨",
        ]
    ),
    (
        re.compile(r"^(спасибо|благодарю|пасиб|от души|спасибочки|thx|thanks|thank you)\b[\s!.,?~]*$", re.IGNORECASE),
        [
            "Всегда рад помочь! Почеши за ушком и обращайся ещё! ✨ Чирик!",
            "Чирик-чирик! Не за что, для хорошего друга мне никаких зёрнышек не жалко! 🐦",
            "На здоровье! Если понадобится что-то ещё — я тут рядышком! 🌟",
        ]
    ),
]

ONBOARDING_FINAL_GREETING: str = (
    "Чирик-чирик! 🐦 Ура! Теперь мы официально знакомы, {full_name}! ✨\n\n"
    "Я запомнил, что твой возраст/год: {birth_val}, а твои интересы — {interests}. "
    "Моё гнёздышко настроено специально под тебя! О чём хочешь поговорить или что для тебя найти в интернете?"
)
