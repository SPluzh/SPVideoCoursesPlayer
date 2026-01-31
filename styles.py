from pathlib import Path

# Path to dark.qss file
DARK_QSS_PATH = Path(__file__).parent / "resources" / "styles" / "dark.qss"

# ==========================
# DARK_STYLE (for compatibility)
# ==========================
try:
    DARK_STYLE = DARK_QSS_PATH.read_text(encoding="utf-8")
except Exception:
    DARK_STYLE = ""  # If file missing, empty style

# ==========================
# Style Manager
# ==========================
class StyleManager:
    """Application style manager."""
    
    @staticmethod
    def get_style(path: Path = DARK_QSS_PATH) -> str:
        """Reads style from file."""
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    @staticmethod
    def apply_style(app, path: Path = DARK_QSS_PATH):
        """Applies style to application."""
        qss = StyleManager.get_style(path)
        if qss:
            app.setStyleSheet(qss)
