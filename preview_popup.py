
import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QProcess, QTimer, QSize, QPoint
from PyQt6.QtGui import QPixmap, QColor, QPainter, QBrush

class PreviewPopup(QWidget):
    """
    A popup widget that displays a timestamp and a video thumbnail
    when hovering over the seek slider.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # UI Setup
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        
        # Container style
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 6px;
                color: #ffffff;
            }
            QLabel {
                border: none;
                background-color: transparent;
            }
        """)

        # Thumbnail Label
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(200, 112) # 16:9 ratio approx
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet("background-color: #000000; border-radius: 4px;")
        self.thumb_label.setText("...") 
        self.layout.addWidget(self.thumb_label)
        
        # Time Label
        self.time_label = QLabel("00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("""
            background-color: #444444; 
            color: #eaeaea;
            border-radius: 3px; 
            padding: 2px 6px; 
            font-weight: bold; 
            font-size: 12px;
        """)
        self.layout.addWidget(self.time_label)

        # State
        self.current_video_path = None
        self.cache = {} # Simple cache {timestamp_sec: QPixmap}
        
        # FFmpeg Process
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self._handle_process_output)
        self.process.finished.connect(self._handle_process_finished)
        
        # Debounce Timer
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(50) # Faster response (50ms)
        self.debounce_timer.timeout.connect(self._fetch_frame)
        
        self.pending_time = None
        self.resources_dir = Path(__file__).parent / "resources"

    def set_video(self, file_path):
        """Update current video path and clear cache."""
        if self.current_video_path != file_path:
            self.current_video_path = file_path
            self.cache.clear()

    def update_content(self, seconds, global_pos):
        """Update popup content and position."""
        # 1. Update Time
        seconds = max(0, seconds) # Clamp to 0
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            time_str = f"{int(h):d}:{int(m):02d}:{int(s):02d}"
        else:
            time_str = f"{int(m):02d}:{int(s):02d}"
        self.time_label.setText(time_str)
        
        # 2. Position
        # Position above cursor, centered horizontally
        popup_width = self.width()
        popup_height = self.height()
        x = global_pos.x() - popup_width // 2
        y = global_pos.y() - popup_height - 15 # 15px margin
        
        # Keep within screen bounds (roughly)
        screen = self.screen()
        if screen:
            geo = screen.availableGeometry()
            x = max(geo.left(), min(x, geo.right() - popup_width))
            y = max(geo.top(), min(y, geo.bottom() - popup_height))
            
        self.move(x, y)
        
        # 3. Schedule Frame Extraction
        # Round to nearest second for caching efficiency
        time_key = int(seconds) 
        
        if time_key in self.cache:
            self.display_pixmap(self.cache[time_key])
            self.debounce_timer.stop()
        else:
            # Show placeholder or loading if not cached
            # Only trigger if we settled on a new time
            if self.process.state() == QProcess.ProcessState.NotRunning:
                self.pending_time = time_key
                self.debounce_timer.start()
            else:
                # If busy, update pending and restart debounce
                self.pending_time = time_key
                self.debounce_timer.start()

    def _fetch_frame(self):
        if not self.current_video_path or self.pending_time is None:
            return

        # Check cache again just in case
        if self.pending_time in self.cache:
            self.display_pixmap(self.cache[self.pending_time])
            return

        # Kill existing process if running (though we try to avoid overlap)
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(100)

        # Build FFmpeg command
        # Extract 1 frame at specific time
        # Output to stdout as BMP (fastest for QPixmap to read from data) or JPEG
        ffmpeg_exe = self._resolve_ffmpeg()
        if not ffmpeg_exe:
            self.thumb_label.setText("FFmpeg missing")
            return

        args = [
            "-ss", str(self.pending_time),
            "-i", self.current_video_path,
            "-vframes", "1",
            "-vf", "scale=200:-1",
            "-f", "image2pipe",
            "-vcodec", "mjpeg",
            "-q:v", "2", # Lower quality for speed (2-31)
            "-threads", "1", # Restrict threads to avoid cpu spike
            "-" # Pipe output
        ]
        
        self.process_data = bytearray() # Reset buffer
        self.process.start(str(ffmpeg_exe), args)

    def _handle_process_output(self):
        data = self.process.readAllStandardOutput()
        self.process_data.extend(data)

    def _handle_process_finished(self):
        if len(self.process_data) > 0:
            pixmap = QPixmap()
            if pixmap.loadFromData(self.process_data, "JPG"):
                self.cache[self.pending_time] = pixmap
                self.display_pixmap(pixmap)
            else:
                self.thumb_label.setText("Prepare failed")
        self.process_data = bytearray()

    def display_pixmap(self, pixmap):
        self.thumb_label.setPixmap(pixmap)
        
    def _resolve_ffmpeg(self):
        # Look in resources/bin
        bin_path = self.resources_dir / "bin" / "ffmpeg.exe"
        if bin_path.exists():
            return bin_path
        
        # Look on PATH
        # (This is a simplified check, usually we rely on the bunbled one)
        return "ffmpeg"
