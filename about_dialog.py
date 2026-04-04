from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
    QGridLayout,
)
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
        self.container.setFixedWidth(900)  # Make window wider
        self.container.setFixedHeight(750)  # Increase height

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(25, 30, 25, 25)
        container_layout.setSpacing(12)

        # Title
        title = QLabel(tr("app.title"))
        title.setObjectName("aboutTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(title)

        # Version
        version_text = self.get_app_version()
        version = QLabel(tr("about.version", version=version_text))
        version.setObjectName("aboutVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(version)

        # Description
        desc = QLabel(tr("about.description"))
        desc.setObjectName("aboutDescription")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        container_layout.addWidget(desc)

        # Hotkeys Section
        hotkey_title = QLabel(tr("hotkeys.title"))
        hotkey_title.setObjectName("aboutHotkeyTitle")
        hotkey_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(hotkey_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("aboutHotkeyScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )  # Enable scrollbar when needed

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
        close_btn = QPushButton(tr("about.close"))
        close_btn.setObjectName("aboutCloseBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedWidth(120)
        close_btn.clicked.connect(self.accept)
        container_layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.container)

    def populate_hotkeys(self, layout):
        # Structure: [(category_key, [(key, desc), ...]), ...]
        categories = [
            (
                "category_playback",
                [
                    (tr("hotkeys.keys.space"), tr("hotkeys.toggle_pause")),
                    (
                        "← / →",
                        f"{tr('hotkeys.seek_backward')} / {tr('hotkeys.seek_forward')}",
                    ),
                    (",", tr("hotkeys.frame_back")),
                    (".", tr("hotkeys.frame_step")),
                    (f"{tr('hotkeys.keys.shift')} + ←", tr("hotkeys.prev_video")),
                    (f"{tr('hotkeys.keys.shift')} + →", tr("hotkeys.next_video")),
                ],
            ),
            (
                "category_audio",
                [
                    ("M", tr("hotkeys.toggle_mute")),
                    (f"{tr('hotkeys.keys.shift')} + ↑", tr("hotkeys.volume_up")),
                    (f"{tr('hotkeys.keys.shift')} + ↓", tr("hotkeys.volume_down")),
                    (f"{tr('hotkeys.keys.shift')} + ,", tr("hotkeys.audio_delay_down")),
                    (f"{tr('hotkeys.keys.shift')} + .", tr("hotkeys.audio_delay_up")),
                    ("↑ / ↓", f"{tr('hotkeys.speed_up')} / {tr('hotkeys.speed_down')}"),
                ],
            ),
            (
                "category_video",
                [
                    ("R", tr("hotkeys.reset_zoom")),
                    ("Z", tr("hotkeys.zoom_mode")),
                    ("[", tr("hotkeys.zoom_out")),
                    ("]", tr("hotkeys.zoom_in")),
                    ("C", tr("hotkeys.toggle_subtitles")),
                    ("S", tr("hotkeys.take_screenshot")),
                ],
            ),
            (
                "category_bookmarks",
                [
                    ("B", tr("hotkeys.add_marker")),
                    ("G", tr("hotkeys.toggle_marker_gallery")),
                ],
            ),
            (
                "category_library",
                [
                    ("Ctrl + L", tr("hotkeys.toggle_library")),
                    ("L", tr("hotkeys.locate_video")),
                    ("E", tr("hotkeys.expand_tree")),
                    ("W", tr("hotkeys.collapse_tree")),
                ],
            ),
            (
                "category_window",
                [
                    ("F", tr("hotkeys.toggle_fullscreen")),
                    ("P", tr("hotkeys.toggle_pip")),
                    ("ESC", tr("hotkeys.exit_fullscreen_or_pip")),
                    ("T", tr("hotkeys.toggle_always_on_top")),
                ],
            ),
            (
                "category_system",
                [
                    ("Ctrl + R", tr("hotkeys.rescan")),
                    ("Ctrl + ,", tr("hotkeys.open_settings")),
                ],
            ),
            (
                "category_mouse",
                [
                    ("Mouse L-Click", tr("hotkeys.mouse_play_pause")),
                    ("Mouse 2x L-Click", tr("hotkeys.mouse_fullscreen")),
                    ("Mouse R-Click (PIP)", tr("hotkeys.mouse_pip_move")),
                ],
            ),
        ]

        row = 0
        for category_key, hotkeys in categories:
            # Category title
            category_label = QLabel(tr(f"hotkeys.{category_key}"))
            category_label.setObjectName("hotkeyCategoryTitle")
            category_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(category_label, row, 0, 1, 6)  # span 6 columns
            row += 1

            # Separator line
            separator = QFrame()
            separator.setObjectName("hotkeyCategorySeparator")
            separator.setFrameShape(QFrame.Shape.HLine)
            layout.addWidget(separator, row, 0, 1, 6)
            row += 1

            # Hotkeys in 3 columns
            start_row = row
            for i, (key, desc) in enumerate(hotkeys):
                col = (i % 3) * 2
                current_row = start_row + (i // 3)

                # Key container
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
                desc_label.setAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )

                layout.addWidget(key_container, current_row, col)
                layout.addWidget(desc_label, current_row, col + 1)

            # Move to next category
            row = start_row + ((len(hotkeys) - 1) // 3) + 1
            row += 1  # Extra spacing between categories

    def center_window(self):
        if self.parent():
            parent_geo = self.parent().frameGeometry()
            self_geo = self.frameGeometry()
            self_geo.moveCenter(parent_geo.center())
            self.move(self_geo.topLeft())
