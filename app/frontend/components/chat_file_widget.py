import os
import shutil
from pathlib import Path
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox
from core.logger import logger
from core.i18n import tr

FILE_ICONS: dict[str, str] = {".pdf": "📕", ".md": "📝", ".txt": "📄"}


class ChatFileWidget(QWidget):
    """
    Карточка файла в чате (экспортированный документ):
    - Имя файла и папка
    - Кнопки 'Открыть', 'Папка' и 'Сохранить как...'
    """

    def __init__(self, file_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.file_path: str = file_path
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("chat_file_card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMaximumWidth(520)
        self.setStyleSheet("""
            QWidget#chat_file_card {
                background-color: #0F172A;
                border: 1px solid rgba(240, 234, 218, 0.2);
                border-radius: 12px;
            }
            QLabel { color: #F0EADA; background: transparent; border: none; }
            QLabel#file_dir_label { color: rgba(240, 234, 218, 0.55); font-size: 11px; }
            QPushButton {
                background-color: rgba(29, 43, 83, 220);
                color: #F0EADA;
                border: none;
                border-radius: 8px;
                padding: 5px 12px;
            }
            QPushButton:hover { background-color: rgba(39, 58, 113, 255); }
        """)

        path = Path(self.file_path)
        exists: bool = path.exists()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        icon: str = FILE_ICONS.get(path.suffix.lower(), "📁")
        name_label = QLabel(f"{icon}  <b>{path.name}</b>")
        name_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(name_label)

        dir_label = QLabel(str(path.parent) if exists else tr("file_card.moved"))
        dir_label.setObjectName("file_dir_label")
        layout.addWidget(dir_label)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        for title, handler in (
            (tr("file_card.open"), self._open_file),
            (tr("file_card.folder"), self._open_folder),
            (tr("file_card.save_as"), self._save_as),
        ):
            button = QPushButton(title)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setEnabled(exists)
            button.clicked.connect(handler)
            buttons_layout.addWidget(button)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

    def _open_file(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.file_path))

    def _open_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(self.file_path)))

    def _save_as(self) -> None:
        """Копирует файл в выбранную пользователем папку."""
        suffix: str = Path(self.file_path).suffix
        target, _ = QFileDialog.getSaveFileName(
            self, tr("file_card.save_dialog"), os.path.basename(self.file_path), f"*{suffix}"
        )
        if not target:
            return
        try:
            shutil.copyfile(self.file_path, target)
            logger.info(f"Документ сохранён пользователем в {target}")
        except Exception as e:
            logger.error(f"Не удалось сохранить документ в {target}: {e}")
            QMessageBox.warning(self, tr("file_card.error_title"), tr("file_card.error", error=e))
