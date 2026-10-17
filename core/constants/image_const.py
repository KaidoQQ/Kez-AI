import os
from pathlib import Path

# Директории кэша и медиа
FRONTEND_DIR: Path = Path(__file__).resolve().parent.parent.parent / "app" / "frontend"
FRONTEND_CACHE_DIR: Path = FRONTEND_DIR / "cache"
CACHE_IMAGES_DIR: Path = FRONTEND_CACHE_DIR / "images"

# Время жизни кэша изображений: 7 дней (в секундах)
CACHE_EXPIRATION_SECONDS: int = 7 * 24 * 60 * 60

# Модели генерации изображений
DEFAULT_IMAGE_MODEL: str = "gemini-2.5-flash-image"
FALLBACK_IMAGE_MODELS: list[str] = [
    "gemini-2.5-flash-image",
    "gemini-3.1-flash-image",
    "gemini-3-pro-image",
    "imagen-3.0-generate-002",
]

# Параметры генерации по умолчанию
DEFAULT_ASPECT_RATIO: str = "1:1"
DEFAULT_NUMBER_OF_IMAGES: int = 1
DEFAULT_OUTPUT_MIME_TYPE: str = "image/png"

