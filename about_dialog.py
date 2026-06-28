from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QApplication,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon
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
        """Load version from version.txt or return default"""
        try:
            version_file = Path(__file__).parent / "resources" / "version.txt"
            if version_file.exists():
                return version_file.read_text("utf-8").strip()
        except Exception:
            pass
        return "1.0"

    def setup_ui(self):
        # Main layout with dark background
        layout = QVBoxLayout(self)

        # Container frame
        self.container = QFrame()
        self.container.setObjectName("aboutContainer")

        container_layout = QVBoxLayout(self.container)
        container_layout.setSpacing(15)

        # Title (App Name + Version)
        app_title = tr("app.title")
        version_text = self.get_app_version()
        
        title = QLabel(f"{app_title} {version_text}")
        title.setObjectName("aboutTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(title)

        # GitHub and Feedback Links Layout
        links_layout = QHBoxLayout()
        links_layout.setContentsMargins(0, 0, 0, 0)
        links_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # GitHub Link Group
        github_link_group = QHBoxLayout()
        github_link_group.setSpacing(5)

        # Icon Label
        github_icon_label = QLabel()
        github_icon_path = str(RESOURCES_DIR / "icons" / "github.png")
        github_icon_label.setPixmap(QIcon(github_icon_path).pixmap(16, 16))
        github_link_group.addWidget(github_icon_label)

        # Text Label
        github_text_label = QLabel(tr("about.github"))
        github_text_label.setObjectName("aboutGithubLink")
        github_text_label.setCursor(Qt.CursorShape.PointingHandCursor)
        github_text_label.mousePressEvent = lambda e: self.open_github()
        github_link_group.addWidget(github_text_label)

        links_layout.addLayout(github_link_group)

        links_layout.addSpacing(15)

        # Feedback Link Group
        feedback_link_group = QHBoxLayout()
        feedback_link_group.setSpacing(5)

        # Icon Label
        feedback_icon_label = QLabel()
        feedback_icon_label.setPixmap(QIcon(github_icon_path).pixmap(16, 16))
        feedback_link_group.addWidget(feedback_icon_label)

        # Text Label
        feedback_text_label = QLabel(tr("about.feedback"))
        feedback_text_label.setObjectName("aboutGithubLink")
        feedback_text_label.setCursor(Qt.CursorShape.PointingHandCursor)
        feedback_text_label.mousePressEvent = lambda e: self.open_feedback()
        feedback_link_group.addWidget(feedback_text_label)

        links_layout.addLayout(feedback_link_group)
        container_layout.addLayout(links_layout)

        # Separator Line
        line = QFrame()
        line.setObjectName("aboutSeparator")
        line.setFrameShape(QFrame.Shape.HLine)
        container_layout.addWidget(line)

        # Description
        desc = QLabel(tr("about.description"))
        desc.setObjectName("aboutDescription")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        container_layout.addWidget(desc)

        # Hotkeys columns layout
        self.build_hotkeys_columns(container_layout)

        container_layout.addSpacing(5)

        # Close Button
        close_btn = QPushButton(tr("about.close"))
        close_btn.setObjectName("aboutCloseBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedWidth(120)
        close_btn.clicked.connect(self.accept)
        container_layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.container)

    def build_hotkeys_columns(self, container_layout):
        # General hotkeys title
        hotkeys_title = QLabel(tr("hotkeys.title"))
        hotkeys_title.setObjectName("aboutHotkeyTitle")
        hotkeys_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(hotkeys_title)

        # Columns layout
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(30)
        columns_layout.setContentsMargins(0, 0, 0, 0)

        # Left Column
        left_column = QVBoxLayout()
        left_column.setSpacing(4)
        left_column.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Right Column
        right_column = QVBoxLayout()
        right_column.setSpacing(4)
        right_column.setAlignment(Qt.AlignmentFlag.AlignTop)

        categories = [
            (
                "category_playback",
                [
                    (tr("hotkeys.keys.space"), tr("hotkeys.toggle_pause")),
                    (
                        "← / →",
                        f"{tr('hotkeys.seek_backward')} / {tr('hotkeys.seek_forward')}",
                    ),
                    ("0-9 / Numpad 0-9", f"{tr('hotkeys.seek_to_0')} - {tr('hotkeys.seek_to_90')}"),
                    (",", tr("hotkeys.frame_back")),
                    (".", tr("hotkeys.frame_step")),
                    (f"{tr('hotkeys.keys.shift')} + ←", tr("hotkeys.prev_video")),
                    (f"{tr('hotkeys.keys.shift')} + →", tr("hotkeys.next_video")),
                ],
            ),
            (
                "category_subtitles",
                [
                    ("C", tr("hotkeys.toggle_subtitles")),
                    (f"{tr('hotkeys.keys.alt')} + ←", tr("hotkeys.prev_phrase")),
                    (f"{tr('hotkeys.keys.alt')} + →", tr("hotkeys.next_phrase")),
                    (f"{tr('hotkeys.keys.alt')} + ↓", tr("hotkeys.replay_phrase")),
                    (f"{tr('hotkeys.keys.alt')} + ↑", tr("hotkeys.translate_subtitle")),
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
                    ("Ctrl + M", tr("hotkeys.toggle_mass_selection")),
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

        # Distribute: Left column gets Playback, Subtitles, Audio, Video. Right column gets Bookmarks, Library, Window, System, Mouse.
        left_cats = categories[:4]
        right_cats = categories[4:]

        for col_layout, cats in [(left_column, left_cats), (right_column, right_cats)]:
            for idx, (category_key, hotkeys) in enumerate(cats):
                # Category title
                category_label = QLabel(tr(f"hotkeys.{category_key}"))
                category_label.setObjectName("hotkeyCategoryTitle")
                category_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                col_layout.addWidget(category_label)

                # Format hotkeys text
                hotkey_lines = []
                for key, desc in hotkeys:
                    hotkey_lines.append(f"{key}  —  {desc}")
                
                content_label = QLabel("\n".join(hotkey_lines))
                content_label.setObjectName("aboutSectionContent")
                content_label.setWordWrap(True)
                content_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                col_layout.addWidget(content_label)

                # Spacing between categories (add spacing if not the last item in this column)
                if idx < len(cats) - 1:
                    col_layout.addSpacing(6)

        columns_layout.addLayout(left_column, 1)
        columns_layout.addLayout(right_column, 1)
        container_layout.addLayout(columns_layout)

    def center_window(self):
        if self.parent():
            parent_geo = self.parent().frameGeometry()
            self_geo = self.frameGeometry()
            self_geo.moveCenter(parent_geo.center())
            self.move(self_geo.topLeft())
        else:
            screen = QApplication.primaryScreen().geometry()
            self_geo = self.frameGeometry()
            self_geo.moveCenter(screen.center())
            self.move(self_geo.topLeft())

    def open_github(self):
        """Open project GitHub repository in default browser"""
        QDesktopServices.openUrl(QUrl("https://github.com/SPluzh/SPVideoCoursesPlayer"))

    def open_feedback(self):
        """Open project feedback page in default browser"""
        QDesktopServices.openUrl(QUrl("https://github.com/SPluzh/SPVideoCoursesPlayer/issues"))
