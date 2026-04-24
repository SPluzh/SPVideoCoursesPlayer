import sys
import os
import time
from pathlib import Path

from utils import setup_encoding

setup_encoding()

from constants import ROOT_DIR, RESOURCES_DIR, DATA_DIR

from mpv_handler import setup_mpv_dll, resolve_binary_path

setup_mpv_dll()
import locale

locale.setlocale(locale.LC_NUMERIC, "C")
from database import DatabaseManager
import json
import logging
from logging.handlers import RotatingFileHandler


# Configure logging with both file and console handlers
def setup_logging():
    """Setup logging to both file and console."""
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Clear any existing handlers
    logger.handlers.clear()

    # Console handler (always enabled)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (only if enabled in config)
    # Note: Config is not loaded yet at this point, so we check later in MainWindow
    # For now, just setup console logging


def enable_file_logging():
    """Enable file logging if configured."""
    # Determine log file location (next to exe or main.py)
    if getattr(sys, "frozen", False):
        # Running as compiled exe
        log_dir = Path(sys.executable).parent
    else:
        # Running as script
        log_dir = ROOT_DIR

    log_file = log_dir / "sp_video_player_debug.log"

    # Check if file handler already exists
    logger = logging.getLogger()
    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler):
            return  # Already enabled

    # Add file handler with rotation (10 MB max, 3 backups)
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        logging.info(f"✅ Debug file logging enabled: {log_file}")
    except Exception as e:
        logging.error(f"⚠️ Could not create log file: {e}")


setup_logging()
import io
from icon_manager import load_icons_dict
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QLabel,
    QPushButton,
    QLineEdit,
    QHBoxLayout,
    QFileDialog,
    QStyle,
    QMenu,
    QMessageBox,
    QCheckBox,
    QSplitter,
    QTreeWidgetItemIterator,
    QDialog,
    QGroupBox,
    QSpinBox,
    QSizePolicy,
    QFrame,
    QComboBox,
    QTextEdit,
    QProgressBar,
    QListWidget,
    QListWidgetItem,
    QGridLayout,
)
from PyQt6.QtCore import (
    Qt,
    QSize,
    QRect,
    QTimer,
    QUrl,
    pyqtSignal,
    QByteArray,
    QPoint,
    QThread,
    QRectF,
    QEvent,
)
from PyQt6.QtGui import (
    QIcon,
    QPixmap,
    QFont,
    QBrush,
    QColor,
    QPainter,
    QAction,
    QKeyEvent,
    QMouseEvent,
    QActionGroup,
    QPalette,
    QPolygon,
    QCursor,
    QPen,
    QTextCursor,
)
from styles import DARK_STYLE
import styles
from taskbar_progress import TaskbarProgress, TaskbarThumbnailButtons
import re
from translator import tr, Translator
from about_dialog import AboutDialog
from settings_dialog import SettingsDialog, ScanProgressDialog
from folder_stats_dialog import FolderStatsDialog
from subtitle_popup import SubtitlePopup, SubtitleButton
from placeholders import draw_video_placeholder, draw_library_placeholder

from video_item_data import VideoItemData
from player import VideoPlayerWidget
from library import HoverTreeWidget, VideoItemDelegate
from hotkeys import HotkeyManager
from tags_dialog import TagsDialog

# from floating_player import FloatingVideoWindow, PiPManager
from tag_filter_popup import TagFilterPopup
from utils import natural_sort_key, format_time, format_duration, format_size, format_audio_track_name
from config_manager import ConfigManager
from pureref_manager import PureRefManager
from search_utils import smart_search


class PiPOverlay(QWidget):
    def __init__(self, parent=None):
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        if hasattr(Qt.WindowType, "WindowTransparentForInput"):
            flags |= Qt.WindowType.WindowTransparentForInput
        super().__init__(parent, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.hover_edge = None
        self.active = False
        self.accent_color = QColor("#018574")

    def set_active(self, active):
        if self.active != active:
            self.active = active
            self.update()

    def set_hover_edge(self, edge):
        if self.hover_edge != edge:
            self.hover_edge = edge
            self.update()

    def paintEvent(self, event):
        if self.active or self.hover_edge:
            # logging.debug(f"PiPOverlay paintEvent: edge={self.hover_edge}")
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            w, h = self.width(), self.height()
            r_large = 6
            r_small = 4

            # Border rect connecting the centers of the large dots
            painter.setPen(QPen(self.accent_color, 2))
            painter.drawRect(r_large, r_large, w - 2 * r_large, h - 2 * r_large)

            painter.setBrush(self.accent_color)
            painter.setPen(Qt.PenStyle.NoPen)

            # Corners (exactly on the rect vertices)
            painter.drawEllipse(QPoint(r_large, r_large), r_large, r_large)
            painter.drawEllipse(QPoint(w - r_large, r_large), r_large, r_large)
            painter.drawEllipse(QPoint(r_large, h - r_large), r_large, r_large)
            painter.drawEllipse(QPoint(w - r_large, h - r_large), r_large, r_large)

            # Midpoints (on the rect edges)
            painter.drawEllipse(QPoint(w // 2, r_large), r_small, r_small)
            painter.drawEllipse(QPoint(w // 2, h - r_large), r_small, r_small)
            painter.drawEllipse(QPoint(r_large, h // 2), r_small, r_small)
            painter.drawEllipse(QPoint(w - r_large, h // 2), r_small, r_small)

            painter.end()


class VideoCourseBrowser(QMainWindow):
    # natural_sort_key is now in utils.py

    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()
        self.setWindowTitle(tr("app.title"))

        self.script_dir = Path(__file__).parent
        self.config_file = RESOURCES_DIR / "settings.ini"
        self.db_file = DATA_DIR / "video_courses.db"
        self.db = DatabaseManager(self.db_file)
        self.config = ConfigManager(self.config_file, ROOT_DIR, DATA_DIR)
        self.pureref_manager = PureRefManager(self.config)

        # Enable file logging if configured
        if self.config.get_enable_debug_file():
            enable_file_logging()

        self.hotkey_manager = HotkeyManager(self)
        self.hotkey_manager.global_action_triggered.connect(self.handle_player_action)
        self.hotkey_manager.global_action_state_changed.connect(
            lambda action, pressed: self.handle_player_action(action, pressed)
        )
        self.selected_tag_ids = set()
        self.load_settings()

        self.load_icons()

        self.taskbar_progress = TaskbarProgress()
        self.last_played_path = None

        # PiP State
        self.is_pip_mode = False
        self.normal_geometry = None
        self.pip_geometry = None
        self.dragging = False
        self.resizing = False
        self.resize_edge = None
        self.drag_start_pos = QPoint()
        self.window_start_geo = QRect()
        self.window_start_pos = QPoint()
        self.resize_margin = 12
        self.current_hover_edge = None
        self.pip_overlay = None
        
        # Fullscreen State
        self._was_maximized_before_fullscreen = False

        self.create_menu_bar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(0)

        self.status = self.statusBar()
        self.status.setSizeGripEnabled(False)
        self.status.setContentsMargins(5, 0, 5, 0)
        self.info_label = QLabel(tr("status.not_loaded"))
        self.status.addWidget(self.info_label, 1)

        self.path_edit = QLineEdit(self.library_paths)
        self.path_edit.setVisible(False)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(
            False
        )  # Default non-collapsible, specific overrides applied later
        main_layout.addWidget(self.splitter, 1)

        self.browser_widget = QWidget()
        self.browser_widget.setMinimumWidth(200)  # Ensure library has minimum width
        browser_layout = QVBoxLayout(self.browser_widget)
        browser_layout.setContentsMargins(0, 0, 0, 0)
        browser_layout.setSpacing(0)

        # Search area layout
        search_container = QWidget()
        search_container_layout = QHBoxLayout(search_container)
        search_container_layout.setContentsMargins(5, 0, 5, 5)
        search_container_layout.setSpacing(5)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(tr("library.search_placeholder"))
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self.filter_library)
        self.search_edit.setObjectName("librarySearch")
        search_container_layout.addWidget(self.search_edit)

        self.fav_filter_btn = QPushButton()
        self.fav_filter_btn.setCheckable(True)
        self.fav_filter_btn.setIcon(self.icons.get("context_favorite_on", QIcon()))
        self.fav_filter_btn.setToolTip(tr("library.filter_favorites"))
        self.fav_filter_btn.setFixedSize(30, 30)
        self.fav_filter_btn.setObjectName("favFilterBtn")

        # Connect toggled BEFORE setting checked state to ensure initial filtering
        self.fav_filter_btn.toggled.connect(
            lambda _: self.filter_library(self.search_edit.text())
        )

        search_container_layout.addWidget(self.fav_filter_btn)

        self.tag_filter_btn = QPushButton()
        self.tag_filter_btn.setCheckable(True)
        self.tag_filter_btn.setIcon(
            self.icons.get("context_tags", QIcon())
        )  # Assuming context_tags exists
        self.tag_filter_btn.setToolTip(tr("library.filter_tags"))
        self.tag_filter_btn.setFixedSize(30, 30)
        self.tag_filter_btn.setObjectName("tagFilterBtn")
        self.tag_filter_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tag_filter_btn.customContextMenuRequested.connect(
            self.show_tag_filter_popup
        )
        self.tag_filter_btn.toggled.connect(
            lambda _: self.filter_library(self.search_edit.text())
        )

        search_container_layout.addWidget(self.tag_filter_btn)

        self.marker_toggle_btn = QPushButton()
        self.marker_toggle_btn.setCheckable(True)
        # Use a fallback icon if show_markers doesn't exist, e.g. context_tags or just text if needed
        # But we added "show_markers" to load_icons, relying on IconManager returning empty if missing.
        # Let's set a standard icon or reuse one if empty.
        icon = self.icons.get("show_markers", QIcon())
        if icon.isNull():
            icon = self.style().standardIcon(
                QStyle.StandardPixmap.SP_FileDialogDetailedView
            )
        self.marker_toggle_btn.setIcon(icon)
        self.marker_toggle_btn.setToolTip(tr("library.show_markers") or "Show Markers")
        self.marker_toggle_btn.setFixedSize(30, 30)
        self.marker_toggle_btn.setObjectName("markerToggleBtn")
        self.marker_toggle_btn.setChecked(True)  # Default On
        self.marker_toggle_btn.toggled.connect(self.toggle_markers)

        search_container_layout.addWidget(self.marker_toggle_btn)

        browser_layout.addWidget(search_container)

        self.course_tree = HoverTreeWidget()
        self.course_tree.setColumnCount(1)
        self.course_tree.setHeaderHidden(True)
        self.course_tree.setAlternatingRowColors(False)
        self.course_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.course_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.course_tree.itemDoubleClicked.connect(self.item_double_clicked)
        self.course_tree.set_animation_interval(self.animation_interval)
        self.course_tree.itemExpanded.connect(self.on_item_expanded)
        self.course_tree.itemCollapsed.connect(self.on_item_collapsed)

        delegate_config = {
            "folder_row_height": self.folder_row_height,
            "video_row_height": self.video_row_height,
            "display_width": self.display_width,
            "display_height": self.display_height,
            "format_duration": format_duration,
            "format_size": format_size,
            "show_tree_lines": True,
            "show_pureref_badges": True,
            "show_pureref_badges_when_missing": False,
            "tree_line_colors": self.config.get_tree_line_colors(),
        }
        delegate = VideoItemDelegate(delegate_config, self.course_tree)
        delegate.pureref_manager = self.pureref_manager
        self.course_tree.setItemDelegate(delegate)

        browser_layout.addWidget(self.course_tree)

        self.video_player = VideoPlayerWidget()
        self.video_player.setMinimumWidth(400)  # Ensure player has minimum width
        self.video_player.db = self.db
        self.video_player.config = self.config
        self.video_player.taskbar_progress = self.taskbar_progress
        self.video_player.show_preview = self.show_preview_popup
        self.video_player.set_ffmpeg_path(self.ffmpeg_path)

        self.video_player.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.video_player.video_finished.connect(self.on_video_finished)
        self.video_player.position_changed.connect(self.save_progress)
        self.video_player.pause_changed.connect(self.on_player_pause_changed)
        self.video_player.subtitle_style_changed.connect(self.save_subtitle_settings)
        self.video_player.next_video_requested.connect(self.play_next_video)
        self.video_player.prev_video_requested.connect(self.play_prev_video)
        self.video_player.markers_changed.connect(self.on_markers_changed)
        self.video_player.toggle_fullscreen_requested.connect(self.toggle_fullscreen)
        self.video_player.pip_mode_requested.connect(self.enter_pip_mode)
        self.video_player.pip_exit_requested.connect(self.exit_pip_mode)

        # Apply initial subtitle settings
        self.video_player.set_subtitle_styles(
            self.sub_color, self.sub_border_color, self.sub_scale
        )

        self.splitter.addWidget(self.browser_widget)
        self.splitter.addWidget(self.video_player)

        # Set default sizes before restoring state
        self.splitter.setSizes(
            [int(self.window_width * 0.3), int(self.window_width * 0.7)]
        )

        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        self._init_maximized = self.restore_window_state()

        # Override collapsible state from settings: Library (0) collapsible, Player (1) fixed
        self.splitter.setCollapsible(0, True)
        self.splitter.setCollapsible(1, False)

        # Double-check splitter sizes after all geometry is set
        QTimer.singleShot(50, self._ensure_player_visible)

        self.load_courses()
        self.course_tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        QTimer.singleShot(100, self.restore_last_video)

        self.last_saved_position = {}
        self.progress_save_timer = QTimer(self)
        self.progress_save_timer.timeout.connect(self.periodic_progress_save)
        self.progress_save_timer.start(1000)

        self.pureref_status_timer = QTimer(self)
        self.pureref_status_timer.timeout.connect(
            lambda: self.course_tree.viewport().update()
        )
        self.pureref_status_timer.start(5000)
        self._last_stats_update = 0

        # Restore filter states AFTER all components (like course_tree) are initialized
        if hasattr(self, "fav_filter_active"):
            self.fav_filter_btn.setChecked(self.fav_filter_active)
        if hasattr(self, "tag_filter_active"):
            self.tag_filter_btn.setChecked(self.tag_filter_active)

        # Auto-update cleanup and check
        from update_app import cleanup_update_artifacts

        cleanup_update_artifacts()
        if self.config.get_check_updates_on_start():
            QTimer.singleShot(5000, self._check_for_update)

    def keyPressEvent(self, event: QKeyEvent):
        action = self.hotkey_manager.get_action(event)

        # Actions that allow auto-repeat (like seeking, volume, or speed with arrows)
        repeatable_actions = [
            "seek_forward",
            "seek_backward",
            "speed_up",
            "speed_down",
            "volume_up",
            "volume_down",
            "zoom_in",
            "zoom_out",
        ]

        if event.isAutoRepeat() and action not in repeatable_actions:
            return

        if action:
            self.handle_player_action(action, pressed=True)
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.isAutoRepeat():
            return
        action = self.hotkey_manager.get_action(event)
        if action:
            self.handle_player_action(action, pressed=False)
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def handle_player_action(self, action, pressed=True):
        if not hasattr(self, "video_player") or not self.video_player:
            return

        # Special case for hold actions (currently only zoom_mode)
        if action == "zoom_mode":
            self.video_player.set_zoom_mode(pressed)
            return

        # For all other actions, process ONLY on press
        if not pressed:
            return

        if action == "toggle_pause":
            self.video_player.play_pause()
        elif action == "pause":
            if self.video_player.player and not self.video_player.player.pause:
                self.video_player.player.pause = True
        elif action == "seek_forward":
            self.video_player.seek_relative(10)
        elif action == "seek_backward":
            self.video_player.seek_relative(-10)
        elif action == "volume_up":
            self.video_player.adjust_volume(5)
        elif action == "volume_down":
            self.video_player.adjust_volume(-5)
        elif action == "toggle_mute":
            self.video_player.toggle_mute()
        elif action == "toggle_subtitles":
            self.video_player.toggle_subtitles_hotkey()
        elif action == "take_screenshot":
            success = self.video_player.screenshot_to_clipboard()
            # Show OSD notification
            if (
                hasattr(self.video_player, "osd_manager")
                and self.video_player.osd_manager
            ):
                self.video_player.osd_manager.show_screenshot(success)
            # Also update status label for backward compatibility
            if success:
                self.info_label.setText(tr("player.tooltip_screenshot") + " ✓")
                QTimer.singleShot(
                    2000, lambda: self.info_label.setText(tr("status.ready"))
                )
        elif action == "reset_zoom":
            self.video_player.reset_zoom()
        elif action == "zoom_in":
            self.video_player.zoom_in()
        elif action == "zoom_out":
            self.video_player.zoom_out()
        elif action == "frame_step":
            self.video_player.frame_step()
        elif action == "frame_back":
            self.video_player.frame_back_step()
        elif action == "speed_up":
            self.video_player.adjust_speed(0.1)
        elif action == "speed_down":
            self.video_player.adjust_speed(-0.1)
        elif action == "next_video":
            self.play_next_video()
        elif action == "prev_video":
            self.play_prev_video()
        elif action == "toggle_fullscreen":
            self.toggle_fullscreen()
        elif action == "exit_fullscreen_or_pip":
            if self.is_pip_mode:
                self.exit_pip_mode()
            elif self.isFullScreen():
                self.toggle_fullscreen()
        elif action == "add_marker":
            self.video_player.add_marker()
        elif action == "toggle_marker_gallery":
            self.video_player.toggle_marker_gallery()
        elif action == "toggle_pip":
            self.toggle_pip_mode()
        elif action == "audio_delay_up":
            self.video_player.adjust_audio_delay(0.05)
        elif action == "audio_delay_down":
            self.video_player.adjust_audio_delay(-0.05)
        elif action == "toggle_library":
            self.toggle_library()
        elif action == "locate_video":
            self.locate_active_video()
        elif action == "expand_tree":
            self.expand_tree()
        elif action == "collapse_tree":
            self.collapse_tree()
        elif action == "toggle_always_on_top":
            self.toggle_always_on_top()

    def locate_active_video(self):
        """Scroll the library to the currently playing video."""
        if not hasattr(self, "video_player") or not self.video_player.current_file:
            return

        # Show library if hidden
        if not self.browser_widget.isVisible():
            self.toggle_library()

        file_path = self.video_player.current_file
        item = self.find_video_item(file_path)

        if item:
            # Expand all parents
            parent = item.parent()
            while parent:
                parent.setExpanded(True)
                parent = parent.parent()

            self.course_tree.setCurrentItem(item)
            self.course_tree.scrollToItem(item, QTreeWidget.ScrollHint.PositionAtCenter)

            # Temporary status message
            filename = Path(file_path).name
            self.info_label.setText(tr("status.located", file=filename))
            QTimer.singleShot(3000, lambda: self.info_label.setText(tr("status.ready")))
        else:
            logging.warning(f"Could not find video item in library for: {file_path}")

    def expand_tree(self):
        """Expand all items in the library tree."""
        iterator = QTreeWidgetItemIterator(self.course_tree)
        while iterator.value():
            item = iterator.value()
            item.setExpanded(True)
            iterator += 1
        self.info_label.setText(tr("status.tree_expanded"))
        QTimer.singleShot(2000, lambda: self.info_label.setText(tr("status.ready")))

    def collapse_tree(self):
        """Collapse all items in the library tree."""
        iterator = QTreeWidgetItemIterator(self.course_tree)
        while iterator.value():
            item = iterator.value()
            item.setExpanded(False)
            iterator += 1
        self.info_label.setText(tr("status.tree_collapsed"))
        QTimer.singleShot(2000, lambda: self.info_label.setText(tr("status.ready")))

    def toggle_always_on_top(self, checked=None):
        """Toggle Always on Top window state."""
        if checked is None:
            # Toggle current state
            is_on_top = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
            new_state = not is_on_top
        else:
            new_state = checked

        if hasattr(self, "always_on_top_action"):
            self.always_on_top_action.setChecked(new_state)

        flags = self.windowFlags()
        if new_state:
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)

        # We must call show() after changing window flags to apply them
        self.show()

        # Show OSD notification
        if hasattr(self.video_player, "osd_manager") and self.video_player.osd_manager:
            self.video_player.osd_manager.show_always_on_top(new_state)

        # Status message (keep for backward compatibility)
        msg = tr("hotkeys.toggle_always_on_top") + (": ON" if new_state else ": OFF")
        self.info_label.setText(msg)
        QTimer.singleShot(2000, lambda: self.info_label.setText(tr("status.ready")))

    def toggle_fullscreen(self):
        if getattr(self, "is_pip_mode", False):
            self.exit_pip_mode()

        if self.isFullScreen():
            # Exiting fullscreen - restore previous maximize state
            if getattr(self, '_was_maximized_before_fullscreen', False):
                self.showMaximized()
            else:
                self.showNormal()
            self.menuBar().show()
            self.status.show()
            if hasattr(self, "browser_widget"):
                self.browser_widget.show()
            if hasattr(self, "_saved_splitter_state"):
                self.splitter.restoreState(self._saved_splitter_state)
        else:
            # Entering fullscreen - save current maximize state
            self._was_maximized_before_fullscreen = self.isMaximized()
            self._saved_splitter_state = self.splitter.saveState()
            self.showFullScreen()
            self.menuBar().hide()
            self.status.hide()
            if hasattr(self, "browser_widget"):
                self.browser_widget.hide()
            # Collapse library
            self.splitter.setSizes([0, self.width()])

    def change_language(self, lang_code):
        if tr.current_lang == lang_code:
            return

        logging.debug(f"Changing language to {lang_code}...")
        tr.load_language(lang_code)
        self.save_language_setting(lang_code)
        # Defer UI update to avoid crashing while inside a menu action
        # Increased delay to 100ms to ensure menu animations finish
        QTimer.singleShot(100, self.update_all_texts)

    def save_language_setting(self, lang_code):
        self.config.set_language(lang_code)

    def load_language_setting(self):
        return self.config.get_language()

    def update_all_texts(self):
        try:
            logging.debug("update_all_texts started")
            self.setWindowTitle(tr("app.title"))
            logging.debug("Clearing menu bar")
            self.menuBar().clear()
            logging.debug("Recreating menu bar")
            self.create_menu_bar()
            if hasattr(self, "search_edit"):
                self.search_edit.setPlaceholderText(tr("library.search_placeholder"))
            # Update main window button tooltips
            if hasattr(self, "fav_filter_btn"):
                self.fav_filter_btn.setToolTip(tr("library.filter_favorites"))
            if hasattr(self, "tag_filter_btn"):
                self.tag_filter_btn.setToolTip(tr("library.filter_tags"))
            if hasattr(self, "marker_toggle_btn"):
                self.marker_toggle_btn.setToolTip(tr("library.show_markers"))
            if hasattr(self, "video_player") and self.video_player:
                logging.debug("Updating player texts")
                self.video_player.update_texts()
            logging.debug("Loading courses")
            self.load_courses()
            logging.debug("update_all_texts finished")
        except Exception as e:
            logging.critical(f"CRITICAL ERROR in update_all_texts: {e}", exc_info=True)

    def on_item_expanded(self, item):
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if item_type != "folder":
            return

        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path:
            return

        self.db.update_folder_expanded_state(path, True)

    def on_item_collapsed(self, item):
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if item_type != "folder":
            return

        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path:
            return

        self.db.update_folder_expanded_state(path, False)

    def open_pureref_for_folder(self, folder: Path):
        """Open or focus PureRef for the given folder path."""
        if not self.pureref_manager:
            return

        success, error = self.pureref_manager.open(folder)
        if not success:
            if error.startswith("pureref_not_found:"):
                path = error.split(":", 1)[1]
                msg = tr("pureref.exe_not_found") or f"PureRef.exe not found at: {path}"
                if "{path}" in msg:
                    msg = msg.format(path=path)
                QMessageBox.warning(self, tr("error.title"), msg)
            else:
                err = error.split(":", 1)[1] if ":" in error else error
                msg = tr("pureref.launch_error") or f"Error launching PureRef: {err}"
                if "{error}" in msg:
                    msg = msg.format(error=err)
                QMessageBox.warning(self, tr("error.title"), msg)
        else:
            # Refresh tree immediately to update badge color (yellow -> green)
            QTimer.singleShot(1000, lambda: self.course_tree.viewport().update())

    def update_window_title_for_item(self, item):
        course_item = item.parent()
        course_name = ""

        if course_item is not None:
            full_text = course_item.text(0)
            idx = full_text.find("(")
            course_name = full_text[:idx].strip() if idx > 0 else full_text.strip()

        video_name = item.text(0).strip()

        if course_name:
            title = f"{tr('app.title')} - {course_name} - {video_name}"
        else:
            title = video_name

        self.setWindowTitle(title)

    def restore_window_state(self):
        is_maximized = False
        state = self.config.get_window_state()

        if state:
            if "geometry" in state:
                try:
                    # Try hex first (default for other fields), fallback to base64 if needed
                    geo_str = state["geometry"]
                    try:
                        geometry = QByteArray.fromHex(bytes(geo_str, "utf-8"))
                    except:
                        geometry = QByteArray.fromBase64(geo_str.encode())
                    self.restoreGeometry(geometry)
                except Exception as e:
                    logging.error(f"Error restoring geometry: {e}")
                    self.resize(self.window_width, self.window_height)
            else:
                self.resize(self.window_width, self.window_height)

            # Restore library visibility
            show_library = state.get("show_library", True)
            if hasattr(self, "browser_widget"):
                self.browser_widget.setVisible(show_library)
                if hasattr(self, "toggle_lib_action"):
                    self.toggle_lib_action.setChecked(show_library)

            is_maximized = state.get("is_maximized", False)

            if "splitter_state" in state:
                try:
                    splitter_state = QByteArray.fromHex(
                        bytes(state["splitter_state"], "utf-8")
                    )
                    self.splitter.restoreState(splitter_state)

                    # Ensure player pane (index 1) is not collapsed
                    sizes = self.splitter.sizes()
                    if len(sizes) >= 2 and sizes[1] < 50:
                        total_width = sum(sizes)
                        if total_width > 0:
                            self.splitter.setSizes(
                                [int(total_width * 0.3), int(total_width * 0.7)]
                            )
                        else:
                            self.splitter.setSizes([400, 1000])
                except Exception as e:
                    logging.error(f"Error restoring splitter: {e}")

            if "playback_speed" in state:
                try:
                    speed_value = int(state["playback_speed"])
                    self.video_player._restoring_state = True
                    self.video_player.speed_slider.setValue(speed_value)
                    self.video_player._restoring_state = False
                except Exception as e:
                    logging.error(f"Error restoring playback speed: {e}")
                    self.video_player._restoring_state = (
                        False  # Ensure flag is reset on error
                    )

            if "pip_geometry" in state:
                try:
                    self.pip_geometry = QByteArray.fromHex(
                        bytes(state["pip_geometry"], "utf-8")
                    )
                except Exception as e:
                    logging.error(f"Error restoring PiP geometry: {e}")

            if "show_markers" in state:
                try:
                    show = state["show_markers"]
                    if isinstance(show, str):
                        show = show.lower() == "true"
                    self.marker_toggle_btn.setChecked(bool(show))
                    self.toggle_markers(bool(show))
                except Exception as e:
                    logging.error(f"Error restoring marker state: {e}")

            if "always_on_top" in state:
                try:
                    on_top = state["always_on_top"]
                    if isinstance(on_top, str):
                        on_top = on_top.lower() == "true"
                    self.toggle_always_on_top(bool(on_top))
                except Exception as e:
                    logging.error(f"Error restoring always_on_top state: {e}")

            if "show_tree_lines" in state:
                try:
                    show = state["show_tree_lines"]
                    if isinstance(show, str):
                        show = show.lower() == "true"
                    self.show_tree_lines_action.setChecked(bool(show))
                    delegate = self.course_tree.itemDelegate()
                    if hasattr(delegate, "config"):
                        delegate.config["show_tree_lines"] = bool(show)
                except Exception as e:
                    logging.error(f"Error restoring show_tree_lines state: {e}")

            if "show_pureref_badges" in state:
                try:
                    show = state["show_pureref_badges"]
                    if isinstance(show, str):
                        show = show.lower() == "true"
                    self.show_pureref_badges_action.setChecked(bool(show))
                    delegate = self.course_tree.itemDelegate()
                    if hasattr(delegate, "config"):
                        delegate.config["show_pureref_badges"] = bool(show)
                except Exception as e:
                    logging.error(f"Error restoring show_pureref_badges state: {e}")

            if "show_pureref_badges_when_missing" in state:
                try:
                    show = state["show_pureref_badges_when_missing"]
                    if isinstance(show, str):
                        show = show.lower() == "true"
                    self.show_pureref_badges_when_missing_action.setChecked(bool(show))
                    delegate = self.course_tree.itemDelegate()
                    if hasattr(delegate, "config"):
                        delegate.config["show_pureref_badges_when_missing"] = bool(show)
                except Exception as e:
                    logging.error(
                        f"Error restoring show_pureref_badges_when_missing state: {e}"
                    )
        else:
            self.resize(self.window_width, self.window_height)

        return is_maximized

    def _ensure_player_visible(self):
        """Ensure the player pane in the splitter is not collapsed."""
        sizes = self.splitter.sizes()
        if len(sizes) >= 2:
            if sizes[1] < 400:  # Player width is too small
                total_width = self.splitter.width()
                if total_width > 0:
                    # Give 30% to library, 70% to player
                    self.splitter.setSizes(
                        [int(total_width * 0.3), int(total_width * 0.7)]
                    )
                else:
                    self.splitter.setSizes([400, 1000])

    def save_window_state(self):
        # Save PiP geometry
        if self.is_pip_mode:
            self.pip_geometry = self.saveGeometry()

        state = {
            "geometry": self.saveGeometry().toHex().data().decode("utf-8"),
            "is_maximized": self.isMaximized(),
            "show_library": self.browser_widget.isVisible()
            if hasattr(self, "browser_widget")
            else True,
        }

        state["splitter_state"] = (
            self.splitter.saveState().toHex().data().decode("utf-8")
        )

        if self.pip_geometry:
            state["pip_geometry"] = self.pip_geometry.toHex().data().decode("utf-8")

        if self.video_player.current_file:
            state["last_video"] = self.video_player.current_file

        state["playback_speed"] = str(self.video_player.speed_slider.value())
        state["show_markers"] = str(self.marker_toggle_btn.isChecked())
        state["show_pureref_badges"] = str(self.show_pureref_badges_action.isChecked())
        state["show_pureref_badges_when_missing"] = str(
            self.show_pureref_badges_when_missing_action.isChecked()
        )
        state["always_on_top"] = str(
            bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        )

        self.config.save_window_state(state)
        self.config.save_filter_state(
            self.fav_filter_btn.isChecked(),
            self.tag_filter_btn.isChecked(),
            self.selected_tag_ids,
        )

    def restore_last_video(self):
        state = self.config.get_window_state()
        last_video_path = state.get("last_video")
        if not last_video_path:
            return

        if not last_video_path or not Path(last_video_path).exists():
            return

        item = self.find_video_item(last_video_path)

        if item:
            saved_position, saved_volume = self.get_saved_position(last_video_path)
            self.video_player.load_video(
                last_video_path, saved_position, volume=saved_volume, auto_play=False
            )
            # Update delegate
            delegate = self.course_tree.itemDelegate()
            if isinstance(delegate, VideoItemDelegate):
                delegate.playing_path = last_video_path
                delegate.is_paused = True  # Load paused
                self.course_tree.viewport().update()

            self.course_tree.setCurrentItem(item)
            self.course_tree.scrollToItem(item)
            self.setFocus()
            self.update_window_title_for_item(item)
            self.update_navigation_buttons(item)

    def find_video_item(self, file_path):
        iterator = QTreeWidgetItemIterator(self.course_tree)
        while iterator.value():
            item = iterator.value()
            if item.data(0, Qt.ItemDataRole.UserRole) == file_path:
                return item
            iterator += 1
        return None

    def create_menu_bar(self):
        menubar = self.menuBar()

        # [Library] Menu
        lib_menu = menubar.addMenu(tr("menu.library"))

        scan_action = QAction(
            self.icons.get("menu_scan", QIcon()), tr("menu.scan"), self
        )
        scan_action.setShortcut("Ctrl+R")
        scan_action.triggered.connect(self.rescan_directories)
        lib_menu.addAction(scan_action)

        settings_action = QAction(
            self.icons.get("menu_settings", QIcon()), tr("menu.settings"), self
        )
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.open_settings)
        lib_menu.addAction(settings_action)

        # [Tools] Menu
        tools_menu = menubar.addMenu(tr("menu.tools"))

        screenshot_action = QAction(
            self.icons.get("screenshot", QIcon()), tr("menu.screenshot"), self
        )
        screenshot_action.setShortcut("S")
        screenshot_action.triggered.connect(
            lambda: self.handle_player_action("take_screenshot")
        )
        tools_menu.addAction(screenshot_action)

        add_marker_action = QAction(
            self.icons.get("add", QIcon()), tr("player.add_marker_title"), self
        )
        add_marker_action.setShortcut("B")
        add_marker_action.triggered.connect(
            lambda: self.handle_player_action("add_marker")
        )
        tools_menu.addAction(add_marker_action)

        show_markers_action = QAction(
            self.icons.get("show_markers", QIcon()), tr("menu.show_markers"), self
        )
        show_markers_action.setShortcut("G")
        show_markers_action.triggered.connect(
            lambda: self.handle_player_action("toggle_marker_gallery")
        )
        tools_menu.addAction(show_markers_action)

        tools_menu.addSeparator()

        locate_action = QAction(
            self.icons.get("locate", QIcon()), tr("menu.locate_video"), self
        )
        locate_action.setShortcut("L")
        locate_action.triggered.connect(self.locate_active_video)
        tools_menu.addAction(locate_action)

        expand_tree_action = QAction(
            self.icons.get("expand", QIcon()), tr("menu.expand_tree"), self
        )
        expand_tree_action.setShortcut("E")
        expand_tree_action.triggered.connect(
            lambda: self.handle_player_action("expand_tree")
        )
        tools_menu.addAction(expand_tree_action)

        collapse_tree_action = QAction(
            self.icons.get("collapse", QIcon()), tr("menu.collapse_tree"), self
        )
        collapse_tree_action.setShortcut("W")
        collapse_tree_action.triggered.connect(
            lambda: self.handle_player_action("collapse_tree")
        )
        tools_menu.addAction(collapse_tree_action)

        tools_menu.addSeparator()

        frame_step_action = QAction(
            self.icons.get("next_frame", QIcon()), tr("menu.frame_step"), self
        )
        frame_step_action.setShortcut(".")
        frame_step_action.triggered.connect(
            lambda: self.handle_player_action("frame_step")
        )
        tools_menu.addAction(frame_step_action)

        frame_back_action = QAction(
            self.icons.get("prev_frame", QIcon()), tr("menu.frame_back"), self
        )
        frame_back_action.setShortcut(",")
        frame_back_action.triggered.connect(
            lambda: self.handle_player_action("frame_back")
        )
        tools_menu.addAction(frame_back_action)

        # [View] Menu
        view_menu = menubar.addMenu(tr("menu.view"))

        # Language selection
        lang_menu = view_menu.addMenu(tr("menu.language"))
        lang_group = QActionGroup(self)
        lang_group.setExclusive(True)

        ru_action = QAction(tr("menu.language_ru"), self)
        ru_action.setCheckable(True)
        ru_action.setChecked(tr.current_lang == "ru")
        ru_action.triggered.connect(lambda: self.change_language("ru"))
        lang_group.addAction(ru_action)
        lang_menu.addAction(ru_action)

        en_action = QAction(tr("menu.language_en"), self)
        en_action.setCheckable(True)
        en_action.setChecked(tr.current_lang == "en")
        en_action.triggered.connect(lambda: self.change_language("en"))
        lang_group.addAction(en_action)
        lang_menu.addAction(en_action)

        view_menu.addSeparator()

        self.toggle_osd_action = QAction(tr("menu.show_osd"), self)
        self.toggle_osd_action.setCheckable(True)
        self.toggle_osd_action.setChecked(self.config.get_show_osd())
        self.toggle_osd_action.triggered.connect(self.toggle_osd_display)
        view_menu.addAction(self.toggle_osd_action)

        self.toggle_lib_action = QAction(tr("menu.show_library"), self)
        self.toggle_lib_action.setCheckable(True)
        self.toggle_lib_action.setChecked(
            self.browser_widget.isVisible() if hasattr(self, "browser_widget") else True
        )
        self.toggle_lib_action.setShortcut("Ctrl+L")
        self.toggle_lib_action.triggered.connect(self.toggle_library)
        view_menu.addAction(self.toggle_lib_action)

        self.show_tree_lines_action = QAction(tr("menu.show_tree_lines"), self)
        self.show_tree_lines_action.setCheckable(True)
        self.show_tree_lines_action.setChecked(True)
        self.show_tree_lines_action.triggered.connect(self.toggle_tree_lines)
        view_menu.addAction(self.show_tree_lines_action)

        self.show_pureref_badges_action = QAction(tr("menu.show_pureref_badges"), self)
        self.show_pureref_badges_action.setCheckable(True)
        self.show_pureref_badges_action.setChecked(True)
        self.show_pureref_badges_action.triggered.connect(self.toggle_pureref_badges)
        view_menu.addAction(self.show_pureref_badges_action)

        self.show_pureref_badges_when_missing_action = QAction(
            tr("menu.show_pureref_badges_when_missing"), self
        )
        self.show_pureref_badges_when_missing_action.setCheckable(True)
        self.show_pureref_badges_when_missing_action.setChecked(False)
        self.show_pureref_badges_when_missing_action.triggered.connect(
            self.toggle_pureref_badges_when_missing
        )
        view_menu.addAction(self.show_pureref_badges_when_missing_action)

        self.always_on_top_action = QAction(
            self.icons.get("pin", QIcon()), tr("menu.always_on_top"), self
        )
        self.always_on_top_action.setCheckable(True)
        self.always_on_top_action.setShortcut("T")
        self.always_on_top_action.triggered.connect(self.toggle_always_on_top)
        view_menu.addAction(self.always_on_top_action)

        fullscreen_action = QAction(
            self.icons.get("fullscreen", QIcon()), tr("menu.fullscreen"), self
        )
        fullscreen_action.setShortcut("F")
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        pip_action = QAction(
            self.icons.get("picture-in-picture", QIcon()), tr("menu.pip_mode"), self
        )
        pip_action.setShortcut("P")
        pip_action.triggered.connect(self.toggle_pip_mode)
        view_menu.addAction(pip_action)

        view_menu.addSeparator()

        # Reload Styles
        reload_styles_action = QAction(
            self.icons.get("menu_reload", QIcon()), tr("menu.reload_styles"), self
        )
        reload_styles_action.setShortcut("F5")
        reload_styles_action.triggered.connect(self.reload_styles)
        view_menu.addAction(reload_styles_action)

        help_menu = menubar.addMenu(tr("menu.help"))

        check_updates_action = QAction(
            self.icons.get("upload", QIcon()), tr("menu.check_updates"), self
        )
        check_updates_action.triggered.connect(
            lambda: self._check_for_update(force=True)
        )
        help_menu.addAction(check_updates_action)

        help_menu.addSeparator()

        about_action = QAction(
            self.icons.get("menu_about", QIcon()), tr("menu.about"), self
        )
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def reload_styles(self):
        """Reload application styles."""
        qss = styles.StyleManager.get_style()
        self.setStyleSheet(qss)
        # If style update needs to be forced
        self.style().unpolish(self)
        self.style().polish(self)
        self.info_label.setText(tr("status.styles_reloaded"))

    def moveEvent(self, event):
        """Propagate move event to video player to update overlay positions."""
        super().moveEvent(event)
        if hasattr(self, "video_player") and self.video_player:
            # Direct call for immediate sync
            self.video_player._update_gallery_geometry()
            # Delayed call for robustness (Windows drag sync)
            QTimer.singleShot(0, self.video_player._update_gallery_geometry)
        if (
            hasattr(self, "is_pip_mode")
            and self.is_pip_mode
            and getattr(self, "pip_overlay", None)
        ):
            self.pip_overlay.setGeometry(self.geometry())

    def resizeEvent(self, event):
        if self.is_pip_mode and getattr(self, "pip_overlay", None):
            self.pip_overlay.setGeometry(self.geometry())
        super().resizeEvent(event)

    def close_db_connection(self):
        """Prepare for DB deletion: stop timers and release resources"""
        # Stop auto-save timer
        if hasattr(self, "progress_save_timer") and self.progress_save_timer.isActive():
            self.progress_save_timer.stop()

        # Stop player to release any file locks
        if self.video_player and self.video_player.player:
            self.video_player.player.stop()

        # Close the DatabaseManager connection
        if self.db:
            self.db.close()

        # Force garbage collection to close dangling DB connections
        import gc

        gc.collect()

    def open_settings(self):
        dialog = SettingsDialog(self, self.config_file)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_settings()
            self.load_courses()
            self.update_delegate_config()
            # self.path_edit.setText(self.library_paths) # path_edit might not exist or be relevant anymore
            # QMessageBox.information(self, tr('settings.done'), tr('settings.saved')) # Optional, maybe too annoying?

    def update_delegate_config(self):
        """Update delegate configuration with new settings."""
        if hasattr(self, "course_tree"):
            delegate = self.course_tree.itemDelegate()
            if isinstance(delegate, VideoItemDelegate):
                delegate.config.update(
                    {
                        "folder_row_height": self.folder_row_height,
                        "video_row_height": self.video_row_height,
                        "display_width": self.display_width,
                        "display_height": self.display_height,
                    }
                )
                self.course_tree.viewport().update()

    def show_about(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def _check_for_update(self, force=False):
        """Check for app updates. If force=True, always show result."""
        try:
            from update_app import check_for_update, get_current_version

            update_info = check_for_update()

            if update_info:
                # Skip if user chose to skip this version (unless forced)
                if not force:
                    skip = self.config.get_skip_version()
                    if skip and skip == update_info["latest"]:
                        return

                from update_dialog import UpdateDialog

                dialog = UpdateDialog(self, update_info)
                dialog.exec()

                if dialog.result_action == UpdateDialog.UPDATE_NOW:
                    self._do_app_update(update_info)
                elif dialog.result_action == UpdateDialog.SKIP_VERSION:
                    self.config.set_skip_version(update_info["latest"])
            elif force:
                current = get_current_version()
                QMessageBox.information(
                    self, tr("updater.title"), tr("updater.no_updates", version=current)
                )
        except Exception as e:
            if force:
                QMessageBox.warning(
                    self, tr("updater.title"), tr("updater.error", error=str(e))
                )

    def _do_app_update(self, update_info: dict):
        """Download update with progress dialog and restart on user action."""
        from progress_dialog import AppUpdateProgressDialog
        from update_app import launch_updater_and_exit
        from pathlib import Path

        dialog = AppUpdateProgressDialog(self)

        def on_restart(bat_path_str):
            self.save_window_state()
            launch_updater_and_exit(Path(bat_path_str))
            QApplication.quit()

        dialog.restart_requested.connect(on_restart)
        dialog.start_download(update_info)
        dialog.exec()

    def save_progress(self, position_sec, file_path):
        """Save playback progress."""
        # logging.debug(f"save_progress called for {file_path}")
        try:
            # Calculate percent here or let database.py handle it.
            # Current database.py save_progress expects (file_path, position_sec, duration_sec)
            # but I added another one later. Let me check my own code.
            # I added: save_progress(self, file_path, position, duration, percent, current_volume)

            if not file_path or file_path != self.video_player.current_file:
                return

            try:
                # logging.debug("accessing player properties...")
                position = self.video_player.player.time_pos or 0.0
                duration = int(self.video_player.player.duration or 0)
                current_volume = int(self.video_player.player.volume or 100)
                # logging.debug(f"properties: pos={position}, dur={duration}")
            except Exception as e:
                logging.debug(f"error accessing properties: {e}")
                return

            if duration > 0:
                percent = int((position / duration) * 100)
                remaining = duration - position
                if remaining < 1 and percent >= 99:
                    percent = 100
                    position = duration
            else:
                percent = 0

            self.db.save_progress(
                file_path, position, duration, percent, current_volume
            )
        except Exception as e:
            logging.error(f"Error saving progress: {e}")

    def periodic_progress_save(self, force_stats_update=False):
        if not self.video_player.current_file:
            return

        file_path = self.video_player.current_file

        try:
            position = self.video_player.player.time_pos or 0.0
            duration = int(self.video_player.player.duration or 0)
            current_volume = int(self.video_player.player.volume or 100)
        except Exception as e:
            logging.debug(f"periodic_progress_save error getting properties: {e}")
            return

        if duration > 0:
            percent = int((position / duration) * 100)
            remaining = duration - position
            if remaining < 1 and percent >= 99:
                percent = 100
                position = duration

            try:
                self.db.save_progress(
                    file_path, position, duration, percent, current_volume
                )
            except Exception as e:
                logging.error(f"Error saving progress to DB: {e}")
                return

            try:
                current_time = time.time()
                # Update folder stats FIRST so they can calculate delta based on OLD item data
                if force_stats_update or current_time - self._last_stats_update >= 30:
                    self.update_folder_stats_display(
                        file_path, position, duration, percent
                    )
                    self._last_stats_update = current_time

                # Then update the video item itself (which overwrites the stored data in the item)
                self.update_video_item_display(file_path, percent, position)
            except Exception as e:
                logging.debug(f"error in display updates: {e}")

    def update_folder_stats_display(self, file_path, position, duration, percent):
        """Update stats of parent folders for the currently playing video.

        Uses absolute recalculation: walks all child video items of each parent
        folder and recomputes watched/total from scratch. This avoids delta-based
        issues where stored values and current values are near-identical.
        """
        try:
            item = self.find_video_item(file_path)
            if not item:
                return

            parent = item.parent()
            while parent:
                # Recalculate stats from all child video items
                watched_sum = 0.0
                total_sum = 0.0
                video_count = 0

                self._collect_folder_stats(
                    parent,
                    file_path,
                    position,
                    duration,
                    percent,
                    watched_sum,
                    total_sum,
                    video_count,
                )
                stats = self._collect_folder_stats_result

                if stats["count"] > 0 and stats["total"] > 0:
                    pct = int((stats["watched"] / stats["total"]) * 100)
                    duration_str = format_duration(stats["total"])
                    watched_str = format_duration(stats["watched"])
                    stats_text = f"{stats['count']} videos \u2022 {watched_str} / {duration_str} ({pct}%)"

                    parent.setData(0, Qt.ItemDataRole.UserRole + 5, stats_text)
                    parent.setData(0, Qt.ItemDataRole.UserRole + 6, pct)
                    parent.setData(0, Qt.ItemDataRole.UserRole + 7, stats)

                parent = parent.parent()

            self.course_tree.viewport().update()
        except Exception as e:
            logging.error(f"Error in update_folder_stats_display: {e}", exc_info=True)

    def _collect_folder_stats(
        self,
        folder_item,
        current_file,
        current_pos,
        current_dur,
        current_pct,
        _w=0,
        _t=0,
        _c=0,
    ):
        """Recursively collect stats from all video children of a folder item."""
        result = {"watched": 0.0, "total": 0.0, "count": 0}

        for i in range(folder_item.childCount()):
            child = folder_item.child(i)
            item_type = child.data(0, Qt.ItemDataRole.UserRole + 1)

            if item_type == "video":
                child_path = child.data(0, Qt.ItemDataRole.UserRole)
                data = child.data(0, Qt.ItemDataRole.UserRole + 2)

                if child_path == current_file:
                    # Use live values for the currently playing video
                    w = current_dur if current_pct >= 90 else current_pos
                    result["watched"] += w
                    result["total"] += current_dur
                else:
                    # Use stored values for other videos
                    if isinstance(data, VideoItemData):
                        d = data.duration
                        p = data.watched_percent
                        pos = data.last_position
                    elif isinstance(data, (tuple, list)) and len(data) >= 8:
                        d = data[1]
                        p = data[4]
                        pos = data[7]
                    else:
                        continue

                    w = d if p >= 90 else pos
                    result["watched"] += w
                    result["total"] += d

                result["count"] += 1

            elif item_type == "folder":
                # Recurse into subfolders
                self._collect_folder_stats(
                    child, current_file, current_pos, current_dur, current_pct
                )
                sub = self._collect_folder_stats_result
                result["watched"] += sub["watched"]
                result["total"] += sub["total"]
                result["count"] += sub["count"]

        self._collect_folder_stats_result = result

    def update_video_item_display(self, file_path, percent, position):
        iterator = QTreeWidgetItemIterator(self.course_tree)
        while iterator.value():
            item = iterator.value()
            if item.data(0, Qt.ItemDataRole.UserRole) == file_path:
                data = item.data(0, Qt.ItemDataRole.UserRole + 2)
                if data:
                    if isinstance(data, VideoItemData):
                        data.watched_percent = percent
                        data.last_position = position
                        item.setData(0, Qt.ItemDataRole.UserRole + 2, data)
                    else:
                        # Handle tuple (legacy)
                        if len(data) >= 11:
                            (
                                filename,
                                duration,
                                resolution,
                                file_size,
                                _,
                                thumbnail_path,
                                thumbnails_list,
                                _,
                                marker_count,
                                is_favorite,
                                tags,
                            ) = data[:11]
                        else:
                            (
                                filename,
                                duration,
                                resolution,
                                file_size,
                                _,
                                thumbnail_path,
                                thumbnails_list,
                                _,
                                marker_count,
                            ) = data
                            is_favorite = 0
                            tags = []

                        item.setData(
                            0,
                            Qt.ItemDataRole.UserRole + 2,
                            (
                                filename,
                                duration,
                                resolution,
                                file_size,
                                percent,
                                thumbnail_path,
                                thumbnails_list,
                                position,
                                marker_count,
                                is_favorite,
                                tags,
                            ),
                        )
                break
            iterator += 1

        self.course_tree.viewport().update()

    def on_markers_changed(self, file_path):
        """Update marker count and list in library when markers are added/removed."""
        new_count = self.db.get_marker_count(file_path)
        new_markers = self.db.get_markers(file_path)

        iterator = QTreeWidgetItemIterator(
            self.course_tree, QTreeWidgetItemIterator.IteratorFlag.All
        )
        while iterator.value():
            item = iterator.value()
            if item.data(0, Qt.ItemDataRole.UserRole) == file_path:
                data = item.data(0, Qt.ItemDataRole.UserRole + 2)
                if data:
                    if isinstance(data, VideoItemData):
                        data.marker_count = new_count
                        data.markers = new_markers
                        item.setData(0, Qt.ItemDataRole.UserRole + 2, data)
                    elif isinstance(data, (tuple, list)):
                        # Legacy tuple handling
                        if len(data) >= 11:
                            lst = list(data)
                            lst[8] = new_count
                            item.setData(0, Qt.ItemDataRole.UserRole + 2, tuple(lst))
                        else:
                            # Try to upgrade to VideoItemData if possible, or just ignore
                            pass

                # If filter is active, re-apply it
                if (
                    self.search_edit.text()
                    or self.fav_filter_btn.isChecked()
                    or self.tag_filter_btn.isChecked()
                ):
                    self.filter_library(self.search_edit.text())

                # Force layout update to recalculate row height (triggers sizeHint)
                self.course_tree.doItemsLayout()
                break
            iterator += 1

    def toggle_markers(self, checked):
        """Toggle marker visibility in library."""
        delegate = self.course_tree.itemDelegate()
        if isinstance(delegate, VideoItemDelegate):
            delegate.config["show_markers"] = checked
            # Refresh layout to update row heights
            self.course_tree.doItemsLayout()
            self.course_tree.viewport().update()

    def on_video_finished(self):
        """Handle video completion with a delay to ensure stability."""
        if self.video_player.current_file:
            current_file = self.video_player.current_file
            # Defer execution to let MPV handle its internal EOF state first
            QTimer.singleShot(200, lambda: self._handle_video_completion(current_file))

    def _handle_video_completion(self, file_path):
        """Actual completion logic after delay."""
        try:
            self.db.mark_video_as_watched(file_path)
            self.load_courses()
        except Exception as e:
            logging.error(f"Error in delayed video completion: {e}")

    def clear_metadata(self):
        """Clear all metadata via main window button."""
        self.clear_metadata_force()

    def clear_metadata_force(self):
        """Clear all metadata from DB and remove thumbnail cache."""
        if not self.db:
            logging.error("Database manager not initialized")
            return False

        try:
            # 1. Clear data via SQL (safe with open connections)
            if not self.db.clear_all_metadata():
                return False

            # 2. Vacuum database file
            self.db.vacuum()

            # 3. Clear thumbnails
            if self.thumbnails_dir.exists():
                import shutil

                try:
                    # Try to remove all subfolders and files
                    for item in self.thumbnails_dir.iterdir():
                        try:
                            if item.is_dir():
                                shutil.rmtree(item)
                            else:
                                item.unlink()
                        except:
                            pass  # Skip if file is busy
                except Exception as e:
                    logging.warning(f"Warning clearing thumbnails: {e}")

            # 4. Unload current video from player
            if hasattr(self, "video_player"):
                self.video_player.unload_video()

            # 5. Reload interface (will be empty)
            self.load_courses()
            return True

        except Exception as e:
            logging.error(f"Error clearing metadata: {e}")
            return False

    def _find_folder_image(self, folder_path):
        """Find a suitable cover image for the folder."""
        if not folder_path or not Path(folder_path).exists():
            return None

        try:
            # Priority 1: Specific names
            priority_names = ["cover", "folder", "poster", "fanart"]
            for name in priority_names:
                for ext in self.folder_image_extensions:
                    p = folder_path / f"{name}{ext}"
                    if p.exists():
                        return str(p)

            # Priority 2: Any image file
            # This can be slow for large folders, so limit to first few
            count = 0
            for item in folder_path.iterdir():
                if (
                    item.is_file()
                    and item.suffix.lower() in self.folder_image_extensions
                ):
                    if "cover" in item.name.lower() or "folder" in item.name.lower():
                        return str(item)
                    # Return first found if loose mode logic is desired?
                    # The user said "if there is some picture take it"
                    return str(item)

                count += 1
                if count > 50:  # Don't scan forever
                    break
        except Exception as e:
            logging.error(f"Error scanning for folder image: {e}")

        return None

    def get_saved_position(self, file_path):
        """Return (last_position, volume) for file."""
        progress = self.db.get_video_progress(file_path)
        if progress:
            return progress["last_position"], progress["volume"]
        return 0, 100

    def on_player_pause_changed(self, is_paused):
        delegate = self.course_tree.itemDelegate()
        if isinstance(delegate, VideoItemDelegate):
            delegate.is_paused = is_paused
            self.course_tree.viewport().update()
        # Sync taskbar thumbnail play/pause button icon
        if hasattr(self, "thumbnail_buttons"):
            self.thumbnail_buttons.update_play_state(not is_paused)

    def toggle_library(self):
        if not hasattr(self, "browser_widget"):
            return

        if self.browser_widget.isVisible():
            self._saved_splitter_state_manual = self.splitter.saveState()
            self.browser_widget.hide()
            self.splitter.setSizes([0, self.width()])
        else:
            self.browser_widget.show()
            if hasattr(self, "_saved_splitter_state_manual"):
                self.splitter.restoreState(self._saved_splitter_state_manual)
            else:
                # Default roughly 30/70 if no state saved
                width = self.splitter.width()
                if width > 0:
                    self.splitter.setSizes([int(width * 0.3), int(width * 0.7)])
                else:
                    self.splitter.setSizes([400, 1000])

        if hasattr(self, "toggle_lib_action"):
            self.toggle_lib_action.setChecked(self.browser_widget.isVisible())

    def toggle_tree_lines(self):
        checked = self.show_tree_lines_action.isChecked()
        delegate = self.course_tree.itemDelegate()
        if hasattr(delegate, "config"):
            delegate.config["show_tree_lines"] = checked
        self.course_tree.viewport().update()
        self.config.set_show_tree_lines(checked)

    def toggle_pureref_badges(self):
        checked = self.show_pureref_badges_action.isChecked()
        delegate = self.course_tree.itemDelegate()
        if hasattr(delegate, "config"):
            delegate.config["show_pureref_badges"] = checked
        self.course_tree.viewport().update()
        self.config.set_show_pureref_badges(checked)

    def toggle_pureref_badges_when_missing(self):
        checked = self.show_pureref_badges_when_missing_action.isChecked()
        delegate = self.course_tree.itemDelegate()
        if hasattr(delegate, "config"):
            delegate.config["show_pureref_badges_when_missing"] = checked
        self.course_tree.viewport().update()
        self.config.set_show_pureref_badges_when_missing(checked)

    def toggle_osd_display(self):
        """Toggle OSD notifications on/off."""
        checked = self.toggle_osd_action.isChecked()
        self.config.set_show_osd(checked)
        if hasattr(self.video_player, "osd_manager") and self.video_player.osd_manager:
            self.video_player.osd_manager.set_enabled(checked)

    def toggle_pip_mode(self):
        """Toggle Picture-in-Picture mode."""
        if self.is_pip_mode:
            self.exit_pip_mode()
        else:
            self.enter_pip_mode()

    def enter_pip_mode(self):
        """Enter Picture-in-Picture mode."""
        if self.is_pip_mode:
            return

        logging.debug("Entering single-window PiP mode")
        self.is_pip_mode = True
        self.normal_geometry = self.saveGeometry()

        # Create overlay
        if not self.pip_overlay:
            # Create it as a top-level window so it's above the native video player
            self.pip_overlay = PiPOverlay(self)
        self.pip_overlay.setGeometry(self.geometry())
        self.pip_overlay.show()
        self.pip_overlay.raise_()

        # Hide UI elements
        self.browser_widget.hide()
        self.menuBar().hide()
        self.statusBar().hide()
        self.video_player.set_controls_visible(False)

        # Lower minimum sizes for PiP
        self.video_player.setMinimumWidth(0)
        self.video_player.video_widget.setMinimumHeight(0)
        self.setMinimumSize(100, 100)

        # Remove margins to allow edge detection at the very boundaries
        if self.centralWidget() and self.centralWidget().layout():
            self.centralWidget().layout().setContentsMargins(0, 0, 0, 0)

        # Install event filter to capture events from ALL PiP area containers and children
        self.video_player.installEventFilter(self)
        self.splitter.installEventFilter(self)
        self.centralWidget().installEventFilter(self)

        # Recursive mouse tracking and event filtering for video player children
        for widget in self.video_player.findChildren(QWidget):
            widget.setMouseTracking(True)
            widget.installEventFilter(self)

        self.setMouseTracking(True)
        self.video_player.setMouseTracking(True)
        self.splitter.setMouseTracking(True)
        self.centralWidget().setMouseTracking(True)

        # Window flags
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )

        # Determine target PiP size based on video aspect ratio
        ratio = self.video_player.get_video_aspect_ratio()

        # Apply PiP geometry
        if self.pip_geometry:
            self.restoreGeometry(self.pip_geometry)
            # Adjust height to match current video ratio if it changed
            curr_geo = self.geometry()
            new_h = int(curr_geo.width() / ratio)
            self.resize(curr_geo.width(), new_h)
        else:
            # Default PiP size and position (bottom right)
            screen = self.screen().availableGeometry()
            pip_w = 480
            pip_h = int(pip_w / ratio)
            self.setGeometry(
                screen.width() - pip_w - 20, screen.height() - pip_h - 20, pip_w, pip_h
            )

        self.show()

        # Flags change might require re-initializing taskbar buttons
        QTimer.singleShot(500, self._refresh_taskbar_buttons)

    def exit_pip_mode(self):
        """Exit Picture-in-Picture mode."""
        if not self.is_pip_mode:
            return

        logging.debug("Exiting single-window PiP mode")
        self.pip_geometry = self.saveGeometry()
        self.is_pip_mode = False

        # Restore window flags
        self.setWindowFlags(Qt.WindowType.Window)

        # Show UI elements
        self.browser_widget.show()
        self.menuBar().show()
        self.statusBar().show()
        self.video_player.set_controls_visible(True)

        # Restore minimum sizes for normal mode
        self.video_player.setMinimumWidth(400)
        self.video_player.video_widget.setMinimumHeight(300)
        self.setMinimumSize(800, 600)

        # Restore margins
        if self.centralWidget() and self.centralWidget().layout():
            self.centralWidget().layout().setContentsMargins(2, 2, 2, 2)

        # Remove event filters
        self.video_player.removeEventFilter(self)
        self.splitter.removeEventFilter(self)
        self.centralWidget().removeEventFilter(self)
        # Recursive cleanup
        if self.video_player:
            from mpv_handler import MPVVideoWidget
            from player import ClickableSlider

            for widget in self.video_player.findChildren(QWidget):
                widget.removeEventFilter(self)
                if not isinstance(widget, (MPVVideoWidget, ClickableSlider)):
                    widget.setMouseTracking(False)

        self.setMouseTracking(False)
        self.video_player.setMouseTracking(False)
        self.splitter.setMouseTracking(False)
        self.centralWidget().setMouseTracking(False)
        self.unsetCursor()
        self.current_hover_edge = None

        if self.pip_overlay:
            self.pip_overlay.hide()
            self.pip_overlay.deleteLater()
            self.pip_overlay = None

        # Restore normal geometry
        if self.normal_geometry:
            self.restoreGeometry(self.normal_geometry)

        self.show()
        self.raise_()
        self.activateWindow()

        # Flags change might require re-initializing taskbar buttons
        QTimer.singleShot(500, self._refresh_taskbar_buttons)

    def _refresh_taskbar_buttons(self):
        """Force refresh of taskbar buttons after window flag changes."""
        if self.taskbar_progress:
            hwnd = int(self.winId())
            self.taskbar_progress.set_hwnd(hwnd)
            if self.taskbar_progress.taskbar:
                self.thumbnail_buttons = TaskbarThumbnailButtons(
                    self.taskbar_progress.taskbar, hwnd, RESOURCES_DIR / "icons"
                )
                self.thumbnail_buttons.add_buttons()

                # Restore play/pause state
                is_playing = (
                    not self.video_player.player.pause
                    if self.video_player and self.video_player.player
                    else False
                )
                self.thumbnail_buttons.update_play_state(is_playing)

                # Restore progress bar state and color
                if self.video_player and self.video_player.current_file:
                    try:
                        total = self.video_player.player.duration or 0
                        current = self.video_player.player.time_pos or 0
                        if total > 0:
                            self.taskbar_progress.update_for_playback(
                                is_playing, current, total
                            )
                    except:
                        pass

    def load_icons(self):
        # List of icons to load for the browser
        icon_names = [
            "menu_scan",
            "menu_settings",
            "menu_reload",
            "menu_about",
            "context_open_folder",
            "context_mark_read",
            "context_mark_unread",
            "context_play",
            "app_icon",
            "screenshot",
            "next_frame",
            "prev_frame",
            "volume_hight",
            "add",
            "context_favorite_on",
            "context_favorite_off",
            "context_tags",
            "show_markers",
            "pip",
            "fullscreen",
            "picture-in-picture",
            "pin",
            "collapse",
            "expand",
            "locate",
        ]
        self.icons = load_icons_dict(icon_names)

        # Set window icon
        if "app_icon" in self.icons:
            self.setWindowIcon(self.icons["app_icon"])

        self.folder_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        self.video_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)

        if self.video_icon.isNull():
            self.video_icon = self.style().standardIcon(
                QStyle.StandardPixmap.SP_FileIcon
            )

    def show_context_menu(self, pos):
        item = self.course_tree.itemAt(pos)
        if not item:
            return

        menu = QMenu()
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)

        if item_type == "video":
            file_path = item.data(0, Qt.ItemDataRole.UserRole)
            saved_pos, _ = self.get_saved_position(file_path)

            if saved_pos > 0:
                resume_action = menu.addAction(
                    self.icons.get("context_play", QIcon()),
                    tr("context_menu.resume", time=format_time(saved_pos)),
                )
                resume_action.triggered.connect(
                    lambda: self.play_video_in_player(item, resume=True)
                )

                restart_action = menu.addAction(
                    self.icons.get("context_play", QIcon()), tr("context_menu.restart")
                )
                restart_action.triggered.connect(
                    lambda: self.play_video_in_player(item, resume=False)
                )
            else:
                play_action = menu.addAction(
                    self.icons.get("context_play", QIcon()), tr("context_menu.play")
                )
                play_action.triggered.connect(lambda: self.play_video_in_player(item))

            play_external_action = menu.addAction(
                self.icons.get("context_play", QIcon()),
                tr("context_menu.play_external"),
            )
            play_external_action.triggered.connect(lambda: self.play_video(item))

            menu.addSeparator()

            # ADDED: Audio track selection submenu
            audio_menu = menu.addMenu(
                self.icons.get("volume_hight", QIcon()), tr("player.audio_tracks")
            )
            self.populate_audio_submenu(audio_menu, file_path, item)

            menu.addSeparator()

            mark_watched_action = menu.addAction(
                self.icons.get("context_mark_read", QIcon()),
                tr("context_menu.mark_watched"),
            )
            mark_watched_action.triggered.connect(lambda: self.mark_as_watched(item))

            reset_action = menu.addAction(
                self.icons.get("context_mark_unread", QIcon()),
                tr("context_menu.reset_progress"),
            )
            reset_action.triggered.connect(lambda: self.reset_video_progress(item))

            menu.addSeparator()

            # Favorites & Tags
            is_fav = False
            data = item.data(0, Qt.ItemDataRole.UserRole + 2)

            if isinstance(data, VideoItemData):
                is_fav = data.is_favorite
            elif data and len(data) >= 10:
                is_fav = bool(data[9])  # is_favorite at index 9

            fav_text = (
                tr("context_menu.remove_favorite")
                if is_fav
                else tr("context_menu.add_favorite")
            )
            fav_icon = (
                self.icons.get("context_favorite_off")
                if is_fav
                else self.icons.get("context_favorite_on")
            )

            fav_action = menu.addAction(fav_icon, fav_text)
            fav_action.triggered.connect(lambda: self.toggle_favorite(item))

            tags_menu = menu.addMenu(
                self.icons.get("context_tags", QIcon()),
                tr("context_menu.tags") or "Tags",
            )

            # Fetch all available tags
            all_tags = self.db.get_tags()

            # Get current video tags
            current_tag_ids = set()
            if isinstance(data, VideoItemData):
                current_tags = data.tags
                current_tag_ids = {t["id"] for t in current_tags}
            elif data and len(data) >= 11:
                current_tags = data[10]
                current_tag_ids = {t["id"] for t in current_tags}

            for tag in all_tags:
                tag_action = tags_menu.addAction(tag["name"])
                tag_action.setCheckable(True)
                tag_action.setChecked(tag["id"] in current_tag_ids)

                # Add color icon
                color_hex = tag["color"] if tag["color"] else "#3498db"
                pixmap = QPixmap(16, 16)
                pixmap.fill(Qt.GlobalColor.transparent)

                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)

                # Draw colored circle/rounded rect background
                painter.setBrush(QColor(color_hex))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(0, 0, 16, 16, 3, 3)

                # Draw dot if checked
                if tag["id"] in current_tag_ids:
                    painter.setBrush(QColor("white"))
                    painter.drawEllipse(5, 5, 6, 6)

                painter.end()

                tag_action.setIcon(QIcon(pixmap))

                tag_action.triggered.connect(
                    lambda checked, t=tag: self.toggle_video_tag_from_menu(
                        item, t, checked
                    )
                )

            tags_menu.addSeparator()

            tag_action = tags_menu.addAction(
                tr("context_menu.edit_tags") or "Edit Tags..."
            )
            tag_action.triggered.connect(lambda: self.edit_tags(item))

            menu.addSeparator()
            open_dir_action = menu.addAction(
                self.icons.get("context_open_folder", QIcon()),
                tr("context_menu.open_directory"),
            )
            open_dir_action.triggered.connect(lambda: self.open_video_directory(item))

        elif item_type == "folder":
            open_action = menu.addAction(
                self.icons.get("context_open_folder", QIcon()),
                tr("context_menu.open_folder"),
            )
            open_action.triggered.connect(lambda: self.open_folder(item))

            menu.addSeparator()

            stats_action = menu.addAction(
                self.icons.get("menu_about", QIcon()), tr("context_menu.folder_stats")
            )
            stats_action.triggered.connect(lambda: self.show_folder_stats(item))

            menu.addSeparator()

            folder_path = item.data(0, Qt.ItemDataRole.UserRole)
            folder_root = item.data(0, Qt.ItemDataRole.UserRole + 3)
            if folder_path and folder_root:
                folder_full = Path(folder_root) / folder_path
                has_pur = self.pureref_manager.has_pur_file(folder_full)
                pureref_text = tr("context_menu.open_pureref") if has_pur else tr("context_menu.create_pureref")
                pureref_action = menu.addAction(pureref_text)
                pureref_action.triggered.connect(lambda: self.open_pureref(item))

                delete_pureref_action = menu.addAction(tr("context_menu.delete_pureref"))
                delete_pureref_action.setEnabled(has_pur)
                delete_pureref_action.triggered.connect(lambda: self.delete_pureref(item))

            menu.addSeparator()

            play_all_action = menu.addAction(
                self.icons.get("context_play", QIcon()), tr("context_menu.play_all")
            )

            play_all_action.triggered.connect(lambda: self.play_folder(item))

            mark_all_action = menu.addAction(
                self.icons.get("context_mark_read", QIcon()),
                tr("context_menu.mark_all_watched"),
            )
            mark_all_action.triggered.connect(lambda: self.mark_folder_as_watched(item))

            reset_all_action = menu.addAction(
                self.icons.get("context_mark_unread", QIcon()),
                tr("context_menu.reset_all_progress"),
            )
            reset_all_action.triggered.connect(lambda: self.reset_folder_progress(item))

        menu.exec(self.course_tree.viewport().mapToGlobal(pos))

    def show_folder_stats(self, item):
        """Shows statistics for the selected folder/course."""
        folder_path = item.data(0, Qt.ItemDataRole.UserRole)

        # We allow showing stats even if the folder doesn't exist on disk,
        # as long as it exists in the database.

        stats = self.db.get_folder_statistics(folder_path)
        if stats:
            dialog = FolderStatsDialog(stats, item.text(0), self)
            dialog.exec()
        else:
            QMessageBox.warning(
                self,
                tr("status.error"),
                tr("error.folder_not_found", folder=folder_path),
            )

    # ADDED: Context menu audio track methods
    def populate_audio_submenu(self, menu, filepath, item):
        """Populate audio submenu."""
        try:
            video_info = self.db.get_video_info(filepath)
            if not video_info:
                return

            video_id = video_info["id"]
            tracks, selected_audio_id = self.db.load_audio_tracks(filepath)

            if not tracks:
                menu.addAction(tr("player.no_tracks")).setEnabled(False)
                return

            action_group = QActionGroup(self)
            action_group.setExclusive(True)

            for track in tracks:
                track_id = track["id"]
                track_type = track["track_type"]
                stream_index = track["stream_index"]
                audio_file_name = track["audio_file_name"]
                language = track["language"]
                title = track["title"]
                codec = track["codec"]
                channels = track["channels"]
                is_default = track["is_default"]

                label = format_audio_track_name(track)

                if is_default:
                    label += f" [{tr('player.default')}]"

                action = menu.addAction(self.icons.get("volume_hight", QIcon()), label)
                action.setCheckable(True)
                action.setChecked(track_id == selected_audio_id)
                action.setActionGroup(action_group)
                action.triggered.connect(
                    lambda checked,
                    tid=track_id,
                    fp=filepath: self.set_audio_track_for_file(tid, fp, item)
                )

        except Exception as e:
            logging.error(f"Error populating audio submenu: {e}")

    def set_audio_track_for_file(self, track_id, filepath, item):
        """Set audio track for file."""
        try:
            self.db.save_selected_audio(filepath, track_id)

            # If current file, switch track
            if self.video_player.current_file == filepath:
                # This will trigger change_audio_track in VideoPlayerWidget
                # which will then update the player and save to DB again (redundant but safe)
                for i in range(self.video_player.volume_btn.popup.audioCount()):
                    if self.video_player.volume_btn.popup.audioItemData(i) == track_id:
                        self.video_player.volume_btn.popup.setAudioIndex(i)
                        self.video_player.change_audio_track(i)
                        break

        except Exception as e:
            logging.error(f"Error setting audio track: {e}")

    def toggle_favorite(self, item):
        """Toggle favorite status for item."""
        try:
            logging.debug(f"toggle_favorite called for item: {item}")
            file_path = item.data(0, Qt.ItemDataRole.UserRole)
            logging.debug(f"file_path: {file_path}")
            data = item.data(0, Qt.ItemDataRole.UserRole + 2)
            logging.debug(f"current data type: {type(data)}")

            # Determine current state
            is_fav = False
            if isinstance(data, VideoItemData):
                is_fav = data.is_favorite
            elif data and len(data) >= 10:
                is_fav = bool(data[9])

            new_state = not is_fav
            logging.debug(f"Toggling favorite to: {new_state}")

            if self.db.toggle_favorite(file_path, new_state):
                # Refresh this item's data
                if isinstance(data, VideoItemData):
                    data.is_favorite = new_state
                    item.setData(0, Qt.ItemDataRole.UserRole + 2, data)
                elif data and len(data) >= 10:
                    lst = list(data)
                    # Ensure list is long enough
                    while len(lst) < 10:
                        lst.append(0)
                    if len(lst) == 10:
                        lst.append([])  # tags

                    lst[9] = 1 if new_state else 0  # Toggle
                    item.setData(0, Qt.ItemDataRole.UserRole + 2, tuple(lst))
                else:
                    logging.debug(
                        "Data format not recognized or incomplete, reloading courses"
                    )
                    self.load_courses()  # Fallback
                self.course_tree.viewport().update()
            else:
                logging.error("Failed to toggle favorite in DB")
        except Exception as e:
            logging.error(f"Error in toggle_favorite: {e}", exc_info=True)
            QMessageBox.critical(
                self, tr("error.title"), f"Error toggling favorite: {e}"
            )

    def edit_tags(self, item):
        """Open tags dialog."""
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        dialog = TagsDialog(self, self.db, file_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # We need to refresh the tags on the item
            new_tags = self.db.get_video_tags(file_path)
            data = item.data(0, Qt.ItemDataRole.UserRole + 2)

            if isinstance(data, VideoItemData):
                data.tags = new_tags
                item.setData(0, Qt.ItemDataRole.UserRole + 2, data)
                self.course_tree.viewport().update()
            elif data and len(data) >= 11:
                lst = list(data)
                lst[10] = new_tags
                item.setData(0, Qt.ItemDataRole.UserRole + 2, tuple(lst))
                self.course_tree.viewport().update()
            else:
                self.load_courses()

    def toggle_video_tag_from_menu(self, item, tag, checked):
        """Toggle a tag on a video from the context menu."""
        file_path = item.data(0, Qt.ItemDataRole.UserRole)

        if checked:
            success = self.db.add_tag_to_video(file_path, tag["id"])
        else:
            success = self.db.remove_tag_from_video(file_path, tag["id"])

        if success:
            # Update item data
            data = item.data(0, Qt.ItemDataRole.UserRole + 2)

            if isinstance(data, VideoItemData):
                current_tags = list(data.tags)  # Copy
                if checked:
                    if not any(t["id"] == tag["id"] for t in current_tags):
                        current_tags.append(tag)
                else:
                    current_tags = [t for t in current_tags if t["id"] != tag["id"]]

                data.tags = current_tags
                # Trigger update
                item.setData(0, Qt.ItemDataRole.UserRole + 2, data)
                self.course_tree.viewport().update()

            elif isinstance(data, (tuple, list)) and len(data) >= 11:
                lst = list(data)
                current_tags = list(lst[10])  # Copy the list of tags

                if checked:
                    # Add if not exists (shouldn't exist if checked was false before)
                    if not any(t["id"] == tag["id"] for t in current_tags):
                        current_tags.append(tag)
                else:
                    # Remove
                    current_tags = [t for t in current_tags if t["id"] != tag["id"]]

                # Update list in tuple
                lst[10] = current_tags
                item.setData(0, Qt.ItemDataRole.UserRole + 2, tuple(lst))
                self.course_tree.viewport().update()
            else:
                self.load_courses()  # Fallback

    def item_double_clicked(self, item):
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)

        if item_type == "video":
            self.play_video_in_player(item, resume=True)
        elif item_type == "folder":
            item.setExpanded(not item.isExpanded())

    def play_next_video(self):
        current_file = self.video_player.current_file or self.last_played_path
        if not current_file:
            return

        current_item = self.find_video_item(current_file)
        if not current_item:
            return

        # Determine if we should auto-play the next video
        # If player is currently playing (not paused), then auto-play next
        # Or if the config setting 'autoplay_on_next' is enabled
        should_play = self.config.get_autoplay_on_next()
        if self.video_player.player and not should_play:
            should_play = not self.video_player.player.pause

        iterator = QTreeWidgetItemIterator(
            self.course_tree, QTreeWidgetItemIterator.IteratorFlag.All
        )
        # Advance to current
        while iterator.value():
            item = iterator.value()
            iterator += 1
            if item == current_item:
                break

        # Continue to find next video
        while iterator.value():
            item = iterator.value()
            item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if item_type == "video":
                # Get the name of the next video for OSD
                next_file_path = item.data(0, Qt.ItemDataRole.UserRole)
                next_filename = Path(next_file_path).name

                # Show OSD notification before playing
                if (
                    hasattr(self.video_player, "osd_manager")
                    and self.video_player.osd_manager
                ):
                    self.video_player.osd_manager.show_next_video(next_filename)

                self.play_video_in_player(item, resume=True, auto_play=should_play)
                self.course_tree.scrollToItem(item)
                self.course_tree.setCurrentItem(item)
                return
            iterator += 1

    def play_prev_video(self):
        current_file = self.video_player.current_file or self.last_played_path
        if not current_file:
            return

        current_item = self.find_video_item(current_file)
        if not current_item:
            return

        # Determine if we should auto-play the prev video
        # Or if the config setting 'autoplay_on_prev' is enabled
        should_play = self.config.get_autoplay_on_prev()
        if self.video_player.player and not should_play:
            should_play = not self.video_player.player.pause

        iterator = QTreeWidgetItemIterator(
            self.course_tree, QTreeWidgetItemIterator.IteratorFlag.All
        )
        last_video_item = None

        while iterator.value():
            item = iterator.value()
            if item == current_item:
                if last_video_item:
                    # Get the name of the previous video for OSD
                    prev_file_path = last_video_item.data(0, Qt.ItemDataRole.UserRole)
                    prev_filename = Path(prev_file_path).name

                    # Show OSD notification before playing
                    if (
                        hasattr(self.video_player, "osd_manager")
                        and self.video_player.osd_manager
                    ):
                        self.video_player.osd_manager.show_prev_video(prev_filename)

                    self.play_video_in_player(
                        last_video_item, resume=True, auto_play=should_play
                    )
                    self.course_tree.scrollToItem(last_video_item)
                    self.course_tree.setCurrentItem(last_video_item)
                return

            item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if item_type == "video":
                last_video_item = item
            iterator += 1

    def update_navigation_buttons(self, current_item):
        """Enable or disable Prev/Next buttons based on position in tree."""
        if not current_item:
            self.video_player.prev_video_btn.setEnabled(False)
            self.video_player.next_video_btn.setEnabled(False)
            return

        # Check for previous video
        has_prev = False
        iterator = QTreeWidgetItemIterator(
            self.course_tree, QTreeWidgetItemIterator.IteratorFlag.All
        )
        while iterator.value():
            item = iterator.value()
            if item == current_item:
                break
            if item.data(0, Qt.ItemDataRole.UserRole + 1) == "video":
                has_prev = True
            iterator += 1

        # Check for next video
        has_next = False
        if iterator.value() == current_item:
            iterator += 1
            while iterator.value():
                if iterator.value().data(0, Qt.ItemDataRole.UserRole + 1) == "video":
                    has_next = True
                    break
                iterator += 1

        self.video_player.prev_video_btn.setEnabled(has_prev)
        self.video_player.next_video_btn.setEnabled(has_next)

    def play_video_at_marker(self, file_path, position):
        """Play video starting at specific position (from marker click)."""
        if not file_path or not Path(file_path).exists():
            return

        # Find item to select it in the tree
        item = self.find_video_item(file_path)
        if item:
            self.course_tree.setCurrentItem(item)
            self.course_tree.scrollToItem(item)
            self.update_window_title_for_item(item)

        # Load video
        self.video_player.load_video(file_path, position, auto_play=True)

        # Update delegate state
        delegate = self.course_tree.itemDelegate()
        if isinstance(delegate, VideoItemDelegate):
            delegate.playing_path = file_path
            delegate.is_paused = False
            self.course_tree.viewport().update()

    def play_video_in_player(self, item, resume=False, auto_play=True):
        logging.debug("play_video_in_player called")

        # Save progress and update folder stats for the PREVIOUS video before switching
        if self.video_player.current_file:
            self.periodic_progress_save(force_stats_update=True)
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        logging.debug(f"file_path: {file_path}")

        self.last_played_path = file_path

        if file_path and Path(file_path).exists():
            saved_position = 0
            saved_volume = 100
            if resume:
                saved_position, saved_volume = self.get_saved_position(file_path)

            self.video_player.load_video(
                file_path, saved_position, volume=saved_volume, auto_play=auto_play
            )
            # Update delegate
            delegate = self.course_tree.itemDelegate()
            if isinstance(delegate, VideoItemDelegate):
                delegate.playing_path = file_path
                delegate.is_paused = not auto_play
                self.course_tree.viewport().update()

            # self.video_player.restore_audio_track(file_path)
            self.update_window_title_for_item(item)
            self.update_navigation_buttons(item)

    def play_video_at_marker(self, file_path, position):
        """Play video starting at specific marker position."""
        # Check if file exists
        if not Path(file_path).exists():
            QMessageBox.warning(self, tr("app.error"), tr("player.file_not_found"))
            return

        item = self.find_video_item(file_path)
        if item:
            # If it's the same file currently playing, just seek
            if self.video_player.current_file == str(Path(file_path)):
                self.video_player.player.seek(position, "absolute")
                if not self.video_player.is_playing:
                    self.video_player.play_pause()
            else:
                # Otherwise load and play
                # We play, but we need to ensure position is set.
                # play_video_in_player logic usually resumes or starts from 0.
                # Let's use load_video directly for explicit control?
                # But play_video_in_player handles UI updates (selection, etc).

                # Let's call load_video directly on video_player as it seems safest for custom pos.
                # And then update UI.

                self.video_player.load_video(file_path, position, auto_play=True)

                # Update UI state similar to play_video_in_player
                self.course_tree.setCurrentItem(item)
                self.course_tree.scrollToItem(item)
                self.update_window_title_for_item(item)

                # Update delegate state
                delegate = self.course_tree.itemDelegate()
                if isinstance(delegate, VideoItemDelegate):
                    delegate.playing_path = file_path
                    delegate.is_paused = False
                    self.course_tree.viewport().update()

    def play_video(self, item):
        file_path = item.data(0, Qt.ItemDataRole.UserRole)

        if file_path and Path(file_path).exists():
            import os

            os.startfile(file_path)
            self.mark_as_watched(item)

    def mark_as_watched(self, item):
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        self.db.mark_video_as_watched(file_path)
        self.load_courses()

    def mark_folder_as_watched(self, item):
        folder_path = item.data(0, Qt.ItemDataRole.UserRole)
        self.db.mark_folder_as_watched(folder_path)
        self.load_courses()

    def reset_folder_progress(self, item):
        folder_path = item.data(0, Qt.ItemDataRole.UserRole)
        self.db.reset_folder_progress(folder_path)
        self.load_courses()

    def play_folder(self, item):
        if item.childCount() > 0:
            first_child = item.child(0)
            if first_child.data(0, Qt.ItemDataRole.UserRole + 1) == "video":
                self.play_video_in_player(first_child, resume=True)

    def open_folder(self, item):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        root_path = item.data(0, Qt.ItemDataRole.UserRole + 3)

        if path and root_path:
            import os

            folder = Path(root_path) / path

            if folder.exists():
                logging.debug(folder)
                os.startfile(folder)
            else:
                QMessageBox.warning(
                    self, tr("error.title"), tr("error.folder_not_found", folder=folder)
                )

    def open_pureref(self, item):
        """Open or create PureRef file for the folder."""
        import traceback
        logging.info(f"[PUREREF] open_pureref called from: {''.join(traceback.format_stack()[-3:-1])}")
        
        path = item.data(0, Qt.ItemDataRole.UserRole)
        root_path = item.data(0, Qt.ItemDataRole.UserRole + 3)

        if not path or not root_path:
            return

        folder = Path(root_path) / path
        logging.info(f"[PUREREF] Opening PureRef for folder: {folder}")
        
        if not folder.exists():
            QMessageBox.warning(
                self,
                tr("error.title"),
                tr("error.folder_not_found", folder=str(folder)),
            )
            return

        success, error = self.pureref_manager.open(folder)
        if not success:
            if error.startswith("pureref_not_found:"):
                exe_path = error.split(":", 1)[1]
                msg = tr("pureref.exe_not_found", path=exe_path)
            else:
                err_detail = error.split(":", 1)[1] if ":" in error else error
                msg = tr("pureref.launch_error", error=err_detail)
            QMessageBox.warning(self, tr("error.title"), msg)

    def delete_pureref(self, item):
        """Delete PureRef file for the folder."""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        root_path = item.data(0, Qt.ItemDataRole.UserRole + 3)

        if not path or not root_path:
            return

        folder = Path(root_path) / path
        
        if not self.pureref_manager.has_pur_file(folder):
            return

        file_size = self.pureref_manager.get_file_size(folder)
        
        if file_size > 0:
            reply = QMessageBox.question(
                self,
                tr("dialog.confirm"),
                tr("pureref.confirm_delete_nonempty"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        success, error = self.pureref_manager.delete(folder)
        if success:
            self.info_label.setText(tr("pureref.delete_success"))
            QTimer.singleShot(3000, lambda: self.info_label.clear())
        else:
            msg = tr("pureref.delete_error", error=error.split(":", 1)[1] if ":" in error else error)
            QMessageBox.warning(self, tr("error.title"), msg)

        self.load_courses()

    def open_video_directory(self, item):
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if file_path and Path(file_path).exists():
            import os

            folder = Path(file_path).parent
            if folder.exists():
                os.startfile(folder)
            else:
                QMessageBox.warning(
                    self, tr("error.title"), tr("error.folder_not_found", folder=folder)
                )
        else:
            QMessageBox.warning(
                self, tr("error.title"), tr("error.folder_path_unknown")
            )

    def reset_video_progress(self, item):
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        self.db.reset_video_progress(file_path)
        self.load_courses()

    def play_video_at_marker(self, file_path, position):
        """Play video starting at specific position."""
        try:
            # Find item in tree
            target_item = self.find_video_item(file_path)

            if target_item:
                # If same file, just seek
                if self.video_player.current_file == str(Path(file_path)):
                    self.video_player.player.seek(position, "absolute", "exact")
                    if not self.video_player.is_playing:
                        self.video_player.play_pause()
                else:
                    # Load video at specific position
                    self.video_player.load_video(file_path, position, auto_play=True)

                    # Update UI
                    self.course_tree.setCurrentItem(target_item)
                    self.course_tree.scrollToItem(target_item)
                    self.update_window_title_for_item(target_item)

                    delegate = self.course_tree.itemDelegate()
                    if isinstance(delegate, VideoItemDelegate):
                        delegate.playing_path = str(Path(file_path))
                        delegate.is_paused = False
                        self.course_tree.viewport().update()
            else:
                logging.warning(f"Item not found for marker play: {file_path}")
        except Exception as e:
            logging.error(f"Error in play_video_at_marker: {e}", exc_info=True)

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self, tr("dialog.select_directory"), self.path_edit.text()
        )

        if directory:
            self.path_edit.setText(directory)

    def scan_single_directory(self, path):
        try:
            from scanner import VideoScanner
        except ImportError:
            self.info_label.setText(tr("status.scanner_not_found"))
            return 0, 0

        scanner = VideoScanner(str(self.config_file.name))
        return scanner.scan_directory(path)

    def rescan_directories(self, paths=None):
        # If no paths provided, load from config
        if paths is None or isinstance(paths, bool):
            all_paths = self.config.get_library_paths().split(";")
            excluded_set = self.config.get_excluded_library_paths()

            paths = [
                p.strip()
                for p in all_paths
                if p.strip() and os.path.normpath(p.strip()) not in excluded_set
            ]

            if not paths:
                QMessageBox.warning(
                    self, tr("settings.warning"), tr("settings.specify_path")
                )
                return

        # Show progress dialog with console output
        dialog = ScanProgressDialog(self)
        dialog.start_scan(self.config_file, paths, self.ffmpeg_path, self.ffprobe_path)
        dialog.scanner_thread.finished_scan.connect(
            lambda v, f: self._on_scan_complete(v, f)
        )
        dialog.exec()

    def _on_scan_complete(self, total_videos, total_folders):
        self.info_label.setText(
            tr("status.found", folders=total_folders, videos=total_videos)
        )
        # Refresh courses immediately while dialog might still be open
        self.load_courses()

    def load_settings(self):
        lang = self.config.get_language()
        tr.load_language(lang)
        self.show_preview_popup = self.config.get_show_preview_popup()
        self.fav_filter_active = self.config.get_fav_filter_active()
        self.tag_filter_active = self.config.get_tag_filter_active()
        self.selected_tag_ids = self.config.get_selected_tag_ids()

        self.library_paths = self.config.get_library_paths()
        self.excluded_library_paths = self.config.get_excluded_library_paths()
        self.thumbnails_dir = self.config.get_thumbnails_dir()

        # Binary files - use raw config for resolve_binary_path
        raw_config = self.config.get_raw_config()
        self.ffmpeg_path = resolve_binary_path(
            raw_config, "ffmpeg_path", "bin/ffmpeg.exe"
        )
        self.ffprobe_path = resolve_binary_path(
            raw_config, "ffprobe_path", "bin/ffprobe.exe"
        )
        self.libmpv_path = resolve_binary_path(
            raw_config, "libmpv_path", "bin/libmpv-2.dll"
        )

        self.window_width = self.config.get_window_width()
        self.window_height = self.config.get_window_height()
        self.video_row_height = self.config.get_video_row_height()
        self.folder_row_height = self.config.get_folder_row_height()

        self.folder_image_extensions = self.config.get_folder_image_extensions()

        self.display_width = self.config.get_display_width()
        self.display_height = self.config.get_display_height()
        self.animation_interval = self.config.get_animation_interval()

        # Subtitle settings
        self.sub_color, self.sub_border_color, self.sub_scale = (
            self.config.get_subtitle_settings()
        )

    def save_subtitle_settings(self, property_name, value):
        """Save subtitle style settings to ini file."""
        self.config.save_subtitle_setting(property_name, value)

    # format_time, format_duration, format_size moved to utils.py

    def load_courses(self):
        """Load courses from DB and build tree."""
        logging.debug("load_courses start")
        folder_font = QFont()
        folder_font.setBold(True)

        # Safety: Disable progress timer and hover during reload
        if hasattr(self, "progress_save_timer"):
            self.progress_save_timer.stop()

        self.course_tree.stop_hover()
        self.course_tree.blockSignals(True)
        self.course_tree.clear()

        delegate = self.course_tree.itemDelegate()
        if isinstance(delegate, VideoItemDelegate):
            delegate.thumbnail_cache.clear()

        if not self.db_file.exists():
            self.info_label.setText(tr("status.db_not_found"))
            return

        folders, videos = self.db.get_courses()

        # Index folders
        folder_items = {}
        folders_data = {}
        for f in folders:
            folders_data[f["path"]] = f

        # Calculate folder stats
        # 1. Initialize for all folders
        folder_stats = {}
        for f in folders:
            folder_stats[f["path"]] = {"watched": 0.0, "total": 0.0, "count": 0}

        # 2. Add direct video stats
        for v in videos:
            f_path = v["folder_path"]
            # If for some reason video folder is not in folders list (shouldn't happen with FK)
            if f_path not in folder_stats:
                folder_stats[f_path] = {"watched": 0.0, "total": 0.0, "count": 0}

            p = v["watched_percent"]
            d = v["duration"]
            pos = v["last_position"]

            # Logic: if watched >= 90%, count full duration. Else use last position.
            w = d if p >= 90 else pos

            folder_stats[f_path]["watched"] += w
            folder_stats[f_path]["total"] += d
            folder_stats[f_path]["count"] += 1

        # 3. Aggregate recursively (Deepest first)
        # Sort by path length (depth) descending to ensure children are processed before parents
        # We use strict string length as a proxy for depth, or count separators
        sorted_folders = sorted(
            folders, key=lambda x: len(Path(x["path"]).parts), reverse=True
        )

        for f in sorted_folders:
            parent_path = f["parent_path"]
            if parent_path and parent_path in folder_stats:
                child_stats = folder_stats[f["path"]]
                if child_stats["count"] > 0:
                    folder_stats[parent_path]["watched"] += child_stats["watched"]
                    folder_stats[parent_path]["total"] += child_stats["total"]
                    folder_stats[parent_path]["count"] += child_stats["count"]

        # Default folder cover image
        default_cover = str(RESOURCES_DIR / "icons" / "folder_cover.png")

        # Create root folders first (no parent in DB or parent not in list)
        for f in folders:
            # Skip excluded paths (and their children potentially, but simplistic check on root_path here)
            # Use strict string comparison for now, assuming paths are normalized in DB/config
            if os.path.normpath(f["root_path"]) in self.excluded_library_paths:
                continue

            if not f["parent_path"] or f["parent_path"] not in folders_data:
                item = QTreeWidgetItem(self.course_tree)
                item.setText(0, f["name"])

                stats_text = ""
                # Use calculated stats if available, else fallback to DB (though DB count should match)
                f_stats = folder_stats.get(f["path"])

                if f_stats and f_stats["count"] > 0:
                    count = f_stats["count"]
                    total = f_stats["total"]
                    watched = f_stats["watched"]
                    percent = int((watched / total * 100)) if total > 0 else 0

                    # Format: "X videos • Watched / Total (Y%)"
                    duration_str = format_duration(total)
                    watched_str = format_duration(watched)

                    stats_text = (
                        f"{count} videos • {watched_str} / {duration_str} ({percent}%)"
                    )
                elif f["video_count"] > 0:
                    # Fallback if video list didn't have them for some reason (e.g. filter mismatch?)
                    stats_text = f"{f['video_count']} videos • {format_duration(f['total_duration'])}"
                    percent = 0

                item.setFont(0, folder_font)
                item.setData(0, Qt.ItemDataRole.UserRole, f["path"])
                item.setData(0, Qt.ItemDataRole.UserRole + 1, "folder")
                item.setData(
                    0, Qt.ItemDataRole.UserRole + 5, stats_text
                )  # Store stats separately
                item.setData(
                    0,
                    Qt.ItemDataRole.UserRole + 6,
                    percent if "percent" in locals() else 0,
                )  # Store progress percent
                # Store raw stats for live updates
                if f_stats:
                    item.setData(0, Qt.ItemDataRole.UserRole + 7, f_stats.copy())
                else:
                    item.setData(
                        0,
                        Qt.ItemDataRole.UserRole + 7,
                        {"watched": 0.0, "total": 0.0, "count": 0},
                    )

                item.setData(
                    0, Qt.ItemDataRole.UserRole + 3, f["root_path"]
                )  # Store root_path

                # Find folder image
                full_path = (
                    Path(f["root_path"]) / f["path"]
                    if f["path"] != "."
                    else Path(f["root_path"])
                )
                cover_image = self._find_folder_image(full_path) or default_cover
                item.setData(0, Qt.ItemDataRole.UserRole + 4, cover_image)

                # Icon (we might not need the default icon if drawing custom)
                # item.setIcon(0, self.folder_icon)

                folder_items[f["path"]] = item
                if f.get("is_expanded"):
                    item.setExpanded(True)

        # Now insert remaining folders (multiple passes if needed)
        max_iterations = 10
        for _ in range(max_iterations):
            added_any = False
            for f in folders:
                if os.path.normpath(f["root_path"]) in self.excluded_library_paths:
                    continue

                if f["path"] in folder_items:
                    continue

                if f["parent_path"] in folder_items:
                    parent_item = folder_items[f["parent_path"]]
                    item = QTreeWidgetItem(parent_item)

                    item.setText(0, f["name"])

                    stats_text = ""
                    f_stats = folder_stats.get(f["path"])

                    if f_stats and f_stats["count"] > 0:
                        count = f_stats["count"]
                        total = f_stats["total"]
                        watched = f_stats["watched"]
                        percent = int((watched / total * 100)) if total > 0 else 0

                        duration_str = format_duration(total)
                        watched_str = format_duration(watched)

                        stats_text = f"{count} videos • {watched_str} / {duration_str} ({percent}%)"
                    elif f["video_count"] > 0:
                        stats_text = f"{f['video_count']} videos • {format_duration(f['total_duration'])}"
                        percent = 0

                    item.setFont(0, folder_font)
                    item.setData(0, Qt.ItemDataRole.UserRole, f["path"])
                    item.setData(0, Qt.ItemDataRole.UserRole + 1, "folder")
                    item.setData(
                        0, Qt.ItemDataRole.UserRole + 5, stats_text
                    )  # Store stats separately
                    item.setData(
                        0,
                        Qt.ItemDataRole.UserRole + 6,
                        percent if "percent" in locals() else 0,
                    )  # Store progress percent
                    # Store raw stats for live updates
                    if f_stats:
                        item.setData(0, Qt.ItemDataRole.UserRole + 7, f_stats.copy())
                    else:
                        item.setData(
                            0,
                            Qt.ItemDataRole.UserRole + 7,
                            {"watched": 0.0, "total": 0.0, "count": 0},
                        )

                    item.setData(
                        0, Qt.ItemDataRole.UserRole + 3, f["root_path"]
                    )  # Store root_path

                    # Find folder image
                    full_path = Path(f["root_path"]) / f["path"]
                    cover_image = self._find_folder_image(full_path) or default_cover
                    item.setData(0, Qt.ItemDataRole.UserRole + 4, cover_image)

                    # item.setIcon(0, self.folder_icon)

                    folder_items[f["path"]] = item
                    if f.get("is_expanded"):
                        item.setExpanded(True)
                    added_any = True

            if not added_any:
                break

        # Add videos
        for v in videos:
            if v["folder_path"] in folder_items:
                parent_item = folder_items[v["folder_path"]]
                video_item = QTreeWidgetItem(parent_item)

                display_name = v["file_name"]
                if v["track_number"]:
                    display_name = f"{v['track_number']}. {display_name}"

                video_item.setText(0, display_name)
                video_item.setData(0, Qt.ItemDataRole.UserRole, v["file_path"])
                video_item.setData(0, Qt.ItemDataRole.UserRole + 1, "video")

                thumbnails_list = []
                if v["thumbnails_json"]:
                    try:
                        thumbnails_list = json.loads(v["thumbnails_json"])
                    except:
                        pass

                # Data for delegate using VideoItemData
                try:
                    video_data = VideoItemData(
                        filename=v["file_name"],
                        duration=v["duration"],
                        resolution=v["resolution"],
                        file_size=v["file_size"],
                        watched_percent=v["watched_percent"] or 0,
                        thumbnail_path=v["thumbnail_path"],
                        thumbnails_list=thumbnails_list,
                        last_position=v["last_position"] or 0,
                        marker_count=v["marker_count"] or 0,
                        is_favorite=bool(v.get("is_favorite", 0)),
                        tags=v.get("tags", []),
                        markers=v.get("markers", []),
                    )
                    video_item.setData(0, Qt.ItemDataRole.UserRole + 2, video_data)
                except Exception as e:
                    logging.critical(
                        f"CRITICAL ERROR creating VideoItemData for {v.get('file_name')}: {e}",
                        exc_info=True,
                    )

                video_item.setIcon(0, self.video_icon)
                # Disable selection for video rows
                video_item.setFlags(video_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        self.course_tree.blockSignals(False)

        # Re-enable progress timer
        if hasattr(self, "progress_save_timer"):
            self.progress_save_timer.start(1000)

        # Info panel statistics
        folder_count = len(folders)
        video_count = len(videos)
        thumb_count = sum(1 for v in videos if v.get("thumbnails_json"))
        resumed_count = sum(1 for v in videos if v.get("last_position", 0) > 0)

        self.info_label.setText(
            tr(
                "status.loaded",
                folders=folder_count,
                videos=video_count,
                thumbs=thumb_count,
                resumed=resumed_count,
            )
        )

        # Apply current filter if any
        search_text = self.search_edit.text() if hasattr(self, "search_edit") else ""
        fav_active = hasattr(self, "fav_filter_btn") and self.fav_filter_btn.isChecked()
        tag_active = hasattr(self, "tag_filter_btn") and self.tag_filter_btn.isChecked()

        if search_text or fav_active or tag_active:
            self.filter_library(search_text)

    def show_tag_filter_popup(self, pos):
        """Show the tag filter selection popup."""
        all_tags = self.db.get_tags()
        self.tag_popup = TagFilterPopup(all_tags, self.selected_tag_ids, self)

        # Position popup above or below the button
        button_pos = self.tag_filter_btn.mapToGlobal(QPoint(0, 0))
        self.tag_popup.move(
            button_pos.x(), button_pos.y() + self.tag_filter_btn.height()
        )

        self.tag_popup.filter_changed.connect(self._on_tag_filter_changed)
        self.tag_popup.show()

    def _on_tag_filter_changed(self, selected_ids):
        """Handle change in tag selection from the popup."""
        self.selected_tag_ids = selected_ids
        # If filter is active, refresh library
        if self.tag_filter_btn.isChecked():
            self.filter_library(self.search_edit.text())

    def filter_library(self, text):
        """Filter library items by text, favorites and tags."""
        query = text.lower()
        fav_only = hasattr(self, "fav_filter_btn") and self.fav_filter_btn.isChecked()
        tag_ids = (
            self.selected_tag_ids
            if (
                hasattr(self, "tag_filter_btn")
                and self.tag_filter_btn.isChecked()
                and self.selected_tag_ids
            )
            else None
        )

        # Hide progress save timer during bulk operations
        if hasattr(self, "progress_save_timer"):
            self.progress_save_timer.stop()

        self.course_tree.setUpdatesEnabled(False)
        self.course_tree.blockSignals(True)

        try:
            for i in range(self.course_tree.topLevelItemCount()):
                item = self.course_tree.topLevelItem(i)
                self._apply_filter(item, query, fav_only=fav_only, tag_ids=tag_ids)
        finally:
            self.course_tree.blockSignals(False)
            self.course_tree.setUpdatesEnabled(True)
            self.course_tree.viewport().update()

            # Re-enable timer if needed (it will be started in load_courses or similar if active)
            if hasattr(self, "progress_save_timer"):
                self.progress_save_timer.start(1000)

    def _apply_filter(
        self, item, query, fav_only=False, tag_ids=None, parent_matches=False
    ):
        """Recursively apply filter to item and children."""
        item_text = item.text(0).lower()
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)

        # Favorite check
        is_favorite = False
        if item_type == "video":
            data = item.data(0, Qt.ItemDataRole.UserRole + 2)
            if isinstance(data, VideoItemData):
                is_favorite = data.is_favorite
            elif data and len(data) >= 10:
                is_favorite = bool(data[9])

        # Tag check
        tag_match = True
        if tag_ids is not None and item_type == "video":
            # Tags are stored in UserRole + 2, at index 10
            data = item.data(0, Qt.ItemDataRole.UserRole + 2)
            if isinstance(data, VideoItemData):
                item_tags = data.tags
                tag_match = any(t["id"] in tag_ids for t in item_tags)
            elif data and len(data) >= 11:
                item_tags = data[10]
                tag_match = any(t["id"] in tag_ids for t in item_tags)
            else:
                tag_match = False

        # Text search (also check tags names in text search)
        text_matches_item = smart_search(query, item_text)
        if query and not text_matches_item and item_type == "video":
            data = item.data(0, Qt.ItemDataRole.UserRole + 2)
            if isinstance(data, VideoItemData):
                item_tags = data.tags
                text_matches_item = any(
                    smart_search(query, t["name"]) for t in item_tags
                )
                if not text_matches_item and data.markers:
                    text_matches_item = any(
                        smart_search(query, m["label"]) for m in data.markers
                    )

            elif data and len(data) >= 11:
                item_tags = data[10]
                text_matches_item = any(
                    smart_search(query, t["name"]) for t in item_tags
                )

        # Logic for this item
        text_match = text_matches_item or parent_matches

        item_matches = text_match
        if fav_only and item_type == "video":
            item_matches = item_matches and is_favorite
        if tag_ids is not None and item_type == "video":
            item_matches = item_matches and tag_match

        child_visible = False
        for i in range(item.childCount()):
            if self._apply_filter(
                item.child(i), query, fav_only, tag_ids, item_matches
            ):
                child_visible = True

        # Visibility decision
        is_visible = False
        if item_type == "video":
            is_visible = item_matches
        else:
            # Folder visibility
            if fav_only or tag_ids:
                is_visible = child_visible
            else:
                is_visible = text_match or child_visible

        item.setHidden(not is_visible)

        if (query or fav_only or tag_ids) and child_visible:
            item.setExpanded(True)

        return is_visible

    def showEvent(self, event):
        logging.debug("showEvent start")
        super().showEvent(event)
        self.setFocus()
        if self.taskbar_progress:
            try:
                hwnd = int(self.winId())
                self.taskbar_progress.set_hwnd(hwnd)

                # Sync state with player
                if self.video_player.current_file:
                    is_playing = (
                        not self.video_player.player.pause
                        if self.video_player.player
                        else False
                    )
                    if is_playing:
                        self.taskbar_progress.set_normal()
                    else:
                        self.taskbar_progress.set_paused()
                else:
                    self.taskbar_progress.set_normal()

                # Initialize thumbnail toolbar buttons (5 playback controls)
                if self.taskbar_progress.taskbar:
                    self.thumbnail_buttons = TaskbarThumbnailButtons(
                        self.taskbar_progress.taskbar, hwnd, RESOURCES_DIR / "icons"
                    )
                    # Defer to ensure window is fully registered with taskbar
                    QTimer.singleShot(1000, self.thumbnail_buttons.add_buttons)
                    self.thumbnail_buttons.update_play_state(
                        not self.video_player.player.pause
                        if self.video_player.player
                        else False
                    )
            except Exception as e:
                logging.error(f"Taskbar error: {e}")

    def eventFilter(self, source, event):
        if self.is_pip_mode:
            # Handle hover visibility
            if event.type() == QEvent.Type.Enter:
                if self.pip_overlay:
                    self.pip_overlay.set_active(True)
            elif event.type() == QEvent.Type.Leave:
                # Check if mouse is actually outside the main window area
                if self.pip_overlay:
                    from PyQt6.QtGui import QCursor

                    if not self.geometry().contains(QCursor.pos()):
                        self.pip_overlay.set_active(False)
                        self.pip_overlay.set_hover_edge(None)

            # Use global position for consistent coordinate mapping across widgets
            if event.type() in [
                QEvent.Type.MouseMove,
                QEvent.Type.MouseButtonPress,
                QEvent.Type.MouseButtonRelease,
                QEvent.Type.MouseButtonDblClick,
            ]:
                if hasattr(event, "globalPosition"):
                    window_pos = self.mapFromGlobal(event.globalPosition().toPoint())
                else:
                    return super().eventFilter(source, event)

                if event.type() == QEvent.Type.MouseMove:
                    self.handle_pip_mouse_move(event, window_pos)
                    # Always swallow moves if in margin to prevent player hover effects
                    if (
                        self.resizing
                        or self.dragging
                        or self._get_resize_edge(window_pos)
                    ):
                        return True
                elif event.type() == QEvent.Type.MouseButtonPress:
                    if self.handle_pip_mouse_press(event, window_pos):
                        return True
                    # Dead zone check: block any click in the margin even if handle_pip_mouse_press didn't catch it
                    if self._get_resize_edge(window_pos):
                        return True
                elif event.type() == QEvent.Type.MouseButtonRelease:
                    if self.handle_pip_mouse_release(event, window_pos):
                        return True
                    if self._get_resize_edge(window_pos):
                        return True
                elif event.type() == QEvent.Type.MouseButtonDblClick:
                    # Block double clicks in the margin too
                    if self._get_resize_edge(window_pos):
                        return True
        return super().eventFilter(source, event)

    def handle_pip_mouse_press(self, event, window_pos=None):
        if window_pos is None:
            window_pos = self.mapFromGlobal(event.globalPosition().toPoint())

        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_resize_edge(window_pos)
            if edge:
                self.resizing = True
                self.resize_edge = edge
                self.drag_start_pos = event.globalPosition().toPoint()
                self.window_start_geo = self.geometry()
                return True
        elif event.button() == Qt.MouseButton.RightButton:
            self.dragging = True
            self.drag_start_pos = event.globalPosition().toPoint()
            self.window_start_pos = self.pos()
            return True
        return False

    def handle_pip_mouse_move(self, event, window_pos=None):
        if window_pos is None:
            try:
                gpos = event.globalPosition().toPoint()
            except AttributeError:
                gpos = event.globalPos()
            window_pos = self.mapFromGlobal(gpos)

        edge = self._get_resize_edge(window_pos)
        # if edge: logging.debug(f"PiP edge detected: {edge}")

        if self.resizing:
            self.handle_resize(event.globalPosition().toPoint())
        elif self.dragging:
            diff = event.globalPosition().toPoint() - self.drag_start_pos
            self.move(self.window_start_pos + diff)
        else:
            self.update_cursor(edge)

    def handle_pip_mouse_release(self, event, window_pos=None):
        if self.resizing or self.dragging:
            self.resizing = False
            self.dragging = False
            self.resize_edge = None
            self.unsetCursor()
            return True
        return False

    def mousePressEvent(self, event):
        if self.is_pip_mode:
            self.handle_pip_mouse_press(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_pip_mode:
            self.handle_pip_mouse_move(event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_pip_mode:
            self.handle_pip_mouse_release(event)
        else:
            super().mouseReleaseEvent(event)

    def _get_resize_edge(self, pos):
        m = self.resize_margin
        w, h = self.width(), self.height()

        # Determine vertical part
        v_edge = ""
        if pos.y() < m:
            v_edge = "top"
        elif pos.y() > h - m:
            v_edge = "bottom"

        # Determine horizontal part
        h_edge = ""
        if pos.x() < m:
            h_edge = "left"
        elif pos.x() > w - m:
            h_edge = "right"

        # Combine: vertical first (top/bottom) then horizontal (left/right)
        edge = v_edge + h_edge

        return edge if edge else None

    def update_cursor(self, edge):
        if self.is_pip_mode and self.pip_overlay:
            self.pip_overlay.set_active(True)
            self.pip_overlay.set_hover_edge(edge)
            if edge:
                self.pip_overlay.raise_()

        if edge == "left" or edge == "right":
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edge == "top" or edge == "bottom":
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif edge in ["topleft", "bottomright"]:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edge in ["topright", "bottomleft"]:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.unsetCursor()

    def handle_resize(self, global_pos):
        """Handle proportional resizing from all 8 directions in PiP mode."""
        diff = global_pos - self.drag_start_pos
        geo = self.window_start_geo
        new_geo = QRect(geo)

        # Get video aspect ratio
        ratio = self.video_player.get_video_aspect_ratio()

        # Determine master resize axes
        is_horizontal = "left" in self.resize_edge or "right" in self.resize_edge
        is_vertical = "top" in self.resize_edge or "bottom" in self.resize_edge

        # Proposed changes based on mouse movement
        if "left" in self.resize_edge:
            new_geo.setLeft(geo.left() + diff.x())
        elif "right" in self.resize_edge:
            new_geo.setRight(geo.right() + diff.x())

        if "top" in self.resize_edge:
            new_geo.setTop(geo.top() + diff.y())
        elif "bottom" in self.resize_edge:
            new_geo.setBottom(geo.bottom() + diff.y())

        # Enforce aspect ratio and min size
        min_w = 160
        min_h = int(min_w / ratio)

        if is_horizontal:
            # Width change dictates height (standard for proportional resize)
            w = max(min_w, new_geo.width())
            h = int(w / ratio)

            # Align horizontally
            if "left" in self.resize_edge:
                new_geo.setLeft(geo.right() - w + 1)
            else:
                new_geo.setWidth(w)

            # Align vertically
            if "top" in self.resize_edge:
                # If dragging top edge or top corners, top boundary moves up/down
                new_geo.setTop(geo.bottom() - h + 1)
            else:
                # If dragging bottom edge or bottom corners, bottom boundary moves
                new_geo.setHeight(h)
        elif is_vertical:
            # Pure vertical resize (top/bottom)
            h = max(min_h, new_geo.height())
            w = int(h * ratio)

            if "top" in self.resize_edge:
                new_geo.setTop(geo.bottom() - h + 1)
            else:
                new_geo.setHeight(h)

            # Keep left edge fixed for pure horizontal growth/shrink
            new_geo.setWidth(w)

        self.setGeometry(new_geo)

    def closeEvent(self, event):
        self.save_window_state()
        if hasattr(self, "hotkey_manager"):
            self.hotkey_manager.stop()

        # Cleanup player resources
        if hasattr(self, "video_player") and self.video_player:
            try:
                self.video_player.cleanup()
            except Exception as e:
                logging.error(f"Error cleaning up video player: {e}")

        self.close_db_connection()
        self.taskbar_progress.clear()
        event.accept()


from PyQt6.QtCore import QAbstractNativeEventFilter
from ctypes import wintypes as _wintypes

# Button IDs must match THUMBBUTTON_* in taskbar_progress.py
_THUMBBUTTON_PREV = 0
_THUMBBUTTON_REWIND = 1
_THUMBBUTTON_PLAYPAUSE = 2
_THUMBBUTTON_FORWARD = 3
_THUMBBUTTON_NEXT = 4

WM_COMMAND = 0x0111
THBN_CLICKED = 0x1800

import ctypes

WM_TASKBARBUTTONCREATED = 0
if sys.platform == "win32":
    try:
        WM_TASKBARBUTTONCREATED = ctypes.windll.user32.RegisterWindowMessageW(
            "TaskbarButtonCreated"
        )
    except:
        pass


class TaskbarEventFilter(QAbstractNativeEventFilter):
    """Intercepts WM_COMMAND messages from taskbar thumbnail button clicks."""

    def __init__(self, window):
        super().__init__()
        self.window = window

    def nativeEventFilter(self, event_type, message):
        if event_type == b"windows_generic_MSG" and message:
            try:
                msg_ptr = int(message)
                if msg_ptr:
                    msg = _wintypes.MSG.from_address(msg_ptr)
                    if msg.message == WM_COMMAND:
                        if (msg.wParam >> 16) & 0xFFFF == THBN_CLICKED:
                            button_id = msg.wParam & 0xFFFF
                            w = self.window
                            if button_id == _THUMBBUTTON_PREV:
                                w.play_prev_video()
                                return True, 0
                            elif button_id == _THUMBBUTTON_REWIND:
                                w.video_player.seek_relative(-10)
                                return True, 0
                            elif button_id == _THUMBBUTTON_PLAYPAUSE:
                                w.video_player.play_pause()
                                return True, 0
                            elif button_id == _THUMBBUTTON_FORWARD:
                                w.video_player.seek_relative(10)
                                return True, 0
                            elif button_id == _THUMBBUTTON_NEXT:
                                w.play_next_video()
                                return True, 0
                    elif (
                        WM_TASKBARBUTTONCREATED
                        and msg.message == WM_TASKBARBUTTONCREATED
                    ):
                        # Taskbar buttons need to be re-added when this message is received
                        QTimer.singleShot(100, self.window._refresh_taskbar_buttons)
                        return True, 0
            except Exception:
                pass
        return False, 0


def main():
    # Enable High DPI scaling
    from PyQt6.QtGui import QGuiApplication

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE)

    try:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logging.debug("Application starting...")
        window = VideoCourseBrowser()
        logging.debug("Window created")

        # Register native event filter for taskbar thumbnail button clicks
        taskbar_filter = TaskbarEventFilter(window)
        app.installNativeEventFilter(taskbar_filter)

        # Show the window in its final correct state immediately to prevent flickers
        if getattr(window, "_init_maximized", False):
            # Explicitly synchronize screen association before maximizing if needed
            window.showMaximized()
        else:
            window.show()

        logging.debug("Window shown")
        sys.exit(app.exec())
    except Exception as e:
        import traceback

        error_msg = traceback.format_exc()
        logging.critical(error_msg, exc_info=True)

        # Write to file
        try:
            with open("crash_log.txt", "w", encoding="utf-8") as f:
                f.write(error_msg)
        except:
            pass

        # Also try to show a message box if possible
        try:
            from PyQt6.QtWidgets import QMessageBox

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setText("Application Crashed")
            msg.setInformativeText(error_msg)
            msg.setDetailedText("Error saved to crash_log.txt")
            msg.setWindowTitle("Error")
            msg.exec()
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
