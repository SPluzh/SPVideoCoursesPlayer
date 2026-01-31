from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFrame, QLabel, QPushButton
from PyQt6.QtCore import Qt
from translator import tr

ROOT_DIR = Path(__file__).parent
RESOURCES_DIR = ROOT_DIR / "resources"

class AboutDialog(QDialog):
    """Custom About Dialog with dark theme"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setup_ui()

    def showEvent(self, event):
        self.adjustSize()
        self.center_window()
        super().showEvent(event)

    def get_app_version(self):
        try:
            version_file = RESOURCES_DIR / "version.txt"
            if version_file.exists():
                return version_file.read_text("utf-8").strip()
        except Exception:
            pass
        return "1.0.0"

    def setup_ui(self):
        # Main layout with dark background
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Container frame
        self.container = QFrame()
        self.container.setObjectName("aboutContainer")
        self.container.setStyleSheet("""
            QFrame#aboutContainer {
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 3px;
            }
            QLabel { color: #ccc; }
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(30, 40, 30, 30)
        container_layout.setSpacing(15)
        
        # Title
        title = QLabel(tr('app.title'))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        container_layout.addWidget(title)
        
        # Version
        version_text = self.get_app_version()
        version = QLabel(tr('about.version', version=version_text))
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet("font-size: 14px; color: #888; margin-bottom: 10px;")
        container_layout.addWidget(version)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #444;")
        container_layout.addWidget(line)
        
        # Description
        desc = QLabel(tr('about.description'))
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; line-height: 140%; margin: 10px 0;")
        container_layout.addWidget(desc)
        
        container_layout.addSpacing(10)
        
        # Close Button
        close_btn = QPushButton(tr('about.close'))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedWidth(120)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #555; }
            QPushButton:pressed { background-color: #333; }
        """)
        close_btn.clicked.connect(self.accept)
        container_layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.container)

    def center_window(self):
        if self.parent():
            parent_geo = self.parent().frameGeometry()
            self_geo = self.frameGeometry()
            self_geo.moveCenter(parent_geo.center())
            self.move(self_geo.topLeft())
