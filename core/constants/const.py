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

PROMPTS_DIR: Path = Path(__file__).resolve().parent.parent.parent / "Kez" / "prompts"
if not PROMPTS_DIR.exists():
    PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

class _LocalizedPrompts(dict):
    """
    Словарь промптов, который при чтении подставляет язык по умолчанию ({DEFAULT_LANGUAGE})
    из текущих настроек — смена языка в настройках действует сразу, без перезагрузки промптов.
    """

    def __getitem__(self, key: str) -> str:
        from core.i18n import localize_prompt
        return localize_prompt(super().__getitem__(key))

    def get(self, key: str, default: str = "") -> str:
        return self[key] if key in self else default


PROMPTS: dict[str, str] = _LocalizedPrompts(_load_all_prompts(PROMPTS_DIR))

# Паттерны для фото
PHOTO_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(сделай|создай|сгенерируй|нарисуй|покажи)\s+(фото|картинк|изображени|арт|пикчу|снимок)", re.IGNORECASE),
    re.compile(r"\b(фотографи|нарисуй|сгенерируй фото|сделай фото)\b", re.IGNORECASE),
    re.compile(r"\b(generate photo|draw picture|create image|draw a|generate image)\b", re.IGNORECASE),
]

# Паттерны для напоминаний и таймеров
REMINDER_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(напомни|напомнить|поставь таймер|заведи таймер|поставь будильник|установи таймер)\b", re.IGNORECASE),
    re.compile(r"\b(мои напоминания|какие напоминания|список напоминаний)\b", re.IGNORECASE),
    re.compile(r"\b(remind me|set a timer|set timer|set an alarm|my reminders)\b", re.IGNORECASE),
]

# Паттерны редактирования изображения (ссылка на «эту/последнюю» картинку + глагол изменения)
IMAGE_EDIT_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"\b(сделай|измени|перерисуй|переделай|добавь|убери|раскрась|поменяй|преврати)\b.{0,40}?"
        r"\b(эт\w*|последн\w*|прошл\w*|предыдущ\w*)\s+(рисун\w*|картин\w*|фото\w*|изображени\w*|арт\w*)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(эт\w*|последн\w*)\s+(рисун\w*|картин\w*|фото\w*|изображени\w*)\b.{0,40}?"
        r"\b(сделай|измени|перерисуй|переделай|добавь|убери|раскрась|поменяй|преврати|в стиле)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(edit|change|restyle|redraw)\s+(this|that|the last)\s+(image|picture|photo|drawing)\b", re.IGNORECASE),
]

# Глаголы редактирования — для запросов с прикреплённой картинкой
IMAGE_EDIT_VERBS_PATTERN: re.Pattern = re.compile(
    r"\b(сделай|измени|перерисуй|переделай|добавь|убери|раскрась|поменяй|преврати|в стиле|edit|change|restyle|redraw|make it)\b",
    re.IGNORECASE,
)

# Паттерны для файлов
FILE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(сохрани|экспортируй|запиши|выгрузи|сделай|создай)\s+(в\s+)?(файл|документ|таблиц\w*|отч[её]т|презентаци\w*|txt|pdf|csv|json|docx|xlsx|pptx|excel|word)\b", re.IGNORECASE),
    re.compile(r"\b(сохрани|экспортируй|выгрузи)\b.{0,40}\b(в|to)\s+(pdf|txt|docx|xlsx|pptx|excel|word|ворд|эксел\w*|markdown|md)\b", re.IGNORECASE),
    re.compile(r"\b(прикрепи файл|скинь файл|открой файл|прочитай файл)\b", re.IGNORECASE),
    re.compile(r"\b(save to file|export to|create file|save file|read file|make a presentation|create a spreadsheet)\b", re.IGNORECASE),
]

# Паттерны для веб-поиска
WEB_SEARCH_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(найди в инете|найди в интернете|погугли|загугли|поиск в сети|поищи в интернете)\b", re.IGNORECASE),
    re.compile(r"\b(новости\s+(сегодня|вчера|за неделю|за последний)|свежие новости|курс (доллара|евро|биткоина|валют))\b", re.IGNORECASE),
    re.compile(r"\b(search online|google this|find on the web|look up online|latest news)\b", re.IGNORECASE),
]

# Быстрые шаблоны с готовыми ответами в стиле Kez (птичий стиль)
# Мгновенный ответ без задержки и обращения к LLM
# Мгновенные ответы: отвечаем на языке сообщения пользователя (ключи 'ru' / 'en')
QUICK_CONVERSATION_RESPONSES: list[tuple[re.Pattern, dict[str, list[str]]]] = [
    (
        re.compile(r"^(привет|хай|ку|здравствуй|здравствуйте|добрый день|добрый вечер|доброе утро|салам|йоу|hello|hi|hey)\b[\s!.,?~]*$", re.IGNORECASE),
        {
            "ru": [
                "Чирик-чирик! 🐦 Привет, мой пернатый друг! Как твоё настроение сегодня?",
                "Фррр-чик! Приветик! Я тут как раз чистил перышки. Что у нас на повестке дня?",
                "Чирик! Рад тебя слышать! О чём пощебечем сегодня? ✨",
            ],
            "en": [
                "Chirp-chirp! 🐦 Hello, my feathered friend! How are you feeling today?",
                "Frrr-chik! Hi there! I was just preening my feathers. What's on the agenda today?",
                "Chirp! Glad to hear from you! What shall we chirp about today? ✨",
            ],
        }
    ),
    (
        re.compile(r"^(как дела|как ты|как жизнь|как поживаешь|что нового|как делишки|how are you|how is it going)\b[\s!.,?~]*$", re.IGNORECASE),
        {
            "ru": [
                "Всё чик-чирик! 🐦 Гнёздышко тёплое, пёрышки начищены, готов к любым интересным задачкам! А ты как сам?",
                "Чирик! Настроение парить под облаками! Как твои успехи сегодня?",
                "Пока не поймал самого вкусного цифрового червячка, но полон энергии! Что у тебя новенького?",
            ],
            "en": [
                "All chirpy! 🐦 The nest is warm, the feathers are polished, and I'm ready for any interesting task! How about you?",
                "Chirp! I'm in a soaring-above-the-clouds mood! How is your day going?",
                "I haven't caught the tastiest digital worm yet, but I'm full of energy! What's new with you?",
            ],
        }
    ),
    (
        re.compile(r"^(кто ты|ты кто|расскажи о себе|что ты такое|как тебя зовут|who are you)\b[\s!.,?~]*$", re.IGNORECASE),
        {
            "ru": [
                "Я Kez — твоя верная цифровая птица и умный AI-компаньон! 🐦 Умею общаться, искать всё в интернете, помнить наш разговор и поднимать настроение. Чирик!",
                "Чирик! Я Kez — пернатый ассистент прямо на твоём экране. Помогаю с делами, ищу информацию и всегда готов поддержать беседу! ✨",
            ],
            "en": [
                "I'm Kez — your loyal digital bird and smart AI companion! 🐦 I can chat, search the web, remember our conversations and lift your mood. Chirp!",
                "Chirp! I'm Kez — a feathered assistant right on your screen. I help with tasks, find information and I'm always up for a chat! ✨",
            ],
        }
    ),
    (
        re.compile(r"^(откуда ты|где ты живешь|где твой дом|где ты родился|where are you from)\b[\s!.,?~]*$", re.IGNORECASE),
        {
            "ru": [
                "Я родом из облачных серверов и аккуратных строчек кода, но моё самое уютное гнёздышко — прямо здесь, в твоём приложении! 🐦",
                "Мои крылья летают по цифровым проводам, а свиваю гнездо прямо у тебя на экране! Чирик! ✨",
            ],
            "en": [
                "I come from cloud servers and neat lines of code, but my coziest nest is right here in your app! 🐦",
                "My wings fly along digital wires, and I build my nest right on your screen! Chirp! ✨",
            ],
        }
    ),
    (
        re.compile(r"^(спасибо|благодарю|пасиб|от души|спасибочки|thx|thanks|thank you)\b[\s!.,?~]*$", re.IGNORECASE),
        {
            "ru": [
                "Всегда рад помочь! Почеши за ушком и обращайся ещё! ✨ Чирик!",
                "Чирик-чирик! Не за что, для хорошего друга мне никаких зёрнышек не жалко! 🐦",
                "На здоровье! Если понадобится что-то ещё — я тут рядышком! 🌟",
            ],
            "en": [
                "Always happy to help! Come back any time! ✨ Chirp!",
                "Chirp-chirp! You're welcome — I'd share all my seeds with a good friend! 🐦",
                "My pleasure! If you need anything else, I'm right here! 🌟",
            ],
        }
    ),
]

ONBOARDING_FINAL_GREETING: str = (
    "Чирик-чирик! 🐦 Ура! Теперь мы официально знакомы, {full_name}! ✨\n\n"
    "Я запомнил, что твой возраст/год: {birth_val}, а твои интересы — {interests}. "
    "Моё гнёздышко настроено специально под тебя! О чём хочешь поговорить или что для тебя найти в интернете?"
)


WEEKDAYS_RU: list[str] = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

# Единицы времени для «через N ...» / «на N ...»
TIME_UNITS: list[tuple[str, str]] = [
    (r"сек\w*|sec\w*|s\b", "seconds"),
    (r"мин\w*|min\w*|m\b", "minutes"),
    (r"час\w*|hour\w*|h\b", "hours"),
    (r"дн\w*|день|дня|day\w*|d\b", "days"),
]
NUMBER_WORDS: dict[str, int] = {
    "одну": 1, "один": 1, "одна": 1, "две": 2, "два": 2, "три": 3, "четыре": 4, "пять": 5,
    "десять": 10, "пятнадцать": 15, "двадцать": 20, "тридцать": 30, "полчаса": 30,
}

_NUMBER: str = r"\d+(?:[.,]\d+)?|" + "|".join(NUMBER_WORDS)
_UNIT: str = "|".join(u for u, _ in TIME_UNITS)
# «через минуту» — число необязательно; «на 5 минут» — обязательно (иначе «подарок на день рождения»)
RELATIVE_PATTERN: re.Pattern = re.compile(
    rf"\b(?:через|in)\s+(?:(?P<amount>{_NUMBER})\s*)?(?P<unit>{_UNIT})"
    rf"|\b(?:на|for)\s+(?P<amount2>{_NUMBER})\s*(?P<unit2>{_UNIT})",
    re.IGNORECASE,
)
HALF_HOUR_PATTERN: re.Pattern = re.compile(r"\b(?:через|на)\s+полчаса\b", re.IGNORECASE)
CLOCK_PATTERN: re.Pattern = re.compile(r"\b(?:в|at)\s+(\d{1,2})[:.](\d{2})\b|\b(?:в|at)\s+(\d{1,2})\s*(?:час\w*)?\b", re.IGNORECASE)
TOMORROW_PATTERN: re.Pattern = re.compile(r"\b(завтра|tomorrow)\b", re.IGNORECASE)
CLEANUP_PATTERN: re.Pattern = re.compile(
    r"\b(эй,?\s*)?(kez|кез)?,?\s*(напомни|напомнить|поставь|заведи|установи|remind|set)\s*(мне|me)?\s*"
    r"|\b(таймер|будильник|timer|alarm)\b|\b(что|чтобы|о том,? что|про|about|to)\b",
    re.IGNORECASE,
)