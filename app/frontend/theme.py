"""Application-wide theme and palette; safe to use before backend startup."""
from pathlib import Path
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

def apply_theme(theme: str) -> None:
    app = QApplication.instance()
    if app is None:
        return
    light = theme == "light"
    app.setStyle("Fusion")
    palette = QPalette()
    for role, color in {
        QPalette.ColorRole.Window: "#ffffff" if light else "#18181b",
        QPalette.ColorRole.Base: "#f4f4f5" if light else "#242427",
        QPalette.ColorRole.Text: "#202024" if light else "#f4f4f5",
        QPalette.ColorRole.WindowText: "#202024" if light else "#f4f4f5",
        QPalette.ColorRole.ButtonText: "#202024" if light else "#f4f4f5",
        QPalette.ColorRole.Highlight: "#7054c4" if light else "#a99af8",
    }.items():
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    name = "style_light.qss" if light else "style.qss"
    app.setStyleSheet((Path(__file__).parent / name).read_text(encoding="utf-8"))
