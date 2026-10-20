from pathlib import Path

from core.constants.image_const import FRONTEND_CACHE_DIR

# Директории кэша файлов и аудио
CACHE_AUDIO_DIR: Path = FRONTEND_CACHE_DIR / "audio"
CACHE_FILES_DIR: Path = FRONTEND_CACHE_DIR / "files"   # вставленные из буфера обмена изображения
MAX_ATTACHMENTS: int = 5

# Ограничения анализа файлов
MAX_INLINE_FILE_BYTES: int = 18 * 1024 * 1024   # Лимит inline-запроса Gemini (~20 МБ)
MAX_TEXT_FILE_CHARS: int = 200_000

# Файлы, которые Gemini принимает нативно (байтами)
NATIVE_MIME_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
}

# Текстовые файлы, читаемые напрямую
TEXT_FILE_EXTENSIONS: set[str] = {
    ".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml", ".ini", ".toml",
    ".log", ".html", ".htm", ".css", ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".cpp",
    ".h", ".cs", ".go", ".rs", ".php", ".rb", ".sql", ".sh", ".bat", ".ps1",
}

DOCX_EXTENSIONS: set[str] = {".docx"}

# Форматы экспорта
EXPORT_FORMATS: tuple[str, ...] = ("pdf", "md", "txt", "docx", "xlsx", "pptx")
DEFAULT_EXPORT_FORMAT: str = "md"

# Голос: модели синтеза речи и параметры PCM-потока Gemini TTS
TTS_MODELS: list[str] = [
    "gemini-2.5-flash-preview-tts",
    "gemini-2.5-pro-preview-tts",
]
TTS_VOICE_NAME: str = "Puck"
TTS_VOICES: list[str] = ["Puck", "Kore", "Zephyr", "Charon", "Fenrir", "Leda", "Aoede", "Orus"]
TTS_SAMPLE_RATE: int = 24000
TTS_MAX_CHARS: int = 1500
