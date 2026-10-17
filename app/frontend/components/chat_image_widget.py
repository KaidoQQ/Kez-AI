import os
from pathlib import Path
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QContextMenuEvent, QAction, QGuiApplication
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QMenu, QFileDialog, QMessageBox, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QColor
from core.logger import logger


class ChatImageWidget(QWidget):
    """
    Виджет карточки сгенерированного изображения:
    - Скругленные края и аккуратная тень
    - Контекстное меню по правому клику мыши:
        1. 'Скопировать' (копирует картинку в буфер обмена)
        2. 'Скачать' (диалог сохранения файла в выбранную папку)
    """

    def __init__(self, image_path: str, prompt: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.image_path: str = image_path
        self.prompt: str = prompt
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self.image_label = QLabel()
        self.image_label.setObjectName("chat_image_label")
        self.image_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pixmap = QPixmap(self.image_path)
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                460, 460,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setFixedSize(scaled_pixmap.size())
        else:
            self.image_label.setText("🖼 [Не удалось загрузить изображение]")
            self.image_label.setStyleSheet("color: #EF4444; padding: 20px;")

        self.image_label.setStyleSheet("""
            QLabel#chat_image_label {
                border-radius: 12px;
                border: 1px solid rgba(240, 234, 218, 0.2);
                background-color: #0F172A;
            }
        """)

        layout.addWidget(self.image_label)
        self.setLayout(layout)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """
        Контекстное меню по правому клику мыши: 'Скопировать' и 'Скачать'.
        """
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid rgba(240, 234, 218, 0.2);
                border-radius: 8px;
                padding: 4px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #38BDF8;
                color: #0F172A;
                font-weight: 600;
            }
        """)

        copy_action: QAction = menu.addAction("📋 Скопировать")
        save_action: QAction = menu.addAction("💾 Скачать...")

        action = menu.exec(self.mapToGlobal(event.pos()))
        if action == copy_action:
            self.copy_image_to_clipboard()
        elif action == save_action:
            self.save_image_as()

    def copy_image_to_clipboard(self) -> None:
        """Копирует изображение в системный буфер обмена."""
        try:
            pixmap = QPixmap(self.image_path)
            if not pixmap.isNull():
                clipboard = QGuiApplication.clipboard()
                clipboard.setPixmap(pixmap)
                logger.info(f"Изображение скопировано в буфер обмена: {self.image_path}")
            else:
                logger.warning(f"Не удалось скопировать невалидное изображение: {self.image_path}")
        except Exception as e:
            logger.error(f"Ошибка при копировании изображения в буфер: {e}")

    def save_image_as(self) -> None:
        """Открывает диалог сохранения файла в выбранную пользователем папку."""
        try:
            default_name: str = Path(self.image_path).name or "kez_generated.png"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить сгенерированное изображение",
                default_name,
                "Изображения (*.png *.jpg *.webp)"
            )
            if file_path:
                pixmap = QPixmap(self.image_path)
                saved_successfully: bool = pixmap.save(file_path)
                if saved_successfully:
                    logger.info(f"Изображение успешно сохранено в {file_path}")
                else:
                    logger.error(f"Не удалось сохранить изображение в {file_path}")
                    QMessageBox.warning(self, "Ошибка сохранения", "Не удалось сохранить файл на диск.")
        except Exception as e:
            logger.error(f"Ошибка в диалоге сохранения изображения: {e}")
