from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFrame, QLabel, QPushButton
from PyQt6.QtCore import Qt
from translator import tr

from constants import RESOURCES_DIR

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
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(30, 40, 30, 30)
        container_layout.setSpacing(15)
        
        # Title
        title = QLabel(tr('app.title'))
        title.setObjectName("aboutTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(title)
        
        # Version
        version_text = self.get_app_version()
        version = QLabel(tr('about.version', version=version_text))
        version.setObjectName("aboutVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(version)
        
        # Separator
        line = QFrame()
        line.setObjectName("aboutSeparator")
        line.setFrameShape(QFrame.Shape.HLine)
        container_layout.addWidget(line)
        
        # Description
        desc = QLabel(tr('about.description'))
        desc.setObjectName("aboutDescription")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        container_layout.addWidget(desc)
        
        container_layout.addSpacing(10)
        
        # Close Button
        close_btn = QPushButton(tr('about.close'))
        close_btn.setObjectName("aboutCloseBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedWidth(120)
        close_btn.clicked.connect(self.accept)
        container_layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.container)

    def center_window(self):
        if self.parent():
            parent_geo = self.parent().frameGeometry()
            self_geo = self.frameGeometry()
            self_geo.moveCenter(parent_geo.center())
            self.move(self_geo.topLeft())
