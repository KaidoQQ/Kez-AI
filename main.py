import sys
import os
from PyQt6.QtWidgets import QApplication
from app.frontend.main_window import KezMainWindow

def main():
    app = QApplication(sys.argv)
    
    # Загружаем QSS стили
    style_path = os.path.join(os.path.dirname(__file__), "app", "frontend", "style.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    else:
        print(f"Warning: stylesheet not found at {style_path}")
        
    window = KezMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
