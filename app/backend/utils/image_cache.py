import os
import time
from pathlib import Path
from core.logger import logger
from core.constants.image_const import CACHE_IMAGES_DIR, CACHE_EXPIRATION_SECONDS


def ensure_cache_directories() -> Path:
    """
    Создает директорию кэша изображений, если она еще не создана.
    Возвращает объект Path к директории кэша.
    """
    try:
        CACHE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        return CACHE_IMAGES_DIR
    except Exception as e:
        logger.error(f"Не удалось создать директорию кэша изображений {CACHE_IMAGES_DIR}: {e}")
        raise


def cleanup_expired_cache(max_age_seconds: int = CACHE_EXPIRATION_SECONDS) -> int:
    """
    Проверяет файлы в кэше изображений и удаляет те, возраст которых превышает max_age_seconds (по умолчанию 7 дней).
    Возвращает количество удаленных файлов.
    """
    deleted_count: int = 0
    try:
        if not CACHE_IMAGES_DIR.exists():
            return 0

        current_time: float = time.time()
        for item in CACHE_IMAGES_DIR.iterdir():
            if item.is_file():
                try:
                    file_stat = item.stat()
                    file_age: float = current_time - file_stat.st_mtime
                    if file_age > max_age_seconds:
                        item.unlink(missing_ok=True)
                        deleted_count += 1
                        logger.info(f"Удален устаревший файл из кэша: {item.name} (возраст: {int(file_age // 86400)} дн.)")
                except Exception as file_err:
                    logger.error(f"Ошибка при проверке/удалении файла {item.name}: {file_err}")

        if deleted_count > 0:
            logger.info(f"Очистка кэша завершена: удалено {deleted_count} файлов.")
    except Exception as e:
        logger.error(f"Ошибка при очистке кэша изображений: {e}")

    return deleted_count
