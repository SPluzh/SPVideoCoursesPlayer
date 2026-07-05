import sys
import os
import tempfile
import logging
from pathlib import Path
from collections import OrderedDict
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QSize, QPoint
from PyQt6.QtGui import QPixmap, QGuiApplication

PREVIEW_CACHE_MAX = 50


class PreviewPopup(QWidget):
    """
    A popup widget that displays a timestamp and a video thumbnail
    when hovering over the seek slider.
    Optimized to use libmpv for fast seeking and thumbnail generation.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
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
        self.thumb_label.setFixedSize(200, 112)  # 16:9 ratio approx
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
        self._pending_video_path = None

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
        self.debounce_timer.setInterval(50)  # 50ms debounce to reduce seek spam
        self.debounce_timer.timeout.connect(self._fetch_frame)

        # Pre-load timer: init MPV shortly after set_video() to avoid black first frame
        self._preload_timer = QTimer()
        self._preload_timer.setSingleShot(True)
        self._preload_timer.setInterval(300)
        self._preload_timer.timeout.connect(self._ensure_preview_mpv)

        self._capture_retry_count = 0
        self._capture_retry_max = 4  # Max retries for frame capture

        self.resources_dir = Path(__file__).parent / "resources"
        self.ffmpeg_path = None  # Kept for compatibility if external ffmpeg logic is ever needed, but unused now

    def set_video(self, file_path):
        """Update current video path, clear cache and pre-load into preview MPV."""
        if self.current_video_path != file_path:
            self.current_video_path = file_path
            self.cache.clear()
            self._mpv_video_loaded = False
            # Stop any pending operations
            self.debounce_timer.stop()
            self._preload_timer.stop()
            self.pending_time = None
            self._pending_video_path = None
            # Clear stale thumbnail immediately to avoid old frame flash on first hover
            self.thumb_label.clear()
            self.thumb_label.setText("...")
            # If popup is visible, hide it to avoid showing stale content
            if self.isVisible():
                self.hide()
            # Pre-load MPV after a short delay so it's ready on first hover
            if file_path:
                self._preload_timer.start()

    def _ensure_preview_mpv(self):
        """Lazily initialize preview MPV and load the current video."""
        if self.preview_mpv is None:
            self._init_preview_mpv()

        if self.preview_mpv and not self._mpv_video_loaded and self.current_video_path:
            try:
                self._pending_video_path = self.current_video_path
                self.preview_mpv.loadfile(self.current_video_path)
            except Exception as e:
                logging.error(f"Preview MPV loadfile error: {e}")

    def _init_preview_mpv(self):
        """Initialize the hidden MPV instance for previews."""
        if self.preview_mpv is not None:
            return

        try:
            import mpv

            self.preview_mpv = mpv.MPV(
                vo="null",  # No video output to screen (headless)
                ao="null",  # No audio output
                pause=True,  # Always paused
                keep_open=True,
                hwdec="auto-safe",  # Hardware acceleration
                sid="no",  # No subtitles
                video_sync="audio",
                hr_seek="yes",  # Precise seeking
                demuxer_max_bytes="5MiB",  # Reduced from 30MiB for lower memory
            )

            @self.preview_mpv.event_callback("file-loaded")
            def _on_preview_file_loaded(event):
                if self._pending_video_path == self.current_video_path:
                    self._mpv_video_loaded = True
                    logging.debug("Preview MPV: file-loaded event - marked as ready")

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
            self._pending_video_path = None
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
        y = global_pos.y() - popup_height - 15  # 15px margin

        # Keep within screen bounds - use screen at cursor position, not popup's current screen
        screen = QGuiApplication.screenAt(global_pos)
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

        # Check if video is actually loaded by verifying duration
        try:
            duration = self.preview_mpv.duration
            if duration is None or duration <= 0:
                # Video not loaded yet, silently skip
                return
        except Exception:
            # MPV not ready
            return

        time_key = self.pending_time

        # Double check cache
        if time_key in self.cache:
            self.cache.move_to_end(time_key)
            self.display_pixmap(self.cache[time_key])
            return

        try:
            # Keyframe seek for speed
            self.preview_mpv.seek(time_key, "absolute+keyframes")
            self._capture_retry_count = 0

            # Wait 40ms for MPV to decode the frame, then attempt capture with retries
            QTimer.singleShot(40, lambda: self._capture_frame_with_retry(time_key))

        except Exception as e:
            # Silently ignore errors during video switching
            logging.debug(f"Preview seek error (likely during video switch): {e}")

    def _capture_frame_with_retry(self, time_key):
        """Verify MPV has decoded the frame near time_key before capturing. Retries if not ready."""
        if not self.preview_mpv or not self._mpv_video_loaded:
            return

        # If user moved to a different position, abandon this capture
        if self.pending_time is not None and self.pending_time != time_key:
            return

        try:
            current_pos = self.preview_mpv.time_pos
        except Exception:
            current_pos = None

        # Check if MPV has seeked close enough to our target (within 2 seconds)
        if current_pos is not None and abs(current_pos - time_key) <= 2.0:
            self._capture_frame(time_key)
        elif self._capture_retry_count < self._capture_retry_max:
            self._capture_retry_count += 1
            QTimer.singleShot(40, lambda: self._capture_frame_with_retry(time_key))
        else:
            # Timed out waiting — capture anyway (may still have a valid frame)
            self._capture_frame(time_key)

    def _capture_frame(self, time_key):
        """Capture screenshot to temp file and load it."""
        if not self.preview_mpv or not self._mpv_video_loaded:
            return

        # Guard: ensure we're still on the same video we seeked for
        try:
            mpv_path = self.preview_mpv.path
            if mpv_path and self.current_video_path:
                if Path(mpv_path).resolve() != Path(self.current_video_path).resolve():
                    logging.debug("Preview capture skipped: video path mismatch")
                    return
        except Exception:
            pass

        try:
            temp_path = (
                self._temp_dir
                / f"preview_{hash(self.current_video_path)}_{time_key:.1f}.jpg"
            )

            self.preview_mpv.screenshot_to_file(str(temp_path), includes="video")

            if temp_path.exists():
                pixmap = QPixmap(str(temp_path))
                if not pixmap.isNull():
                    # Scale to fit label
                    scaled = pixmap.scaled(
                        200,
                        112,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
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
