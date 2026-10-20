import sys
import os
import asyncio
import qasync
from PyQt6.QtWidgets import QApplication
from app.frontend.main_window import KezMainWindow
from core.loader import db
from core.logger import logger

async def startup(window: KezMainWindow) -> None:
    try:
        from app.backend.utils.image_cache import ensure_cache_directories, cleanup_expired_cache
        from core.constants.file_const import CACHE_AUDIO_DIR, CACHE_FILES_DIR
        ensure_cache_directories()
        deleted_cached_count: int = cleanup_expired_cache()
        cleanup_expired_cache(cache_dir=CACHE_AUDIO_DIR)
        cleanup_expired_cache(cache_dir=CACHE_FILES_DIR)
        if deleted_cached_count > 0:
            logger.info(f"Очищено {deleted_cached_count} устаревших изображений из кэша.")

        await db.connect()
        await db.create_tables()
        logger.info("Database connected and tables verified.")
        await window.load_initial_chat_session()
        window.start_background_services()
    except Exception as e:
        logger.error(f"Startup failed: {e}")

def main() -> None:
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    # Окно может прятаться в режим питомца — приложение живёт, пока не выбран «Выход»
    app.setQuitOnLastWindowClosed(True)

    # QSS-тема (тёмная/светлая) применяется внутри окна по настройкам пользователя
    window = KezMainWindow()
    window.show()
    
    loop.create_task(startup(window))
    
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()
