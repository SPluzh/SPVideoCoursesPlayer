import sys
import os
import configparser
import time
from pathlib import Path

# Fix for 'charmap' codec errors on Windows when printing Cyrillic
if sys.platform == 'win32':
    import io
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    # Try to reconfigure the underlying streams used by OutputCapture
    if hasattr(sys.__stdout__, 'reconfigure'):
        sys.__stdout__.reconfigure(encoding='utf-8')
    if hasattr(sys.__stderr__, 'reconfigure'):
        sys.__stderr__.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).parent
RESOURCES_DIR = ROOT_DIR / "resources"
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

from mpv_handler import setup_mpv_dll, resolve_binary_path

setup_mpv_dll()
import locale
locale.setlocale(locale.LC_NUMERIC, 'C')
from database import DatabaseManager
import configparser
import json
import io
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QTreeWidget, QTreeWidgetItem, QLabel, QPushButton,
    QLineEdit, QHBoxLayout, QFileDialog,
    QStyle, QMenu, QMessageBox, QCheckBox, QSplitter,
    QTreeWidgetItemIterator, QDialog, QGroupBox, QSpinBox, QSizePolicy, QFrame, QComboBox,
    QTextEdit, QProgressBar, QListWidget, QGridLayout
)
from PyQt6.QtCore import Qt, QSize, QRect, QTimer, QUrl, pyqtSignal, QByteArray, QPoint, QThread, QRectF
from PyQt6.QtGui import QIcon, QPixmap, QFont, QBrush, QColor, QPainter, QAction, QKeyEvent, QMouseEvent, QActionGroup, QPalette, QPolygon, QCursor, QPen, QTextCursor
from styles import DARK_STYLE
import styles
from taskbar_progress import TaskbarProgress
import re
from translator import tr, Translator
from about_dialog import AboutDialog
from settings_dialog import SettingsDialog, ScanProgressDialog
from subtitle_popup import SubtitlePopup, SubtitleButton
from volume_popup import VolumePopup, VolumeButton
from placeholders import draw_video_placeholder, draw_library_placeholder
from player import VideoPlayerWidget
from library import HoverTreeWidget, VideoItemDelegate
from hotkeys import HotkeyManager



class VideoCourseBrowser(QMainWindow):
    @staticmethod
    def natural_sort_key(name):
        def convert(text):
            return int(text) if text.isdigit() else text.lower()
        return [convert(c) for c in re.split(r'(\d+)', str(name))]

    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()
        self.setWindowTitle(tr('app.title'))

        self.script_dir = Path(__file__).parent
        self.config_file = RESOURCES_DIR / 'settings.ini'
        self.db_file = DATA_DIR / 'video_courses.db'
        self.db = DatabaseManager(self.db_file)

        self.hotkey_manager = HotkeyManager(self)
        self.hotkey_manager.global_action_triggered.connect(self.handle_player_action)
        self.hotkey_manager.global_action_state_changed.connect(
            lambda action, pressed: self.handle_player_action(action, pressed)
        )
        self.load_settings()

        self.load_icons()

        self.taskbar_progress = TaskbarProgress()

        self.create_menu_bar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.status = self.statusBar()
        self.status.setContentsMargins(5, 0, 5, 0)
        self.info_label = QLabel(tr('status.not_loaded'))
        self.status.addWidget(self.info_label, 1)

        self.path_edit = QLineEdit(self.library_paths)
        self.path_edit.setVisible(False)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False) # Default non-collapsible, specific overrides applied later
        main_layout.addWidget(self.splitter, 1)

        browser_widget = QWidget()
        browser_widget.setMinimumWidth(200) # Ensure library has minimum width
        browser_layout = QVBoxLayout(browser_widget)
        browser_layout.setContentsMargins(0, 0, 0, 0)
        browser_layout.setSpacing(0)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(tr('library.search_placeholder'))
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self.filter_library)
        self.search_edit.setObjectName("librarySearch")
        browser_layout.addWidget(self.search_edit)

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
            'folder_row_height': self.folder_row_height,
            'video_row_height': self.video_row_height,
            'display_width': self.display_width,
            'display_height': self.display_height,
            'format_duration': self.format_duration,
            'format_size': self.format_size
        }
        self.course_tree.setItemDelegate(
            VideoItemDelegate(delegate_config, self.course_tree)
        )

        browser_layout.addWidget(self.course_tree)
        self.splitter.addWidget(browser_widget)

        self.video_player = VideoPlayerWidget()
        self.video_player.setMinimumWidth(400) # Ensure player has minimum width
        self.video_player.db = self.db
        self.video_player.taskbar_progress = self.taskbar_progress
        self.video_player.show_preview = self.show_preview_popup
        self.video_player.set_ffmpeg_path(self.ffmpeg_path)

        self.video_player.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.video_player.video_finished.connect(self.on_video_finished)
        self.video_player.position_changed.connect(self.save_progress)
        self.video_player.pause_changed.connect(self.on_player_pause_changed)
        self.video_player.subtitle_style_changed.connect(self.save_subtitle_settings)
        self.video_player.next_video_requested.connect(self.play_next_video)
        self.video_player.prev_video_requested.connect(self.play_prev_video)
        self.video_player.toggle_fullscreen_requested.connect(self.toggle_fullscreen)

        # Apply initial subtitle settings
        self.video_player.set_subtitle_styles(self.sub_color, self.sub_border_color, self.sub_scale)

        self.splitter.addWidget(self.video_player)

        # Set default sizes before restoring state
        self.splitter.setSizes([int(self.window_width * 0.3), int(self.window_width * 0.7)])

        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 3)

        self.restore_window_state()
        
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

    def keyPressEvent(self, event: QKeyEvent):
        action = self.hotkey_manager.get_action(event)
        
        # Actions that allow auto-repeat (like seeking, volume, or speed with arrows)
        repeatable_actions = [
            "seek_forward", "seek_backward", 
            "speed_up", "speed_down", 
            "volume_up", "volume_down",
            "zoom_in", "zoom_out"
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
        if not hasattr(self, 'video_player') or not self.video_player:
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
            self.video_player.seek_relative(5)
        elif action == "seek_backward":
            self.video_player.seek_relative(-5)
        elif action == "volume_up":
            self.video_player.adjust_volume(5)
        elif action == "volume_down":
            self.video_player.adjust_volume(-5)
        elif action == "toggle_mute":
            self.video_player.toggle_mute()
        elif action == "toggle_subtitles":
            self.video_player.toggle_subtitles_hotkey()
        elif action == "take_screenshot":
            if self.video_player.screenshot_to_clipboard():
                self.info_label.setText(tr('player.tooltip_screenshot') + " ✓")
                QTimer.singleShot(2000, lambda: self.info_label.setText(tr('status.ready')))
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

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.menuBar().show()
            self.status.show()
            if hasattr(self, '_saved_splitter_state'):
                self.splitter.restoreState(self._saved_splitter_state)
        else:
            self._saved_splitter_state = self.splitter.saveState()
            self.showFullScreen()
            self.menuBar().hide()
            self.status.hide()
            # Collapse library
            self.splitter.setSizes([0, self.width()])

    def change_language(self, lang_code):
        if tr.current_lang == lang_code:
            return

        print(f"DEBUG: Changing language to {lang_code}...")
        tr.load_language(lang_code)
        self.save_language_setting(lang_code)
        # Defer UI update to avoid crashing while inside a menu action
        # Increased delay to 100ms to ensure menu animations finish
        QTimer.singleShot(100, self.update_all_texts)

    def save_language_setting(self, lang_code):
        config = configparser.ConfigParser()
        if self.config_file.exists():
            config.read(self.config_file, encoding='utf-8')

        if 'General' not in config:
            config['General'] = {}

        config['General']['language'] = lang_code

        with open(self.config_file, 'w', encoding='utf-8') as f:
            config.write(f)

    def load_language_setting(self):
        if not self.config_file.exists():
            return 'ru'

        config = configparser.ConfigParser()
        config.read(self.config_file, encoding='utf-8')

        return config.get('General', 'language', fallback='ru')

    def update_all_texts(self):
        try:
            print("DEBUG: update_all_texts started")
            self.setWindowTitle(tr('app.title'))
            print("DEBUG: Clearing menu bar")
            self.menuBar().clear()
            print("DEBUG: Recreating menu bar")
            self.create_menu_bar()
            if hasattr(self, 'search_edit'):
                self.search_edit.setPlaceholderText(tr('library.search_placeholder'))
            if hasattr(self, 'video_player') and self.video_player:
                print("DEBUG: Updating player texts")
                self.video_player.update_texts()
            print("DEBUG: Loading courses")
            self.load_courses()
            print("DEBUG: update_all_texts finished")
        except Exception as e:
            print(f"CRITICAL ERROR in update_all_texts: {e}")
            import traceback
            traceback.print_exc()

    def on_item_expanded(self, item):
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if item_type != 'folder':
            return

        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path:
            return

        self.db.update_folder_expanded_state(path, True)

    def on_item_collapsed(self, item):
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if item_type != 'folder':
            return

        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path:
            return

        self.db.update_folder_expanded_state(path, False)

    def update_window_title_for_item(self, item):
        course_item = item.parent()
        course_name = ''

        if course_item is not None:
            full_text = course_item.text(0)
            idx = full_text.find('(')
            course_name = full_text[:idx].strip() if idx > 0 else full_text.strip()

        video_name = item.text(0).strip()

        if course_name:
            title = f"{tr('app.title')} - {course_name} - {video_name}"
        else:
            title = video_name

        self.setWindowTitle(title)

    def restore_window_state(self):
        is_maximized = False
        config = configparser.ConfigParser()
        if self.config_file.exists():
            config.read(self.config_file, encoding='utf-8')

            if config.has_option('Window', 'geometry'):
                try:
                    geometry_hex = config.get('Window', 'geometry')
                    geometry = QByteArray.fromHex(bytes(geometry_hex, 'utf-8'))
                    self.restoreGeometry(geometry)
                except Exception as e:
                    print(f"Error restoring geometry: {e}")
                    self.resize(self.window_width, self.window_height)
            else:
                self.resize(self.window_width, self.window_height)

            if config.has_option('Window', 'is_maximized'):
                try:
                    is_maximized = config.getboolean('Window', 'is_maximized')
                except Exception as e:
                    print(f"Error reading maximized state: {e}")

            if config.has_option('Window', 'splitter_state'):
                try:
                    splitter_hex = config.get('Window', 'splitter_state')
                    splitter_state = QByteArray.fromHex(bytes(splitter_hex, 'utf-8'))
                    self.splitter.restoreState(splitter_state)
                    
                    # Ensure player pane (index 1) is not collapsed
                    sizes = self.splitter.sizes()
                    if len(sizes) >= 2 and sizes[1] < 50:
                        total_width = sum(sizes)
                        if total_width > 0:
                            self.splitter.setSizes([int(total_width * 0.3), int(total_width * 0.7)])
                        else:
                            self.splitter.setSizes([400, 1000])
                except Exception as e:
                    print(f"Error restoring splitter: {e}")

            if config.has_option('Window', 'playback_speed'):
                try:
                    speed_value = int(config.get('Window', 'playback_speed'))
                    self.video_player.speed_slider.setValue(speed_value)
                except Exception as e:
                    print(f"Error restoring playback speed: {e}")
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
                    self.splitter.setSizes([int(total_width * 0.3), int(total_width * 0.7)])
                else:
                    self.splitter.setSizes([400, 1000])

    def save_window_state(self):
        config = configparser.ConfigParser()
        if self.config_file.exists():
            config.read(self.config_file, encoding='utf-8')

        if 'Window' not in config:
            config['Window'] = {}

        geometry = self.saveGeometry().toHex().data().decode('utf-8')
        config['Window']['geometry'] = geometry

        splitter_state = self.splitter.saveState().toHex().data().decode('utf-8')
        config['Window']['splitter_state'] = splitter_state

        config['Window']['is_maximized'] = str(self.isMaximized())

        if self.video_player.current_file:
            config['Window']['last_video'] = self.video_player.current_file

        config['Window']['playback_speed'] = str(self.video_player.speed_slider.value())

        with open(self.config_file, 'w', encoding='utf-8') as f:
            config.write(f)

    def restore_last_video(self):
        config = configparser.ConfigParser()
        if not self.config_file.exists():
            return

        config.read(self.config_file, encoding='utf-8')

        if not config.has_option('Window', 'last_video'):
            return

        last_video_path = config.get('Window', 'last_video')

        if not last_video_path or not Path(last_video_path).exists():
            return

        item = self.find_video_item(last_video_path)

        if item:
            saved_position, saved_volume = self.get_saved_position(last_video_path)
            self.video_player.load_video(last_video_path, saved_position, volume=saved_volume, auto_play=False)
            # Update delegate
            delegate = self.course_tree.itemDelegate()
            if isinstance(delegate, VideoItemDelegate):
                delegate.playing_path = last_video_path
                delegate.is_paused = True # Load paused
                self.course_tree.viewport().update()
                
            self.course_tree.setCurrentItem(item)
            self.course_tree.scrollToItem(item)
            self.setFocus()
            self.update_window_title_for_item(item)

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
        lib_menu = menubar.addMenu(tr('menu.library'))

        scan_action = QAction(self.icons.get('menu_scan', QIcon()), tr('menu.scan'), self)
        scan_action.setShortcut('Ctrl+R')
        scan_action.triggered.connect(self.rescan_directories)
        lib_menu.addAction(scan_action)

        settings_action = QAction(self.icons.get('menu_settings', QIcon()), tr('menu.settings'), self)
        settings_action.setShortcut('Ctrl+,')
        settings_action.triggered.connect(self.open_settings)
        lib_menu.addAction(settings_action)
        
        # [Tools] Menu
        tools_menu = menubar.addMenu(tr('menu.tools'))
        
        screenshot_action = QAction(self.icons.get('screenshot', QIcon()), tr('menu.screenshot'), self)
        screenshot_action.setShortcut('S')
        screenshot_action.triggered.connect(lambda: self.handle_player_action("take_screenshot"))
        tools_menu.addAction(screenshot_action)
        
        tools_menu.addSeparator()
        
        frame_step_action = QAction(self.icons.get('next_frame', QIcon()), tr('menu.frame_step'), self)
        frame_step_action.setShortcut('.')
        frame_step_action.triggered.connect(lambda: self.handle_player_action("frame_step"))
        tools_menu.addAction(frame_step_action)
        
        frame_back_action = QAction(self.icons.get('prev_frame', QIcon()), tr('menu.frame_back'), self)
        frame_back_action.setShortcut(',')
        frame_back_action.triggered.connect(lambda: self.handle_player_action("frame_back"))
        tools_menu.addAction(frame_back_action)

        # [View] Menu
        view_menu = menubar.addMenu(tr('menu.view'))

        # Language selection
        lang_menu = view_menu.addMenu(tr('menu.language'))
        lang_group = QActionGroup(self)
        lang_group.setExclusive(True)

        ru_action = QAction(tr('menu.language_ru'), self)
        ru_action.setCheckable(True)
        ru_action.setChecked(tr.current_lang == 'ru')
        ru_action.triggered.connect(lambda: self.change_language('ru'))
        lang_group.addAction(ru_action)
        lang_menu.addAction(ru_action)

        en_action = QAction(tr('menu.language_en'), self)
        en_action.setCheckable(True)
        en_action.setChecked(tr.current_lang == 'en')
        en_action.triggered.connect(lambda: self.change_language('en'))
        lang_group.addAction(en_action)
        lang_menu.addAction(en_action)

        view_menu.addSeparator()

        # Reload Styles
        reload_styles_action = QAction(self.icons.get('menu_reload', QIcon()), tr('menu.reload_styles'), self)
        reload_styles_action.setShortcut('F5')
        reload_styles_action.triggered.connect(self.reload_styles)
        view_menu.addAction(reload_styles_action)

        # [Help] Menu
        help_menu = menubar.addMenu(tr('menu.help'))

        about_action = QAction(self.icons.get('menu_about', QIcon()), tr('menu.about'), self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def reload_styles(self):
        """Reload application styles."""
        qss = styles.StyleManager.get_style()
        self.setStyleSheet(qss)
        # If style update needs to be forced
        self.style().unpolish(self)
        self.style().polish(self)
        self.info_label.setText(tr('status.styles_reloaded'))

    def close_db_connection(self):
        """Prepare for DB deletion: stop timers and release resources"""
        # Stop auto-save timer
        if hasattr(self, 'progress_save_timer') and self.progress_save_timer.isActive():
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
            self.path_edit.setText(self.library_paths)
            QMessageBox.information(self, tr('settings.done'), tr('settings.saved'))

    def show_about(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def save_progress(self, position_sec, file_path):
        """Save playback progress."""
        try:
            # Calculate percent here or let database.py handle it. 
            # Current database.py save_progress expects (file_path, position_sec, duration_sec)
            # but I added another one later. Let me check my own code.
            # I added: save_progress(self, file_path, position, duration, percent, current_volume)
            
            position = int(self.video_player.player.time_pos or 0)
            duration = int(self.video_player.player.duration or 0)
            current_volume = int(self.video_player.player.volume or 100)
            percent = min(100, int((position / duration) * 100)) if duration > 0 else 0
            
            self.db.save_progress(file_path, position, duration, percent, current_volume)
        except Exception as e:
            print(f"Error saving progress: {e}")

    def periodic_progress_save(self):
        if not self.video_player.current_file:
            return

        file_path = self.video_player.current_file

        try:
            position = int(self.video_player.player.time_pos or 0)
            duration = int(self.video_player.player.duration or 0)
            current_volume = int(self.video_player.player.volume or 100)
        except Exception as e:
            print(f"Error getting player state for save: {e}")
            return

        if duration > 0:
            percent = int((position / duration) * 100)
            
            try:
                self.db.save_progress(file_path, position, duration, percent, current_volume)
            except Exception as e:
                print(f"Error saving progress to DB: {e}")
                return

            self.update_video_item_display(file_path, percent, position)

    def update_video_item_display(self, file_path, percent, position):
        iterator = QTreeWidgetItemIterator(self.course_tree)
        while iterator.value():
            item = iterator.value()
            if item.data(0, Qt.ItemDataRole.UserRole) == file_path:
                data = item.data(0, Qt.ItemDataRole.UserRole + 2)
                if data:
                    filename, duration, resolution, file_size, _, thumbnail_path, thumbnails_list, _ = data
                    item.setData(0, Qt.ItemDataRole.UserRole + 2,
                               (filename, duration, resolution, file_size,
                                percent, thumbnail_path, thumbnails_list, position))
                break
            iterator += 1

        self.course_tree.viewport().update()

    def on_video_finished(self):
        if self.video_player.current_file:
            self.db.mark_video_as_watched(self.video_player.current_file)
            self.load_courses()

    def clear_metadata(self):
        """Clear all metadata via main window button."""
        self.clear_metadata_force()

    def clear_metadata_force(self):
        """Clear all metadata from DB and remove thumbnail cache."""
        if not self.db:
            print("❌ Database manager not initialized")
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
                            pass # Skip if file is busy
                except Exception as e:
                    print(f"Warning clearing thumbnails: {e}")
                
            # 4. Unload current video from player
            if hasattr(self, 'video_player'):
                self.video_player.unload_video()
                
            # 5. Reload interface (will be empty)
            self.load_courses()
            return True
            
        except Exception as e:
            print(f"Error clearing metadata: {e}")
            return False

    def get_saved_position(self, file_path):
        """Return (last_position, volume) for file."""
        progress = self.db.get_video_progress(file_path)
        if progress:
            return progress['last_position'], progress['volume']
        return 0, 100

    def on_player_pause_changed(self, is_paused):
        delegate = self.course_tree.itemDelegate()
        if isinstance(delegate, VideoItemDelegate):
            delegate.is_paused = is_paused
            self.course_tree.viewport().update()

    def load_icons(self):
        self.icons = {}
        # List of icons to load for the browser
        icon_names = [
            "menu_scan", "menu_settings", "menu_reload", "menu_about",
            "context_open_folder", "context_mark_read", "context_mark_unread",
            "context_play", "app_icon", "screenshot", "next_frame", "prev_frame",
            "volume_hight"
        ]
        for name in icon_names:
            icon_path = RESOURCES_DIR / "icons" / f"{name}.png"
            if icon_path.exists():
                self.icons[name] = QIcon(str(icon_path))
            else:
                self.icons[name] = QIcon()

        # Set window icon
        if 'app_icon' in self.icons:
            self.setWindowIcon(self.icons['app_icon'])

        self.folder_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        self.video_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)

        if self.video_icon.isNull():
            self.video_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)

    def show_context_menu(self, pos):
        item = self.course_tree.itemAt(pos)
        if not item:
            return

        menu = QMenu()
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)

        if item_type == 'video':
            file_path = item.data(0, Qt.ItemDataRole.UserRole)
            saved_pos, _ = self.get_saved_position(file_path)

            if saved_pos > 0:
                resume_action = menu.addAction(self.icons.get('context_play', QIcon()), tr('context_menu.resume', time=self.format_time(saved_pos)))
                resume_action.triggered.connect(lambda: self.play_video_in_player(item, resume=True))

                restart_action = menu.addAction(self.icons.get('context_play', QIcon()), tr('context_menu.restart'))
                restart_action.triggered.connect(lambda: self.play_video_in_player(item, resume=False))
            else:
                play_action = menu.addAction(self.icons.get('context_play', QIcon()), tr('context_menu.play'))
                play_action.triggered.connect(lambda: self.play_video_in_player(item))

            play_external_action = menu.addAction(self.icons.get('context_play', QIcon()), tr('context_menu.play_external'))
            play_external_action.triggered.connect(lambda: self.play_video(item))

            menu.addSeparator()

            # ADDED: Audio track selection submenu
            audio_menu = menu.addMenu(self.icons.get('volume_hight', QIcon()), tr('player.audio_tracks'))
            self.populate_audio_submenu(audio_menu, file_path, item)

            menu.addSeparator()

            mark_watched_action = menu.addAction(self.icons.get('context_mark_read', QIcon()), tr('context_menu.mark_watched'))
            mark_watched_action.triggered.connect(lambda: self.mark_as_watched(item))

            reset_action = menu.addAction(self.icons.get('context_mark_unread', QIcon()), tr('context_menu.reset_progress'))
            reset_action.triggered.connect(lambda: self.reset_video_progress(item))

            menu.addSeparator()
            open_dir_action = menu.addAction(self.icons.get('context_open_folder', QIcon()), tr('context_menu.open_directory'))
            open_dir_action.triggered.connect(lambda: self.open_video_directory(item))

        elif item_type == 'folder':
            open_action = menu.addAction(self.icons.get('context_open_folder', QIcon()), tr('context_menu.open_folder'))
            open_action.triggered.connect(lambda: self.open_folder(item))

            menu.addSeparator()

            play_all_action = menu.addAction(self.icons.get('context_play', QIcon()), tr('context_menu.play_all'))
            play_all_action.triggered.connect(lambda: self.play_folder(item))

            mark_all_action = menu.addAction(self.icons.get('context_mark_read', QIcon()), tr('context_menu.mark_all_watched'))
            mark_all_action.triggered.connect(lambda: self.mark_folder_as_watched(item))

            reset_all_action = menu.addAction(self.icons.get('context_mark_unread', QIcon()), tr('context_menu.reset_all_progress'))
            reset_all_action.triggered.connect(lambda: self.reset_folder_progress(item))

        menu.exec(self.course_tree.viewport().mapToGlobal(pos))

    # ADDED: Context menu audio track methods
    def populate_audio_submenu(self, menu, filepath, item):
        """Populate audio submenu."""
        try:
            video_info = self.db.get_video_info(filepath)
            if not video_info:
                return

            video_id = video_info['id']
            tracks, selected_audio_id = self.db.load_audio_tracks(filepath)

            if not tracks:
                menu.addAction(tr('player.no_tracks')).setEnabled(False)
                return

            action_group = QActionGroup(self)
            action_group.setExclusive(True)

            for track in tracks:
                track_id = track['id']
                track_type = track['track_type']
                stream_index = track['stream_index']
                audio_file_name = track['audio_file_name']
                language = track['language']
                title = track['title']
                codec = track['codec']
                channels = track['channels']
                is_default = track['is_default']

                if track_type == 'embedded':
                    label = f"#{stream_index}"
                    if language:
                        label += f" [{language}]"
                    if title:
                        label += f" - {title}"
                else:
                    label = f"{audio_file_name or tr('player.external_audio')}"

                if is_default:
                    label += f" [{tr('player.default')}]"

                action = menu.addAction(self.icons.get('volume_hight', QIcon()), label)
                action.setCheckable(True)
                action.setChecked(track_id == selected_audio_id)
                action.setActionGroup(action_group)
                action.triggered.connect(
                    lambda checked, tid=track_id, fp=filepath:
                    self.set_audio_track_for_file(tid, fp, item)
                )

        except Exception as e:
            print(f"Error populating audio submenu: {e}")

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
            print(f"Error setting audio track: {e}")

    def item_double_clicked(self, item):
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)

        if item_type == 'video':
            self.play_video_in_player(item, resume=True)
        elif item_type == 'folder':
            item.setExpanded(not item.isExpanded())

    def play_next_video(self):
        if not self.video_player.current_file:
            return

        current_item = self.find_video_item(self.video_player.current_file)
        if not current_item:
            return

        # Determine if we should auto-play the next video
        # If player is currently playing (not paused), then auto-play next
        should_play = True
        if self.video_player.player:
            should_play = not self.video_player.player.pause

        iterator = QTreeWidgetItemIterator(self.course_tree, QTreeWidgetItemIterator.IteratorFlag.All)
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
            if item_type == 'video':
                self.play_video_in_player(item, resume=True, auto_play=should_play)
                self.course_tree.scrollToItem(item)
                self.course_tree.setCurrentItem(item)
                return
            iterator += 1

    def play_prev_video(self):
        if not self.video_player.current_file:
            return

        current_item = self.find_video_item(self.video_player.current_file)
        if not current_item:
            return

        # Determine if we should auto-play the prev video
        should_play = True
        if self.video_player.player:
            should_play = not self.video_player.player.pause

        iterator = QTreeWidgetItemIterator(self.course_tree, QTreeWidgetItemIterator.IteratorFlag.All)
        last_video_item = None

        while iterator.value():
            item = iterator.value()
            if item == current_item:
                if last_video_item:
                    self.play_video_in_player(last_video_item, resume=True, auto_play=should_play)
                    self.course_tree.scrollToItem(last_video_item)
                    self.course_tree.setCurrentItem(last_video_item)
                return
            
            item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if item_type == 'video':
                last_video_item = item
            
            iterator += 1

    def play_video_in_player(self, item, resume=True, auto_play=True):
        file_path = item.data(0, Qt.ItemDataRole.UserRole)

        if file_path and Path(file_path).exists():
            saved_position = 0
            saved_volume = 100
            if resume:
                saved_position, saved_volume = self.get_saved_position(file_path)

            self.video_player.load_video(file_path, saved_position, volume=saved_volume, auto_play=auto_play)
            # Update delegate
            delegate = self.course_tree.itemDelegate()
            if isinstance(delegate, VideoItemDelegate):
                delegate.playing_path = file_path
                delegate.is_paused = not auto_play
                self.course_tree.viewport().update()
                
            #self.video_player.restore_audio_track(file_path)
            self.update_window_title_for_item(item)

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
            if first_child.data(0, Qt.ItemDataRole.UserRole + 1) == 'video':
                self.play_video_in_player(first_child, resume=True)

    def open_folder(self, item):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        root_path = item.data(0, Qt.ItemDataRole.UserRole + 3)

        if path and root_path:
            import os
            folder = Path(root_path) / path

            if folder.exists():
                print(folder)
                os.startfile(folder)
            else:
                QMessageBox.warning(self, tr('error.title'), tr('error.folder_not_found', folder=folder))
        else:
            QMessageBox.warning(self, tr('error.title'), tr('error.folder_path_unknown'))

    def open_video_directory(self, item):
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if file_path and Path(file_path).exists():
            import os
            folder = Path(file_path).parent
            if folder.exists():
                os.startfile(folder)
            else:
                QMessageBox.warning(self, tr('error.title'), tr('error.folder_not_found', folder=folder))
        else:
            QMessageBox.warning(self, tr('error.title'), tr('error.folder_path_unknown'))

    def reset_video_progress(self, item):
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        self.db.reset_video_progress(file_path)
        self.load_courses()

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, tr('dialog.select_directory'), self.path_edit.text())

        if directory:
            self.path_edit.setText(directory)

    def scan_single_directory(self, path):
        try:
            from scanner import VideoScanner
        except ImportError:
            self.info_label.setText(tr('status.scanner_not_found'))
            return 0, 0

        scanner = VideoScanner(str(self.config_file.name))
        return scanner.scan_directory(path)

    def rescan_directories(self, paths=None):
        config = configparser.ConfigParser()
        config.read(self.config_file, encoding='utf-8')

        # If no paths provided, load from config
        if paths is None or isinstance(paths, bool):
            paths_str = config.get('Paths', 'paths', fallback='')
            paths = [p.strip() for p in paths_str.split(';') if p.strip()]
            if not paths:
                QMessageBox.warning(
                    self,
                    tr('settings.warning'),
                    tr('settings.specify_path')
                )
                return

        if 'Thumbnails' not in config:
            config['Thumbnails'] = {}

        with open(self.config_file, 'w', encoding='utf-8') as f:
            config.write(f)

        # Show progress dialog with console output
        dialog = ScanProgressDialog(self)
        dialog.start_scan(self.config_file, paths, self.ffmpeg_path, self.ffprobe_path)
        dialog.scanner_thread.finished_scan.connect(
            lambda v, f: self._on_scan_complete(v, f)
        )
        dialog.exec()

    def _on_scan_complete(self, total_videos, total_folders):
        self.info_label.setText(tr('status.found', folders=total_folders, videos=total_videos))
        # Refresh courses immediately while dialog might still be open
        self.load_courses()

    def create_default_settings(self):
        config = configparser.ConfigParser()

        config['General'] = {
        'language': 'ru',
        'show_preview_popup': 'True'
    }
        config['Paths'] = {
            'paths': '',
            'thumbnails_dir': 'data/video_thumbnails',
            'ffmpeg_path': 'resources/bin/ffmpeg.exe',
            'ffprobe_path': 'resources/bin/ffprobe.exe',
            'libmpv_path': 'resources/bin/libmpv-2.dll'
        }
        config['Display'] = {
            'window_width': '1400',
            'window_height': '800',
            'video_row_height': '110',
            'folder_row_height': '35'
        }
        config['Thumbnails'] = {
            'render_width': '320',
            'render_height': '180',
            'display_width': '160',
            'display_height': '90',
            'count': '12',
            'quality': '2',
            'regenerate': 'False',
            'max_workers': '8',
            'animation_interval': '400'
        }
        config['Video'] = {
            'extensions': '.mp4,.mkv,.avi,.mov,.wmv,.flv,.webm,.m4v,.mpg,.mpeg,.3gp,.ts'
        }
        config['Subtitles'] = {
            'text_color': '#FFFFFF',
            'outline_color': '#000000',
            'font_scale': '1.0'
        }

        with open(self.config_file, 'w', encoding='utf-8') as f:
            config.write(f)

    def load_settings(self):
        if not self.config_file.exists():
            self.create_default_settings()

        config = configparser.ConfigParser()
        config.read(self.config_file, encoding='utf-8')

        lang = config.get('General', 'language', fallback='ru')
        tr.load_language(lang)
        self.show_preview_popup = config.getboolean('General', 'show_preview_popup', fallback=True)

        self.library_paths = config.get('Paths', 'paths', fallback='')
        self.thumbnails_dir = DATA_DIR / 'video_thumbnails'
        if config.has_section('Paths'):
            self.thumbnails_dir = Path(config.get('Paths', 'thumbnails_dir', fallback=str(DATA_DIR / 'video_thumbnails')))
            # If path is relative, make it absolute relative to ROOT_DIR
            if not self.thumbnails_dir.is_absolute():
                self.thumbnails_dir = ROOT_DIR / self.thumbnails_dir

            if not self.thumbnails_dir.is_absolute():
                self.thumbnails_dir = ROOT_DIR / self.thumbnails_dir

        # Binary files - get from already loaded config
        self.ffmpeg_path = resolve_binary_path(config, 'ffmpeg_path', 'bin/ffmpeg.exe')
        self.ffprobe_path = resolve_binary_path(config, 'ffprobe_path', 'bin/ffprobe.exe')
        self.libmpv_path = resolve_binary_path(config, 'libmpv_path', 'bin/libmpv-2.dll')

        self.window_width = config.getint('Display', 'window_width', fallback=1400)
        self.window_height = config.getint('Display', 'window_height', fallback=800)
        self.video_row_height = config.getint('Display', 'video_row_height', fallback=110)
        self.folder_row_height = config.getint('Display', 'folder_row_height', fallback=35)

        self.display_width = config.getint('Thumbnails', 'display_width', fallback=160)
        self.display_height = config.getint('Thumbnails', 'display_height', fallback=90)
        self.animation_interval = config.getint('Thumbnails', 'animation_interval', fallback=400)

        # Subtitle settings
        self.sub_color = config.get('Subtitles', 'text_color', fallback='#FFFFFF')
        self.sub_border_color = config.get('Subtitles', 'outline_color', fallback='#000000')
        self.sub_scale = config.getfloat('Subtitles', 'font_scale', fallback=1.0)

    def save_subtitle_settings(self, property_name, value):
        """Save subtitle style settings to ini file."""
        config = configparser.ConfigParser()
        if self.config_file.exists():
            config.read(self.config_file, encoding='utf-8')

        if 'Subtitles' not in config:
            config['Subtitles'] = {}

        if property_name == "sub-color":
            config['Subtitles']['text_color'] = value
        elif property_name == "sub-border-color":
            config['Subtitles']['outline_color'] = value
        elif property_name == "sub-scale":
            config['Subtitles']['font_scale'] = f"{value:.2f}"

        with open(self.config_file, 'w', encoding='utf-8') as f:
            config.write(f)

    def format_time(self, seconds):
        if not seconds:
            return "00:00"

        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)

        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def format_duration(self, seconds):
        return self.format_time(seconds)

    def format_size(self, bytes_size):
        if bytes_size < 1024 * 1024:
            return tr('video_info.size_kb', size=f'{bytes_size/1024:.1f}')
        elif bytes_size < 1024 * 1024 * 1024:
            return tr('video_info.size_mb', size=f'{bytes_size/(1024*1024):.1f}')
        else:
            return tr('video_info.size_gb', size=f'{bytes_size/(1024*1024*1024):.2f}')

    def load_courses(self):
        """Load courses from DB and build tree."""
        folder_font = QFont()
        folder_font.setBold(True)

        # Safety: Disable progress timer and hover during reload
        if hasattr(self, 'progress_save_timer'):
            self.progress_save_timer.stop()
            
        self.course_tree.stop_hover()
        self.course_tree.blockSignals(True)
        self.course_tree.clear()
        
        delegate = self.course_tree.itemDelegate()
        if isinstance(delegate, VideoItemDelegate):
            delegate.thumbnail_cache.clear()

        if not self.db_file.exists():
            self.info_label.setText(tr('status.db_not_found'))
            return
        
        folders, videos = self.db.get_courses()
        
        # Index folders
        folder_items = {}
        folders_data = {}
        for f in folders:
            folders_data[f['path']] = f

        # Create root folders first (no parent in DB or parent not in list)
        for f in folders:
            if not f['parent_path'] or f['parent_path'] not in folders_data:
                item = QTreeWidgetItem(self.course_tree)
                name_with_info = f"{f['name']}"
                if f['video_count'] > 0:
                    name_with_info += f" ({f['video_count']}) - {self.format_duration(f['total_duration'])}"
                
                item.setText(0, name_with_info)
                item.setFont(0, folder_font)
                item.setData(0, Qt.ItemDataRole.UserRole, f['path'])
                item.setData(0, Qt.ItemDataRole.UserRole + 1, 'folder')
                item.setData(0, Qt.ItemDataRole.UserRole + 3, f['root_path']) # Store root_path for opening folder
                
                # Icon
                item.setIcon(0, self.folder_icon)
                
                folder_items[f['path']] = item
                if f.get('is_expanded'):
                    item.setExpanded(True)

        # Now insert remaining folders (multiple passes if needed)
        max_iterations = 10
        for _ in range(max_iterations):
            added_any = False
            for f in folders:
                if f['path'] in folder_items:
                    continue
                
                if f['parent_path'] in folder_items:
                    parent_item = folder_items[f['parent_path']]
                    item = QTreeWidgetItem(parent_item)
                    
                    name_with_info = f"{f['name']}"
                    if f['video_count'] > 0:
                        name_with_info += f" ({f['video_count']}) - {self.format_duration(f['total_duration'])}"
                    
                    item.setText(0, name_with_info)
                    item.setFont(0, folder_font)
                    item.setData(0, Qt.ItemDataRole.UserRole, f['path'])
                    item.setData(0, Qt.ItemDataRole.UserRole + 1, 'folder')
                    item.setData(0, Qt.ItemDataRole.UserRole + 3, f['root_path']) # Store root_path
                    item.setIcon(0, self.folder_icon)
                    
                    folder_items[f['path']] = item
                    if f.get('is_expanded'):
                        item.setExpanded(True)
                    added_any = True
            
            if not added_any:
                break

        # Add videos
        for v in videos:
            if v['folder_path'] in folder_items:
                parent_item = folder_items[v['folder_path']]
                video_item = QTreeWidgetItem(parent_item)
                
                display_name = v['file_name']
                if v['track_number']:
                    display_name = f"{v['track_number']}. {display_name}"
                
                video_item.setText(0, display_name)
                video_item.setData(0, Qt.ItemDataRole.UserRole, v['file_path'])
                video_item.setData(0, Qt.ItemDataRole.UserRole + 1, 'video')
                
                thumbnails_list = []
                if v['thumbnails_json']:
                    try:
                        thumbnails_list = json.loads(v['thumbnails_json'])
                    except:
                        pass

                # Data for delegate
                video_item.setData(0, Qt.ItemDataRole.UserRole + 2,
                                  (v['file_name'], v['duration'], v['resolution'], v['file_size'],
                                   v['watched_percent'] or 0, v['thumbnail_path'], thumbnails_list, v['last_position'] or 0))
                
                video_item.setIcon(0, self.video_icon)
                # Disable selection for video rows
                video_item.setFlags(video_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        self.course_tree.blockSignals(False)
        
        # Re-enable progress timer
        if hasattr(self, 'progress_save_timer'):
            self.progress_save_timer.start(1000)

        # Info panel statistics
        folder_count = len(folders)
        video_count = len(videos)
        thumb_count = sum(1 for v in videos if v.get('thumbnails_json'))
        resumed_count = sum(1 for v in videos if v.get('last_position', 0) > 0)

        self.info_label.setText(tr('status.loaded',
                                   folders=folder_count,
                                   videos=video_count,
                                   thumbs=thumb_count,
                                   resumed=resumed_count))
        
        # Apply current filter if any
        if hasattr(self, 'search_edit') and self.search_edit.text():
            self.filter_library(self.search_edit.text())

    def filter_library(self, text):
        """Filter library items by text."""
        query = text.lower()
        self.course_tree.blockSignals(True)
        self.course_tree.setUpdatesEnabled(False)
        try:
            for i in range(self.course_tree.topLevelItemCount()):
                item = self.course_tree.topLevelItem(i)
                self._apply_filter(item, query)
        finally:
            self.course_tree.setUpdatesEnabled(True)
            self.course_tree.blockSignals(False)

    def _apply_filter(self, item, query, parent_matches=False):
        """Recursively apply filter to item and children."""
        item_text = item.text(0).lower()
        item_matches = query in item_text
        
        # If parent matches, all children are shown
        actual_matches = item_matches or parent_matches
        
        child_visible = False
        for i in range(item.childCount()):
            if self._apply_filter(item.child(i), query, actual_matches):
                child_visible = True
        
        is_visible = actual_matches or child_visible
        item.setHidden(not is_visible)
        
        if query and child_visible:
            item.setExpanded(True)
            
        return is_visible

    def showEvent(self, event):
        super().showEvent(event)
        self.setFocus()
        if self.taskbar_progress:
            try:
                hwnd = int(self.winId())
                self.taskbar_progress.set_hwnd(hwnd)
                self.taskbar_progress.set_normal()
            except Exception as e:
                print(f"Taskbar error: {e}")

    def closeEvent(self, event):
        self.save_window_state()
        if hasattr(self, 'hotkey_manager'):
            self.hotkey_manager.stop()
        self.taskbar_progress.clear()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(DARK_STYLE)

    try:
        window = VideoCourseBrowser()
        is_maximized = window.restore_window_state()
        window.show()
        if is_maximized:
            # Explicitly synchronize screen association before maximizing
            center = window.geometry().center()
            screen = QApplication.screenAt(center)
            if screen and window.windowHandle():
                window.windowHandle().setScreen(screen)
                
            # Still using a small delay to ensure OS window manager is ready
            QTimer.singleShot(100, window.showMaximized)
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(error_msg)
        
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


if __name__ == '__main__':
    main()
