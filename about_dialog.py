from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFrame, QLabel, QPushButton, QScrollArea, QWidget, QGridLayout
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
        self.container.setFixedWidth(850) # Make window wider
        self.container.setFixedHeight(650) # Increase height
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(25, 30, 25, 25)
        container_layout.setSpacing(12)
        
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
                
        # Description
        desc = QLabel(tr('about.description'))
        desc.setObjectName("aboutDescription")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        container_layout.addWidget(desc)
        
        # Hotkeys Section
        hotkey_title = QLabel(tr('hotkeys.title'))
        hotkey_title.setObjectName("aboutHotkeyTitle")
        hotkey_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(hotkey_title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("aboutHotkeyScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # Disable scrollbar
        
        hotkey_widget = QWidget()
        hotkey_widget.setObjectName("hotkeyWidget")
        hotkey_layout = QGridLayout(hotkey_widget)
        hotkey_layout.setContentsMargins(5, 5, 5, 5)
        hotkey_layout.setSpacing(8)
        # 3 columns for hotkeys
        hotkey_layout.setColumnStretch(1, 1)
        hotkey_layout.setColumnStretch(3, 1)
        hotkey_layout.setColumnStretch(5, 1)
        
        self.populate_hotkeys(hotkey_layout)
        
        scroll.setWidget(hotkey_widget)
        container_layout.addWidget(scroll)
        
        container_layout.addSpacing(10)
        
        # Close Button
        close_btn = QPushButton(tr('about.close'))
        close_btn.setObjectName("aboutCloseBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedWidth(120)
        close_btn.clicked.connect(self.accept)
        container_layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.container)

    def populate_hotkeys(self, layout):
        hotkeys = [
            (tr('hotkeys.keys.space'), tr('hotkeys.toggle_pause')),
            ("Ctrl + R", tr('hotkeys.rescan')),
            ("Ctrl + L", tr('hotkeys.toggle_library')),
            ("Ctrl + ,", tr('hotkeys.open_settings')),
            ("F", tr('hotkeys.toggle_fullscreen')),
            ("M", tr('hotkeys.toggle_mute')),
            ("S", tr('hotkeys.take_screenshot')),
            ("C", tr('hotkeys.toggle_subtitles')),
            ("R", tr('hotkeys.reset_zoom')),
            ("Z", tr('hotkeys.zoom_mode')),
            ("[", tr('hotkeys.zoom_out')),
            ("]", tr('hotkeys.zoom_in')),
            (",", tr('hotkeys.frame_back')),
            (".", tr('hotkeys.frame_step')),
            ("B", tr('hotkeys.add_marker')),
            ("G", tr('hotkeys.toggle_marker_gallery')),
            ("T", tr('hotkeys.toggle_always_on_top')),
            ("L", tr('hotkeys.locate_video')),
            ("P", tr('hotkeys.toggle_pip')),
            (f"{tr('hotkeys.keys.shift')} + ←", tr('hotkeys.prev_video')),
            (f"{tr('hotkeys.keys.shift')} + →", tr('hotkeys.next_video')),
            (f"{tr('hotkeys.keys.shift')} + ↑", tr('hotkeys.volume_up')),
            (f"{tr('hotkeys.keys.shift')} + ↓", tr('hotkeys.volume_down')),
            (f"{tr('hotkeys.keys.shift')} + ,", tr('hotkeys.audio_delay_down')),
            (f"{tr('hotkeys.keys.shift')} + .", tr('hotkeys.audio_delay_up')),
            ("← / →", f"{tr('hotkeys.seek_backward')} / {tr('hotkeys.seek_forward')}"),
            ("↑ / ↓", f"{tr('hotkeys.speed_up')} / {tr('hotkeys.speed_down')}"),
            ("Mouse L-Click", tr('hotkeys.mouse_play_pause')),
            ("Mouse 2x L-Click", tr('hotkeys.mouse_fullscreen')),
            ("Mouse R-Click (PIP)", tr('hotkeys.mouse_pip_move')),
        ]

        for i, (key, desc) in enumerate(hotkeys):
            row = i // 3
            col = (i % 3) * 2
            
            key_container = QWidget()
            key_item_layout = QVBoxLayout(key_container)
            key_item_layout.setContentsMargins(0, 0, 0, 0)
            
            key_label = QLabel(key)
            key_label.setObjectName("hotkeyKey")
            key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            key_item_layout.addWidget(key_label)
            
            desc_label = QLabel(desc)
            desc_label.setObjectName("hotkeyDesc")
            desc_label.setWordWrap(True)
            desc_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            layout.addWidget(key_container, row, col)
            layout.addWidget(desc_label, row, col + 1)

    def center_window(self):
        if self.parent():
            parent_geo = self.parent().frameGeometry()
            self_geo = self.frameGeometry()
            self_geo.moveCenter(parent_geo.center())
            self.move(self_geo.topLeft())
