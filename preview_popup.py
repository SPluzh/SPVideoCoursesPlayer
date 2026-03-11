
import sys
import os
import tempfile
import logging
from pathlib import Path
from collections import OrderedDict
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QSize, QPoint
from PyQt6.QtGui import QPixmap

PREVIEW_CACHE_MAX = 50

class PreviewPopup(QWidget):
    """
    A popup widget that displays a timestamp and a video thumbnail
    when hovering over the seek slider.
    Optimized to use libmpv for fast seeking and thumbnail generation.
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
        
        # Container style done via PreviewPopup selector in QSS

        # Thumbnail Label
        self.thumb_label = QLabel()
        self.thumb_label.setObjectName("previewThumb")
        self.thumb_label.setFixedSize(200, 112) # 16:9 ratio approx
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setText("...") 
        self.layout.addWidget(self.thumb_label)
        
        # Time Label
        self.time_label = QLabel("00:00")
        self.time_label.setObjectName("previewTimeLabel")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.time_label)

        # State
        self.current_video_path = None
        self.cache = OrderedDict()  # LRU cache {timestamp_sec: QPixmap}
        self.pending_time = None
        
        # MPV instance for preview — created lazily on first hover
        self.preview_mpv = None
        self._mpv_video_loaded = False
        
        # Idle timer: destroy preview MPV after inactivity
        self._idle_timer = QTimer()
        self._idle_timer.setSingleShot(True)
        self._idle_timer.setInterval(10000)  # 10 seconds idle → destroy MPV
        self._idle_timer.timeout.connect(self._destroy_preview_mpv)
        
        # Temp dir for screenshots
        self._temp_dir = Path(tempfile.gettempdir()) / "spvideoplayer_preview"
        try:
            self._temp_dir.mkdir(exist_ok=True)
        except Exception as e:
            logging.error(f"Error creating temp dir for previews: {e}")
        
        # Debounce Timer
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(15) # Optimized: 15ms
        self.debounce_timer.timeout.connect(self._fetch_frame)
        
        self.resources_dir = Path(__file__).parent / "resources"
        self.ffmpeg_path = None # Kept for compatibility if external ffmpeg logic is ever needed, but unused now

    def set_video(self, file_path):
        """Update current video path, clear cache. MPV will load lazily on hover."""
        if self.current_video_path != file_path:
            self.current_video_path = file_path
            self.cache.clear()
            self._mpv_video_loaded = False
            # Don't init MPV here — it will happen lazily on first hover

    def _ensure_preview_mpv(self):
        """Lazily initialize preview MPV and load the current video."""
        if self.preview_mpv is None:
            self._init_preview_mpv()
        
        if self.preview_mpv and not self._mpv_video_loaded and self.current_video_path:
            try:
                self.preview_mpv.loadfile(self.current_video_path)
                self._mpv_video_loaded = True
            except Exception as e:
                logging.error(f"Preview MPV loadfile error: {e}")

    def _init_preview_mpv(self):
        """Initialize the hidden MPV instance for previews."""
        if self.preview_mpv is not None:
            return
            
        try:
            import mpv
            self.preview_mpv = mpv.MPV(
                vo='null',           # No video output to screen (headless)
                ao='null',           # No audio output
                pause=True,          # Always paused
                keep_open=True,
                hwdec='auto-safe',   # Hardware acceleration
                sid='no',            # No subtitles
                video_sync='audio',
                hr_seek='yes',       # Precise seeking
                demuxer_max_bytes='5MiB',  # Reduced from 30MiB for lower memory
            )
            logging.debug("Preview MPV initialized (lazy)")
        except Exception as e:
            logging.error(f"Failed to create preview MPV: {e}")
            self.preview_mpv = None

    def _destroy_preview_mpv(self):
        """Destroy preview MPV to free memory when idle."""
        if self.preview_mpv:
            try:
                self.preview_mpv.terminate()
            except Exception:
                pass
            self.preview_mpv = None
            self._mpv_video_loaded = False
            logging.debug("Preview MPV destroyed (idle timeout)")

    def update_content(self, seconds, global_pos):
        """Update popup content and position."""
        # Reset idle timer — MPV is being used
        self._idle_timer.stop()
        self._idle_timer.start()
        
        # 1. Update Time Label
        seconds = max(0, seconds)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            time_str = f"{int(h):d}:{int(m):02d}:{int(s):02d}"
        else:
            time_str = f"{int(m):02d}:{int(s):02d}"
        self.time_label.setText(time_str)
        
        # 2. Position
        popup_width = self.width()
        popup_height = self.height()
        x = global_pos.x() - popup_width // 2
        y = global_pos.y() - popup_height - 15 # 15px margin
        
        # Keep within screen bounds
        screen = self.screen()
        if screen:
            geo = screen.availableGeometry()
            x = max(geo.left(), min(x, geo.right() - popup_width))
            y = max(geo.top(), min(y, geo.bottom() - popup_height))
            
        self.move(x, y)
        
        # 3. Schedule Frame Extraction
        # Round to nearest second for better caching speed (Level 1 Optimization)
        time_key = int(seconds)
        
        if time_key in self.cache:
            self.cache.move_to_end(time_key)  # LRU: mark as recently used
            self.display_pixmap(self.cache[time_key])
            self.debounce_timer.stop()
        else:
            self.pending_time = time_key
            self.debounce_timer.start()

    def _fetch_frame(self):
        """Seek and capture frame using MPV (lazily initialized)."""
        # Ensure MPV is ready
        self._ensure_preview_mpv()
        
        if not self.preview_mpv or self.pending_time is None:
            return
            
        time_key = self.pending_time
        
        # Double check cache
        if time_key in self.cache:
            self.cache.move_to_end(time_key)
            self.display_pixmap(self.cache[time_key])
            return
        
        try:
            # Level 1 Optimization: Keyframe seek (faster but less precise)
            self.preview_mpv.seek(time_key, 'absolute+keyframes')
            
            # Level 1 Optimization: Reduced wait time (5ms)
            QTimer.singleShot(5, lambda: self._capture_frame(time_key))
            
        except Exception as e:
            logging.error(f"Preview seek error: {e}")

    def _capture_frame(self, time_key):
        """Capture screenshot to temp file and load it."""
        if not self.preview_mpv:
            return
        
        try:
            temp_path = self._temp_dir / f"preview_{hash(self.current_video_path)}_{time_key:.1f}.jpg"
            
            self.preview_mpv.screenshot_to_file(
                str(temp_path), 
                includes='video'
            )
            
            if temp_path.exists():
                pixmap = QPixmap(str(temp_path))
                if not pixmap.isNull():
                    # Scale to fit label
                    scaled = pixmap.scaled(
                        200, 112,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    # LRU eviction
                    if len(self.cache) >= PREVIEW_CACHE_MAX:
                        self.cache.popitem(last=False)
                    self.cache[time_key] = scaled
                    self.display_pixmap(scaled)
                else:
                    self.thumb_label.setText("No Preview")
                
                # Copy is in memory (QPixmap), delete file
                try:
                    temp_path.unlink(missing_ok=True)
                except:
                    pass
            else:
                 self.thumb_label.setText("...")
                
        except Exception as e:
            logging.error(f"Preview capture error: {e}")

    def display_pixmap(self, pixmap):
        self.thumb_label.setPixmap(pixmap)
        
    def cleanup(self):
        """Release resources."""
        self._idle_timer.stop()
        self._destroy_preview_mpv()
        
        # Clean temp folder
        if self._temp_dir.exists():
            try:
                for f in self._temp_dir.glob("preview_*.jpg"):
                    try:
                        f.unlink(missing_ok=True)
                    except:
                        pass
            except Exception as e:
                logging.error(f"Error cleaning temp dir: {e}")
