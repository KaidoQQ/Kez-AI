import sys
import os
import asyncio
import qasync
from PyQt6.QtWidgets import QApplication
from app.frontend.main_window import KezMainWindow
from core.loader import db
from core.logger import logger

async def startup() -> None:
    try:
        await db.connect()
        await db.create_tables()
        logger.info("Database connected and tables verified.")
    except Exception as e:
        logger.error(f"Startup failed: {e}")

def main() -> None:
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Загружаем QSS стили
    style_path = os.path.join(os.path.dirname(__file__), "app", "frontend", "style.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    else:
        print(f"Warning: stylesheet not found at {style_path}")
        
    window = KezMainWindow()
    window.show()
    
    loop.create_task(startup())
    
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()
