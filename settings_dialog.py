import sys
import os
import configparser
import time
import io
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QTreeWidget, QTreeWidgetItem, QPushButton,
    QHBoxLayout, QFileDialog, QStyle, QMessageBox, QLabel, QProgressBar, QTextEdit,
    QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QTextCursor

from translator import tr
from styles import DARK_STYLE

ROOT_DIR = Path(__file__).parent
RESOURCES_DIR = ROOT_DIR / "resources"

def resolve_binary_path(config, key, default_relative):
    default_path = RESOURCES_DIR / default_relative
    try:
        custom_path = config.get('Paths', key, fallback=None)
        if custom_path:
            res_path = Path(custom_path)
            if not res_path.is_absolute():
                res_path = ROOT_DIR / res_path
            return res_path
    except Exception:
        pass
    return default_path

class OutputCapture(io.StringIO):
    """Captures print output and emits signals"""
    def __init__(self, signal):
        super().__init__()
        self.signal = signal
        self._real_stdout = sys.__stdout__
    
    def write(self, text):
        if text:
            # Check if this is a progress line (contains \r)
            if '\r' in text:
                self.signal.emit(text)
            elif text.strip():
                self.signal.emit(text.rstrip())
        
        # Also write to real stdout for debugging
        if self._real_stdout:
            self._real_stdout.write(text)
    
    def flush(self):
        if self._real_stdout:
            self._real_stdout.flush()

class ScannerThread(QThread):
    """Background thread for scanning directories"""
    progress = pyqtSignal(str)  # Log message
    finished_scan = pyqtSignal(int, int)  # total_videos, total_folders
    
    def __init__(self, config_file, paths, ffmpeg_path=None, ffprobe_path=None):
        super().__init__()
        self.config_file = config_file
        self.paths = paths
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.total_videos = 0
        self.total_folders = 0
    
    def run(self):
        try:
            # Redirect stdout to capture print statements
            old_stdout = sys.stdout
            sys.stdout = OutputCapture(self.progress)
            
            # Check for ffmpeg/ffprobe before starting
            ffmpeg_path = self.ffmpeg_path or (RESOURCES_DIR / 'bin/ffmpeg.exe')
            ffprobe_path = self.ffprobe_path or (RESOURCES_DIR / 'bin/ffprobe.exe')
            bin_dir = ffmpeg_path.parent
            
            if not ffmpeg_path.exists() or not ffprobe_path.exists():
                self.progress.emit(tr('ffmpeg_updater.missing_auto_download', path=bin_dir))
                try:
                    from update_ffmpeg import download_ffmpeg
                    download_ffmpeg() # It prints to stdout, which we captured
                except Exception as e:
                    self.progress.emit(tr('ffmpeg_updater.auto_download_failed', error=e))

            # Check for libmpv-2.dll before starting
            if not (bin_dir / "libmpv-2.dll").exists() and not (ROOT_DIR / "libmpv-2.dll").exists():
                self.progress.emit(tr('ffmpeg_updater.missing_libmpv_auto_download', path=bin_dir))
                try:
                    from update_libmpv import update_libmpv
                    update_libmpv()
                except Exception as e:
                    self.progress.emit(tr('ffmpeg_updater.libmpv_auto_download_failed', error=e))
            
            from scanner import VideoScanner
            scanner = VideoScanner(str(self.config_file))
            
            for path in self.paths:
                videos, folders = scanner.scan_directory(path)
                self.total_videos += videos
                self.total_folders += folders
            
            sys.stdout = old_stdout
            self.finished_scan.emit(self.total_videos, self.total_folders)
            
        except Exception as e:
            sys.stdout = old_stdout
            self.progress.emit(f"Error: {e}")
            self.finished_scan.emit(0, 0)

class UpdaterThread(QThread):
    """Background thread for updating dependencies"""
    progress = pyqtSignal(str)
    finished_update = pyqtSignal(bool)
    
    def __init__(self, update_func):
        super().__init__()
        self.update_func = update_func
    
    def run(self):
        old_stdout = sys.stdout
        try:
            sys.stdout = OutputCapture(self.progress)
            result = self.update_func()
            sys.stdout = old_stdout
            self.finished_update.emit(result if result is not None else True)
        except Exception as e:
            sys.stdout = old_stdout
            self.progress.emit(f"Error: {e}")
            self.finished_update.emit(False)

class ScanProgressDialog(QDialog):
    """Dialog showing scanning progress with console output"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('scan_dialog.title'))
        self.setMinimumSize(600, 400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel(tr('scan_dialog.scanning'))
        self.status_label.setObjectName("scanStatusLabel")
        layout.addWidget(self.status_label)
        
        # Progress bar (indeterminate)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("scanProgressBar")
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress_bar)
        
        # Console output
        self.console = QTextEdit()
        self.console.setObjectName("scanConsole")
        self.console.setReadOnly(True)
        layout.addWidget(self.console, 1)
        
        # Close button (disabled during scan)
        self.close_btn = QPushButton(tr('scan_dialog.close'))
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)
        
        self.scanner_thread = None
    
    def start_scan(self, config_file, paths, ffmpeg_path=None, ffprobe_path=None):
        self.scanner_thread = ScannerThread(config_file, paths, ffmpeg_path, ffprobe_path)
        self.scanner_thread.progress.connect(self.append_log)
        self.scanner_thread.finished_scan.connect(self.on_scan_finished)
        self.scanner_thread.start()
    
    def append_log(self, text):
        if '\r' in text:
            # Handle carriage return by replacing the last block
            cursor = self.console.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            cursor.insertText(text.replace('\r', '').rstrip())
        else:
            self.console.append(text)
            
        # Auto-scroll to bottom
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def on_scan_finished(self, videos, folders):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.status_label.setText(tr('scan_dialog.complete', folders=folders, videos=videos))
        self.close_btn.setEnabled(True)
    
    def closeEvent(self, event):
        if self.scanner_thread and self.scanner_thread.isRunning():
            event.ignore()
        else:
            super().closeEvent(event)

class UpdateProgressDialog(QDialog):
    """Dialog showing update progress with console output"""
    def __init__(self, parent=None, title=None):
        super().__init__(parent)
        self.setWindowTitle(title or tr('settings.libmpv_updating'))
        self.setMinimumSize(600, 300)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel(tr('settings.libmpv_updating'))
        self.status_label.setObjectName("scanStatusLabel")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("scanProgressBar")
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress_bar)
        
        self.console = QTextEdit()
        self.console.setObjectName("scanConsole")
        self.console.setReadOnly(True)
        layout.addWidget(self.console, 1)
        
        self.close_btn = QPushButton(tr('scan_dialog.close'))
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)
        
        self.updater_thread = None
    
    def start_update(self, update_func):
        self.updater_thread = UpdaterThread(update_func)
        self.updater_thread.progress.connect(self.append_log)
        self.updater_thread.finished_update.connect(self.on_update_finished)
        self.updater_thread.start()
    
    def append_log(self, text):
        if '\r' in text:
            cursor = self.console.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            cursor.insertText(text.replace('\r', '').rstrip())
        else:
            self.console.append(text)
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def on_update_finished(self, success):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        if success:
            self.status_label.setText(tr('libmpv_updater.success', version=''))
        else:
            self.status_label.setText(tr('libmpv_updater.error', error=''))
        self.close_btn.setEnabled(True)
    
    def closeEvent(self, event):
        if self.updater_thread and self.updater_thread.isRunning():
            event.ignore()
        else:
            super().closeEvent(event)

class SettingsDialog(QDialog):
    def __init__(self, parent=None, config_file=None):
        super().__init__(parent)
        self.config_file = config_file
        self.setWindowTitle(tr('settings.title'))
        self.setMinimumWidth(650)
        self.setup_ui()
        self.load_current_settings()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        content_layout = QHBoxLayout()
        
        library_group = QGroupBox(tr('settings.library_group'))
        library_layout = QVBoxLayout()

        self.pathslist = QTreeWidget()
        self.pathslist.setHeaderHidden(True)
        library_layout.addWidget(self.pathslist)

        buttons = QHBoxLayout()
        add_btn = QPushButton(tr('settings.add'))
        add_btn.clicked.connect(self.add_path)
        buttons.addWidget(add_btn)

        edit_btn = QPushButton(tr('settings.edit'))
        edit_btn.clicked.connect(self.edit_path)
        buttons.addWidget(edit_btn)

        remove_btn = QPushButton(tr('settings.remove'))
        remove_btn.clicked.connect(self.remove_path)
        buttons.addWidget(remove_btn)

        library_layout.addLayout(buttons)

        self.scan_btn = QPushButton(tr('settings.scan'))
        self.scan_btn.clicked.connect(self.start_scan)
        library_layout.addWidget(self.scan_btn)

        library_group.setLayout(library_layout)
        content_layout.addWidget(library_group, 2)

        deps_group = QGroupBox(tr('settings.dependencies_group'))
        deps_layout = QVBoxLayout()
        
        self.libmpv_btn = QPushButton(tr('settings.libmpv_checking'))
        self.libmpv_btn.clicked.connect(self.update_libmpv)
        deps_layout.addWidget(self.libmpv_btn)

        self.ffmpeg_btn = QPushButton(tr('settings.ffmpeg_checking'))
        self.ffmpeg_btn.clicked.connect(self.update_ffmpeg)
        deps_layout.addWidget(self.ffmpeg_btn)
        
        deps_layout.addStretch()
        deps_group.setLayout(deps_layout)

        storage_group = QGroupBox(tr('settings.storage_group'))
        storage_layout = QVBoxLayout()
        
        self.clear_data_btn = QPushButton(tr('settings.clear_data'))
        self.clear_data_btn.setStyleSheet("background-color: #8B0000; color: white; font-weight: bold;")
        self.clear_data_btn.clicked.connect(self.clear_metadata)
        storage_layout.addWidget(self.clear_data_btn)
        
        storage_layout.addStretch()
        storage_group.setLayout(storage_layout)
        
        right_column = QVBoxLayout()
        right_column.addWidget(deps_group)
        right_column.addWidget(storage_group)
        content_layout.addLayout(right_column, 1)

        
        main_layout.addLayout(content_layout)
        
        QTimer.singleShot(100, self.check_libmpv_version)
        QTimer.singleShot(200, self.check_ffmpeg_version)

        save_btn = QPushButton(tr('settings.save'))
        save_btn.clicked.connect(self.save_settings)
        main_layout.addWidget(save_btn)

    def add_path(self):
        directory = QFileDialog.getExistingDirectory(
            self, tr('dialog.select_directory')
        )
        if directory:
            item = QTreeWidgetItem([directory])
            self.pathslist.addTopLevelItem(item)
            self._validate_path(item)

    def edit_path(self):
        current = self.pathslist.currentItem()
        if not current:
            return
        directory = QFileDialog.getExistingDirectory(
            self,
            tr('dialog.select_directory'),
            current.text(0)
        )
        if directory:
            current.setText(0, directory)
            self._validate_path(current)

    def clear_metadata(self):
        """Clear all metadata from DB via parent window."""
        reply = QMessageBox.question(
            self, tr('settings.clear_title'),
            tr('settings.clear_confirm_text'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Use parent method to clear data
            if self.parent() and hasattr(self.parent(), 'clear_metadata_force'):
                if self.parent().clear_metadata_force():
                    # Show status on parent
                    if hasattr(self.parent(), 'info_label'):
                        self.parent().info_label.setText(tr('settings.data_cleared'))
                    QMessageBox.information(self, tr('settings.clear_title'), tr('settings.clear_success'))
                else:
                    QMessageBox.critical(self, tr('settings.clear_title'), tr('settings.clear_error'))
            else:
                # If parent cannot, try directly (logic duplication)
                if self.parent() and hasattr(self.parent(), 'db'):
                    if self.parent().db.clear_all_metadata():
                        self.parent().db.vacuum()
                        if hasattr(self.parent(), 'load_courses'):
                            self.parent().load_courses()
                        QMessageBox.information(self, tr('settings.clear_title'), tr('settings.clear_success'))
                    else:
                        QMessageBox.critical(self, tr('settings.clear_title'), tr('settings.clear_error'))
                else:
                    QMessageBox.critical(self, tr('settings.clear_title'), tr('settings.db_not_available'))

    def remove_path(self):
        current = self.pathslist.currentItem()
        if not current:
            return

        msg = QMessageBox(self)
        msg.setWindowTitle(tr('settings.confirm'))
        msg.setText(tr('settings.removeconfirm'))
        msg.setIcon(QMessageBox.Icon.Question)
        yes_button = msg.addButton(tr('settings.yes'), QMessageBox.ButtonRole.YesRole)
        no_button = msg.addButton(tr('settings.no'), QMessageBox.ButtonRole.NoRole)
        msg.exec()

        if msg.clickedButton() == yes_button:
            index = self.pathslist.indexOfTopLevelItem(current)
            self.pathslist.takeTopLevelItem(index)

    def get_paths_list(self):
        paths = []
        for i in range(self.pathslist.topLevelItemCount()):
            paths.append(self.pathslist.topLevelItem(i).text(0))
        return paths

    def load_current_settings(self):
        if not self.config_file or not self.config_file.exists():
            return

        config = configparser.ConfigParser()
        config.read(self.config_file, encoding='utf-8')

        paths_str = config.get('Paths', 'paths', fallback='')
        if paths_str:
            for path in paths_str.split(';'):
                path = path.strip()
                if path:
                    item = QTreeWidgetItem([path])
                    self.pathslist.addTopLevelItem(item)
                    self._validate_path(item)

    def _validate_path(self, item):
        path = item.text(0)
        if os.path.exists(path):
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
            item.setIcon(0, icon)
            item.setToolTip(0, tr('settings.path_valid', path=path))
        else:
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)
            item.setIcon(0, icon)
            item.setToolTip(0, tr('settings.path_invalid', path=path))

    def save_settings(self):
        config = configparser.ConfigParser()
        if self.config_file.exists():
            config.read(self.config_file, encoding='utf-8')

        if 'Paths' not in config:
            config['Paths'] = {}

        paths = self.get_paths_list()
        config['Paths']['paths'] = ';'.join(paths)

        with open(self.config_file, 'w', encoding='utf-8') as f:
            config.write(f)

        self.close()

    def start_scan(self):
        paths = self.get_paths_list()
        if not paths:
            QMessageBox.warning(
                self,
                tr('settings.warning'),
                tr('settings.specify_path')
            )
            return

        # Save settings without closing
        self._save_settings_only()

        # Show scan dialog directly
        dialog = ScanProgressDialog(self)
        ffmpeg_path = None
        ffprobe_path = None
        if self.parent() and hasattr(self.parent(), 'ffmpeg_path'):
            ffmpeg_path = self.parent().ffmpeg_path
            ffprobe_path = self.parent().ffprobe_path
            
        dialog.start_scan(self.config_file, paths, ffmpeg_path, ffprobe_path)
        
        if self.parent() and hasattr(self.parent(), 'load_courses'):
            dialog.scanner_thread.finished_scan.connect(
                lambda v, f: self.parent().load_courses()
            )
        dialog.exec()

    def _save_settings_only(self):
        """Save settings without closing the dialog"""
        config = configparser.ConfigParser()
        if self.config_file.exists():
            config.read(self.config_file, encoding='utf-8')

        if 'Paths' not in config:
            config['Paths'] = {}

        paths = self.get_paths_list()
        config['Paths']['paths'] = ';'.join(paths)

        with open(self.config_file, 'w', encoding='utf-8') as f:
            config.write(f)

    def check_libmpv_version(self):
        """Check if libmpv-2.dll is up to date"""
        try:
            from update_libmpv import get_latest_release, get_dll_version
            config = configparser.ConfigParser()
            if self.config_file and os.path.exists(self.config_file):
                config.read(self.config_file, encoding='utf-8')
            
            dll_path = resolve_binary_path(config, 'libmpv_path', 'bin/libmpv-2.dll')
            bin_dir = dll_path.parent
            version_file = bin_dir / "libmpv.version"
            
            # Get local version
            local_version = None
            if version_file.exists():
                local_version = version_file.read_text().strip()
            elif dll_path.exists():
                local_version = get_dll_version(dll_path)
            
            latest_version, _ = get_latest_release()
            
            if local_version == latest_version and dll_path.exists():
                self.libmpv_btn.setText(f"✓ libmpv-2.dll ({latest_version})")
                self.libmpv_btn.setToolTip(tr('settings.libmpv_up_to_date'))
            elif dll_path.exists():
                self.libmpv_btn.setText(f"⬆ libmpv-2.dll ({local_version or '?'} → {latest_version})")
                self.libmpv_btn.setToolTip(tr('settings.libmpv_update_available'))
            else:
                self.libmpv_btn.setText(f"⬇ libmpv-2.dll ({latest_version})")
                self.libmpv_btn.setToolTip(tr('settings.libmpv_not_installed'))
        except Exception as e:
            self.libmpv_btn.setText(f"⚠ libmpv-2.dll")
            self.libmpv_btn.setToolTip(str(e))

    def update_libmpv(self):
        """Update libmpv-2.dll with progress dialog"""
        from update_libmpv import update_libmpv as do_update
        
        dialog = UpdateProgressDialog(self, tr('libmpv_updater.title'))
        dialog.start_update(do_update)
        dialog.exec()
        
        self.check_libmpv_version()

    def check_ffmpeg_version(self):
        """Check if FFmpeg/ffprobe are present in bin folder"""
        try:
            config = configparser.ConfigParser()
            if self.config_file and os.path.exists(self.config_file):
                config.read(self.config_file, encoding='utf-8')
                
            ffmpeg_path = resolve_binary_path(config, 'ffmpeg_path', 'bin/ffmpeg.exe')
            ffprobe_path = resolve_binary_path(config, 'ffprobe_path', 'bin/ffprobe.exe')
            
            if ffmpeg_path.exists() and ffprobe_path.exists():
                self.ffmpeg_btn.setText(f"✓ FFmpeg & ffprobe")
                self.ffmpeg_btn.setToolTip(tr('settings.ffmpeg_found'))
            else:
                self.ffmpeg_btn.setText(f"⬇ {tr('settings.ffmpeg_update')}")
                self.ffmpeg_btn.setToolTip(tr('settings.ffmpeg_not_found'))
        except Exception as e:
            self.ffmpeg_btn.setText(f"⚠ FFmpeg")
            self.ffmpeg_btn.setToolTip(str(e))

    def update_ffmpeg(self):
        """Download FFmpeg with progress dialog"""
        from update_ffmpeg import download_ffmpeg
        
        # Wrap download_ffmpeg to match the expected signature (no args or default force=True)
        def do_update():
            return download_ffmpeg(force=True)
            
        dialog = UpdateProgressDialog(self, tr('ffmpeg_updater.title'))
        dialog.start_update(do_update)
        dialog.exec()
        
        self.check_ffmpeg_version()
