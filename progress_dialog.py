import sys
import io
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QTextEdit, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QTextCursor

from translator import tr
from constants import ROOT_DIR, RESOURCES_DIR

class OutputCapture(io.StringIO):
    """Captures print output and emits signals"""
    def __init__(self, signal):
        super().__init__()
        self.signal = signal
        self._real_stdout = sys.__stdout__
    
    def write(self, text):
        if text:
            if '\r' in text:
                self.signal.emit(text)
            elif text.strip():
                self.signal.emit(text.rstrip())
        
        if self._real_stdout:
            self._real_stdout.write(text)
    
    def flush(self):
        if self._real_stdout:
            self._real_stdout.flush()

class BaseProgressDialog(QDialog):
    """Base dialog for showing progress with console output."""
    def __init__(self, parent=None, title="Progress"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(600, 400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel(title)
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
        
        self.thread = None

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

    def on_finished(self):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.close_btn.setEnabled(True)

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            event.ignore()
        else:
            super().closeEvent(event)

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
            old_stdout = sys.stdout
            sys.stdout = OutputCapture(self.progress)
            
            ffmpeg_path = self.ffmpeg_path or (RESOURCES_DIR / 'bin/ffmpeg.exe')
            ffprobe_path = self.ffprobe_path or (RESOURCES_DIR / 'bin/ffprobe.exe')
            bin_dir = ffmpeg_path.parent
            
            if not ffmpeg_path.exists() or not ffprobe_path.exists():
                self.progress.emit(tr('ffmpeg_updater.missing_auto_download', path=bin_dir))
                try:
                    from update_ffmpeg import download_ffmpeg
                    download_ffmpeg()
                except Exception as e:
                    self.progress.emit(tr('ffmpeg_updater.auto_download_failed', error=e))

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

class ScanProgressDialog(BaseProgressDialog):
    def __init__(self, parent=None):
        super().__init__(parent, tr('scan_dialog.title'))
        self.status_label.setText(tr('scan_dialog.scanning'))
    
    def start_scan(self, config_file, paths, ffmpeg_path=None, ffprobe_path=None):
        self.scanner_thread = ScannerThread(config_file, paths, ffmpeg_path, ffprobe_path)
        self.thread = self.scanner_thread
        self.scanner_thread.progress.connect(self.append_log)
        self.scanner_thread.finished_scan.connect(self.on_scan_finished)
        self.scanner_thread.start()
    
    def on_scan_finished(self, videos, folders):
        super().on_finished()
        self.status_label.setText(tr('scan_dialog.complete', folders=folders, videos=videos))

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

class UpdateProgressDialog(BaseProgressDialog):
    def __init__(self, parent=None, title=None):
        super().__init__(parent, title or tr('settings.libmpv_updating'))
        self.status_label.setText(title or tr('settings.libmpv_updating'))
        
    def start_update(self, update_func):
        self.updater_thread = UpdaterThread(update_func)
        self.thread = self.updater_thread
        self.updater_thread.progress.connect(self.append_log)
        self.updater_thread.finished_update.connect(self.on_update_finished)
        self.updater_thread.start()
        
    def on_update_finished(self, success):
        super().on_finished()
        if success:
            self.status_label.setText(tr('libmpv_updater.success', version=''))
        else:
            self.status_label.setText(tr('libmpv_updater.error', error=''))


class AppUpdateThread(QThread):
    """Background thread for downloading app update and creating updater script."""
    progress = pyqtSignal(str)
    finished_update = pyqtSignal(bool, str, str)  # success, zip_path, bat_path

    def __init__(self, update_info: dict):
        super().__init__()
        self.update_info = update_info

    def run(self):
        old_stdout = sys.stdout
        try:
            sys.stdout = OutputCapture(self.progress)

            from update_app import download_update, create_updater_script

            zip_path = download_update(self.update_info['url'])
            bat_path = create_updater_script(zip_path, self.update_info['latest'])

            sys.stdout = old_stdout
            self.finished_update.emit(True, str(zip_path), str(bat_path))
        except Exception as e:
            sys.stdout = old_stdout
            self.progress.emit(f"Error: {e}")
            self.finished_update.emit(False, '', '')


class AppUpdateProgressDialog(BaseProgressDialog):
    """Download progress dialog with a restart button on success."""

    restart_requested = pyqtSignal(str)  # bat_path

    def __init__(self, parent=None):
        super().__init__(parent, tr('updater.title'))
        self.status_label.setText(tr('updater.downloading'))

        self.restart_btn = QPushButton(tr('updater.update_now'))
        self.restart_btn.setObjectName("updateNowBtn")
        self.restart_btn.setVisible(False)
        self.restart_btn.clicked.connect(self._on_restart)
        self.layout().insertWidget(self.layout().indexOf(self.close_btn), self.restart_btn)

        self._bat_path = ''

    def start_download(self, update_info: dict):
        self.update_thread = AppUpdateThread(update_info)
        self.thread = self.update_thread
        self.update_thread.progress.connect(self.append_log)
        self.update_thread.finished_update.connect(self._on_download_finished)
        self.update_thread.start()

    def _on_download_finished(self, success: bool, zip_path: str, bat_path: str):
        super().on_finished()
        if success:
            self._bat_path = bat_path
            self.status_label.setText(tr('updater.success'))
            self.restart_btn.setVisible(True)
        else:
            self.status_label.setText(tr('updater.error', error=''))

    def _on_restart(self):
        self.restart_requested.emit(self._bat_path)
        self.accept()
