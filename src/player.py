import sys
from pathlib import Path
import logging
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSizePolicy,
    QStylePainter,
    QStyleOptionSlider,
    QStyle,
    QToolTip,
    QMenu,
    QComboBox,
    QFrame,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint, QRect, QSize
from PyQt6.QtGui import QIcon, QColor, QPalette, QPainter, QPen, QBrush

from mpv_handler import setup_mpv_dll, MPVVideoWidget
from translator import tr
from subtitle_popup import SubtitleButton
from subtitle_overlay import SubtitleOverlayWidget
from subtitle_translator import TranslationPopup
from volume_popup import VolumeButton
from preview_popup import PreviewPopup
from marker_dialog import MarkerDialog
from marker_gallery import MarkerGalleryWidget
from thumbnail_provider import ThumbnailProvider
from utils import format_audio_track_name

from constants import RESOURCES_DIR
from icon_manager import load_icons_dict


class ClickableSlider(QSlider):
    """Slider that jumps to click position."""

    hovered = pyqtSignal(int, QPoint)
    hover_left = pyqtSignal()
    marker_edit_requested = pyqtSignal(dict)
    marker_delete_requested = pyqtSignal(int)
    add_marker_requested = pyqtSignal(float)

    def __init__(self, orientation):
        super().__init__(orientation)
        self.setMouseTracking(True)
        self.markers = []
        self.duration = 0

    def set_markers(self, markers, duration):
        """Update markers and duration for drawing."""
        self.markers = markers
        self.duration = duration
        self.update()

    def paintEvent(self, event):
        """Custom paint to draw marker ticks."""
        try:
            super().paintEvent(event)

            # Ensure duration is a valid number
            duration = self.duration if self.duration is not None else 0

            if not self.markers or duration <= 0:
                return

            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            w = self.width()
            h = self.height()

            # Draw markers
            for marker in self.markers:
                pos_sec = marker.get("position_seconds", 0)
                m_color = marker.get("color", "#FFD700")
                if pos_sec > self.duration:
                    continue

                # Ratio 0..1
                ratio = pos_sec / self.duration
                x = int(ratio * w)

                # Draw tick mark with marker color
                painter.setPen(QPen(QColor(m_color), 2))
                tick_h = 8
                y = (h - tick_h) // 2
                painter.drawLine(x, y, x, y + tick_h)

            painter.end()
            # logging.debug("ClickableSlider paintEvent end") # DEBUG
        except Exception as e:
            logging.error(f"❌ ERROR in ClickableSlider.paintEvent: {e}", exc_info=True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos_ratio = event.position().x() / self.width()
            value = int(self.minimum() + pos_ratio * (self.maximum() - self.minimum()))
            self.setValue(value)
            self.sliderMoved.emit(value)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos_ratio = event.position().x() / self.width()
        value = int(self.minimum() + pos_ratio * (self.maximum() - self.minimum()))
        value = max(self.minimum(), min(self.maximum(), value))
        self.hovered.emit(value, event.globalPosition().toPoint())
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.hover_left.emit()
        super().leaveEvent(event)

    def contextMenuEvent(self, event):
        """Show context menu for markers."""
        try:
            duration = self.duration if self.duration is not None else 0
            if duration <= 0 or self.width() <= 0:
                return

            w = self.width()
            click_x = event.pos().x()
            click_ratio = click_x / w
            click_sec = click_ratio * duration

            # Look for nearby marker (tolerance: 10 pixels)
            tolerance_sec = (10 / w) * self.duration

            target_marker = None
            markers = self.markers if self.markers is not None else []
            for m in markers:
                if abs(m.get("position_seconds", 0) - click_sec) < tolerance_sec:
                    target_marker = m
                    break

            menu = QMenu(self)
            add_action = menu.addAction(tr("player.add_marker_title") or "Add Marker")

            edit_action = None
            delete_action = None

            if target_marker:
                menu.addSeparator()
                edit_action = menu.addAction(tr("player.edit_marker") or "Edit Marker")
                delete_action = menu.addAction(
                    tr("player.delete_marker") or "Delete Marker"
                )

            action = menu.exec(event.globalPos())
            if action == add_action:
                self.add_marker_requested.emit(click_sec)
            elif edit_action and action == edit_action:
                self.marker_edit_requested.emit(target_marker)
            elif delete_action and action == delete_action:
                self.marker_delete_requested.emit(target_marker.get("id"))
        except Exception as e:
            logging.error(
                f"❌ Error in ClickableSlider.contextMenuEvent: {e}", exc_info=True
            )


class VideoPlayerWidget(QWidget):
    """MPV-based player with audio track support."""

    video_finished = pyqtSignal()
    position_changed = pyqtSignal(int, str)
    request_hide_main_window = pyqtSignal()
    request_show_main_window = pyqtSignal()

    @property
    def is_playing(self):
        return self.player is not None and not self.player.pause

    pause_changed = pyqtSignal(bool)
    subtitle_style_changed = pyqtSignal(str, object)
    next_video_requested = pyqtSignal()
    prev_video_requested = pyqtSignal()
    markers_changed = pyqtSignal(str)  # file_path
    toggle_fullscreen_requested = pyqtSignal()
    pip_mode_requested = pyqtSignal()
    pip_mode_requested = pyqtSignal()
    pip_exit_requested = pyqtSignal()

    # MPV Thread-Safe Signals
    mpv_time_pos_changed = pyqtSignal(int)
    mpv_duration_changed = pyqtSignal(int)
    mpv_pause_changed = pyqtSignal(bool)
    mpv_file_loaded = pyqtSignal()  # Emitted from MPV thread when file is loaded
    mpv_sub_text_changed = pyqtSignal(str)
    mpv_secondary_sub_text_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        logging.debug("VideoPlayerWidget init start")
        self.db = None
        self.config = None  # Will be set by MainWindow
        self.current_file = None
        self.saved_position = 0
        self.position_restore_attempted = False
        self.slider_updating = False
        self.is_seeking_slider = False
        self.taskbar_progress = None
        self.is_loading = False
        self.auto_play_pending = False
        self._pending_file_path = None  # File path pending initialization after file-loaded
        self._cached_audio_data = None  # Cache for (tracks, selected_audio_id) to avoid duplicate DB queries
        self._cached_subtitle_data = None # Cache for subtitle tracks
        self.player = None
        self.osd_manager = None  # Will be initialized in setup_mpv
        self.sub_color = "#FFCC66"
        self.sub_border_color = "#000000"
        self.secondary_sub_color = "#E6E6FA"
        self.sub_scale = 1.0
        self.markers = []
        self._restoring_state = False  # Flag to suppress OSD during state restoration
        self._paused_by_hover = False
        self.hover_check_timer = QTimer(self)
        self.hover_check_timer.setInterval(100)
        self.hover_check_timer.timeout.connect(self._on_hover_check_timeout)

        # Marker Gallery & Thumbnailing
        self.thumb_provider = ThumbnailProvider(self)
        self.thumb_provider.finished.connect(self._on_marker_thumbnail_ready)
        self.thumb_provider.finished.connect(self._on_marker_thumbnail_ready)
        # Audio Processing State
        self.audio_opts = {
            "noise_mode": "off",
            "compressor": False,
            "deesser": False,
            "channel_mode": "normal",
            "delay": 0.0,
        }
        self.audio_track_ids = []

        # Secondary Audio State
        self.secondary_audio_enabled = False
        self.secondary_audio_track_id = None
        self.secondary_audio_volume = 10
        self.secondary_volume_debounce_timer = QTimer()
        self.secondary_volume_debounce_timer.setSingleShot(True)
        self.secondary_volume_debounce_timer.timeout.connect(self._apply_dual_audio)

        self.marker_gallery = None  # Created in setup_ui
        logging.debug("Calling setup_ui")
        self.setup_ui()
        logging.debug("Calling setup_mpv")
        self.setup_mpv()
        logging.debug("VideoPlayerWidget init done")

    def cleanup(self):
        """Cleanup resources."""
        logging.debug("VideoPlayerWidget cleanup called")
        if hasattr(self, "preview_popup"):
            self.preview_popup.cleanup()

        # Stop thumbnail provider
        if hasattr(self, "thumb_provider"):
            self.thumb_provider.stop()

        if hasattr(self, "subtitle_overlay") and self.subtitle_overlay:
            self.subtitle_overlay.close()
        if hasattr(self, "translation_popup") and self.translation_popup:
            self.translation_popup.close()

        # Shutdown main player
        if self.player:
            try:
                self.player.terminate()
            except Exception as e:
                logging.error(f"Error terminating player: {e}")
            self.player = None

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.video_container = QWidget()
        self.video_container.setAutoFillBackground(True)
        container_palette = self.video_container.palette()
        container_palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        self.video_container.setPalette(container_palette)

        container_layout = QVBoxLayout(self.video_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self.video_widget = MPVVideoWidget()
        self.video_widget.setMinimumHeight(300)
        self.video_widget.zoom_changed.connect(self.on_zoom_changed)
        self.video_widget.toggle_fullscreen_requested.connect(
            self.toggle_fullscreen_requested.emit
        )
        container_layout.addWidget(self.video_widget, 1)

        # Subtitle interactive overlay and translation popup
        self.subtitle_overlay = SubtitleOverlayWidget(self.video_widget, self)
        self.translation_popup = TranslationPopup(self.subtitle_overlay)
        self.subtitle_overlay.hide()
        self.translation_popup.hide()

        # Connect overlay signals for hover/selection
        self.subtitle_overlay.text_edit.wordHovered.connect(self._on_subtitle_word_hovered)
        self.subtitle_overlay.text_edit.selectionSelected.connect(self._on_subtitle_selection_selected)
        self.subtitle_overlay.text_edit.hoverCleared.connect(self._on_subtitle_hover_cleared)
        self.subtitle_overlay.mouseEntered.connect(self._on_subtitle_area_entered)
        self.subtitle_overlay.translateRequested.connect(self._on_subtitle_selection_selected)
        self.subtitle_overlay.prevPhraseRequested.connect(self.seek_prev_phrase)
        self.subtitle_overlay.nextPhraseRequested.connect(self.seek_next_phrase)
        self.subtitle_overlay.replayPhraseRequested.connect(self.replay_current_phrase)

        # Marker Gallery Overlay (Horizontal) - Independent window to avoid Airspace issue
        self.marker_gallery = MarkerGalleryWidget(self)
        self.marker_gallery.hide()
        self.marker_gallery.seek_requested.connect(self._on_marker_gallery_seek)
        self.marker_gallery.edit_requested.connect(self.edit_marker)
        self.marker_gallery.delete_requested.connect(self.delete_marker)

        layout.addWidget(self.video_container, 1)

        self.control_panel = QWidget()
        self.control_panel.setObjectName("controlPanel")
        panel_layout = QHBoxLayout(self.control_panel)
        panel_layout.setContentsMargins(0, 5, 0, 0)

        self.icons = load_icons_dict(["play", "pause", "next", "prev", "pip", "fullscreen", "picture-in-picture", "chevron-down"])

        # Previous Video Button
        self.prev_video_btn = QPushButton()
        self.prev_video_btn.setIcon(self.icons["prev"])
        self.prev_video_btn.setFixedSize(30, 30)
        self.prev_video_btn.setToolTip(tr("player.tooltip_prev_video"))
        self.prev_video_btn.clicked.connect(self.prev_video_requested.emit)
        self.prev_video_btn.setEnabled(False)
        panel_layout.addWidget(self.prev_video_btn)

        self.play_btn = QPushButton()
        self.play_btn.setIcon(self.icons["play"])
        self.play_btn.setObjectName("playBtn")
        self.play_btn.setFixedHeight(30)
        self.play_btn.clicked.connect(self.play_pause)
        self.play_btn.setEnabled(False)
        panel_layout.addWidget(self.play_btn)

        # Next Video Button
        self.next_video_btn = QPushButton()
        self.next_video_btn.setIcon(self.icons["next"])
        self.next_video_btn.setFixedSize(30, 30)
        self.next_video_btn.setToolTip(tr("player.tooltip_next_video"))
        self.next_video_btn.clicked.connect(self.next_video_requested.emit)
        panel_layout.addWidget(self.next_video_btn)

        self.progress_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.sliderMoved.connect(self.set_position)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.progress_slider.setEnabled(False)
        self.progress_slider.marker_edit_requested.connect(self.edit_marker)
        self.progress_slider.marker_delete_requested.connect(self.delete_marker)
        self.progress_slider.add_marker_requested.connect(self.add_marker)
        panel_layout.addWidget(self.progress_slider, 1)

        self.time_label = QLabel("00:00 / 00:00")
        panel_layout.addWidget(self.time_label, 0, Qt.AlignmentFlag.AlignVCenter)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(5, 30)
        self.speed_slider.setValue(10)
        self.speed_slider.setToolTip(tr("player.tooltip_speed"))
        self.speed_slider.valueChanged.connect(self.change_speed)
        panel_layout.addWidget(self.speed_slider)

        self.speed_label = QLabel(tr("player.speed", speed="1.0"))
        self.speed_label.setContentsMargins(0, 0, 2, 0)
        panel_layout.addWidget(self.speed_label, 0, Qt.AlignmentFlag.AlignVCenter)

        self.subtitle_btn = SubtitleButton()
        self.subtitle_btn.setObjectName("subtitleBtn")
        self.subtitle_btn.subtitleToggled.connect(self.toggle_subtitles)
        self.subtitle_btn.subtitleChanged.connect(self.change_subtitle_track)
        self.subtitle_btn.popup.styleChanged.connect(self.change_subtitle_style)
        self.subtitle_btn.popup.interactiveToggled.connect(self.toggle_interactive_subtitles)
        self.subtitle_btn.secondarySubtitleToggled.connect(self._on_secondary_subtitle_toggled)
        self.subtitle_btn.secondarySubtitleChanged.connect(self._on_secondary_subtitle_changed)
        self.subtitle_btn.secondaryHoverOnlyChanged.connect(self._on_secondary_hover_only_changed)
        self.subtitle_btn.subtitleDelayChanged.connect(self._on_subtitle_delay_changed)

        self.sub_settings_btn = QPushButton()
        self.sub_settings_btn.setObjectName("subSettingsBtn")
        self.sub_settings_btn.setFixedSize(15, 30)
        self.sub_settings_btn.setIcon(self.icons["chevron-down"])
        self.sub_settings_btn.setIconSize(QSize(10, 10))
        self.sub_settings_btn.setToolTip(tr("player.tooltip_subtitle_settings"))
        self.sub_settings_btn.clicked.connect(self.subtitle_btn.show_popup)

        sub_layout = QHBoxLayout()
        sub_layout.setSpacing(0)
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.addWidget(self.subtitle_btn)
        sub_layout.addWidget(self.sub_settings_btn)
        panel_layout.addLayout(sub_layout)

        self.volume_btn = VolumeButton()
        self.volume_btn.setObjectName("volumeBtn")
        self.volume_btn.volumeChanged.connect(self.change_volume)
        self.volume_btn.audioChanged.connect(self.change_audio_track)

        # Audio Tools connections from VolumePopup
        self.volume_btn.noiseModeChanged.connect(self.set_noise_mode)
        self.volume_btn.compressorToggled.connect(self.toggle_compressor)
        self.volume_btn.deesserToggled.connect(self._on_deesser_toggled)
        self.volume_btn.channelModeChanged.connect(self._on_channel_mode_changed)
        self.volume_btn.delayChanged.connect(self._on_audio_delay_changed)

        # Secondary Audio connections
        self.volume_btn.secondaryAudioToggled.connect(self.toggle_secondary_audio)
        self.volume_btn.secondaryAudioTrackChanged.connect(
            self.set_secondary_audio_track
        )
        self.volume_btn.secondaryAudioVolumeChanged.connect(
            self.set_secondary_audio_volume
        )

        self.vol_settings_btn = QPushButton()
        self.vol_settings_btn.setObjectName("volSettingsBtn")
        self.vol_settings_btn.setFixedSize(15, 30)
        self.vol_settings_btn.setIcon(self.icons["chevron-down"])
        self.vol_settings_btn.setIconSize(QSize(10, 10))
        self.vol_settings_btn.setToolTip(tr("player.tooltip_volume_settings"))
        self.vol_settings_btn.clicked.connect(self.volume_btn.show_popup)

        vol_layout = QHBoxLayout()
        vol_layout.setSpacing(0)
        vol_layout.setContentsMargins(0, 0, 0, 0)
        vol_layout.addWidget(self.volume_btn)
        vol_layout.addWidget(self.vol_settings_btn)
        panel_layout.addLayout(vol_layout)

        # PiP Button
        self.pip_btn = QPushButton()
        self.pip_btn.setIcon(self.icons["picture-in-picture"])
        self.pip_btn.setFixedSize(30, 30)
        self.pip_btn.setToolTip(tr("player.tooltip_pip"))
        self.pip_btn.clicked.connect(self.pip_mode_requested.emit)
        panel_layout.addWidget(self.pip_btn)

        # Fullscreen Button
        self.fullscreen_btn = QPushButton()
        self.fullscreen_btn.setIcon(self.icons["fullscreen"])
        self.fullscreen_btn.setFixedSize(30, 30)
        self.fullscreen_btn.setToolTip(tr("player.tooltip_fullscreen"))
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen_requested.emit)
        panel_layout.addWidget(self.fullscreen_btn)

        # Ensure buttons don't take focus to avoid breaking global hotkeys
        for btn in [
            self.prev_video_btn,
            self.play_btn,
            self.next_video_btn,
            self.subtitle_btn,
            self.sub_settings_btn,
            self.volume_btn,
            self.vol_settings_btn,
            self.pip_btn,
            self.fullscreen_btn,
        ]:
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Sliders should also not take focus if we want Space to always work for play/pause
        self.progress_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.speed_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout.addWidget(self.control_panel)

        self.video_widget.toggle_play_pause.connect(self.play_pause)

        # Connect MPV signals to handlers
        self.mpv_time_pos_changed.connect(self.position_updated)
        self.mpv_duration_changed.connect(self.duration_changed)
        self.mpv_pause_changed.connect(self.state_changed)
        self.mpv_sub_text_changed.connect(self._on_sub_text_changed)
        self.mpv_secondary_sub_text_changed.connect(self._on_secondary_sub_text_changed)

        # Preview Popup
        self.preview_popup = PreviewPopup(self.video_widget)
        self.progress_slider.hovered.connect(self._on_slider_hovered)
        self.progress_slider.hover_left.connect(self._on_slider_left)

    def set_controls_visible(self, visible):
        """Toggle visibility of the playback control panel."""
        if hasattr(self, "control_panel"):
            self.control_panel.setVisible(visible)

    def get_video_aspect_ratio(self):
        """Get the actual aspect ratio of the current video."""
        if not self.player:
            return 16 / 9

        try:
            params = self.player.video_params
            if params and "aspect" in params and params["aspect"] > 0:
                return params["aspect"]

            # Fallback to width/height if aspect isn't explicitly set
            w = params.get("w", 0)
            h = params.get("h", 0)
            if w > 0 and h > 0:
                return w / h
        except Exception as e:
            logging.error(f"Error getting aspect ratio: {e}")

        return 16 / 9

    def _on_slider_hovered(self, value, global_pos):
        """Show preview popup on slider hover."""
        if not getattr(self, "show_preview", True):
            return

        if not self.player or not self.current_file or not self.player.duration:
            return

        duration = self.player.duration
        if duration <= 0:
            return

        # Calculate time in seconds
        # slider value is in milliseconds (set by duration_changed)
        seconds = value / 1000.0

        # Check for nearby markers
        marker_text = ""
        for m in self.markers:
            m_sec = m["position_seconds"]
            # Tolerance: e.g. 1% of duration or fixed 5 seconds, whichever is smaller
            tolerance = max(2.0, duration * 0.005)
            if abs(seconds - m_sec) < tolerance:
                marker_text = f" [{m['label']}]"
                break

        # Anchor Y to slider top to avoid jitter
        slider_geo = self.progress_slider.mapToGlobal(QPoint(0, 0))
        target_pos = QPoint(global_pos.x(), slider_geo.y())

        # Pass marker text to preview popup if supported, otherwise just update content
        # For this iteration, let's assume update_content only takes seconds.
        # We might need to modify preview_popup.py to support custom text label.
        # But for now, let's just stick to time.
        # Better: Uses QToolTip for marker label if hovered

        if marker_text:
            QToolTip.showText(global_pos, marker_text.strip(), self.progress_slider)
        else:
            QToolTip.hideText()

        self.preview_popup.update_content(seconds, target_pos)
        if self.preview_popup.isHidden():
            self.preview_popup.show()

    def _on_slider_left(self):
        """Hide preview popup."""
        self.preview_popup.hide()

    def toggle_mute(self):
        """Toggle audio mute."""
        if not self.player:
            return
        try:
            is_muted = getattr(self.player, "mute", False)
            self.player.mute = not is_muted
            # Update volume UI
            current_vol = self.player.volume
            self.volume_btn._update_icon(0 if self.player.mute else current_vol)
        except Exception as e:
            logging.error(f"Error toggling mute: {e}")

    def adjust_volume(self, delta):
        """Adjust volume by delta percentage."""
        if not self.player:
            return
        try:
            current = self.player.volume or 0
            new_vol = max(0, min(150, current + delta))
            self.player.volume = new_vol

            # Update UI
            self.volume_btn.popup.slider.blockSignals(True)
            self.volume_btn.popup.slider.setValue(int(new_vol))
            self.volume_btn.popup.slider.blockSignals(False)
            self.volume_btn._update_icon(int(new_vol))

            # Show OSD notification for volume change
            if self.osd_manager:
                self.osd_manager.show_volume(int(new_vol))
        except Exception as e:
            logging.error(f"Error adjusting volume: {e}")

    def change_volume(self, value):
        """Handle volume slider change."""
        if not self.player:
            return
        try:
            self.player.volume = value
            self.volume_btn._update_icon(value)
        except Exception as e:
            logging.error(f"Error setting volume: {e}")

    # Removed _update_volume_icon as it's now back in VolumeButton

    def adjust_speed(self, delta):
        """Adjust playback speed by delta."""
        if not self.player:
            return
        try:
            # speed_slider range is 5 (0.5x) to 30 (3.0x)
            current_slider_val = self.speed_slider.value()
            # delta is e.g. 0.1, which corresponds to 1 unit on slider
            slider_delta = int(delta * 10)
            new_val = max(5, min(30, current_slider_val + slider_delta))
            self.speed_slider.setValue(new_val)
            # change_speed is already connected to valueChanged
        except Exception as e:
            logging.error(f"Error adjusting speed: {e}")

    # ==========================
    # Audio Processing Methods
    # ==========================

    def adjust_audio_delay(self, delta):
        """Adjust audio delay by delta seconds."""
        if not self.player:
            return
        try:
            current = self.player.audio_delay or 0
            new_val = round(current + delta, 3)
            self.set_audio_delay(new_val)
        except Exception as e:
            logging.error(f"Error adjusting delay: {e}")

    def set_audio_delay(self, value, show_osd=True):
        """Set absolute audio delay in seconds."""
        self.audio_opts["delay"] = value
        if hasattr(self, "volume_btn") and self.volume_btn:
            self.volume_btn.setDelay(value)
        if self.player:
            try:
                self.player.audio_delay = value
                # Show OSD notification via OSD Manager
                if show_osd and self.osd_manager:
                    ms = int(value * 1000)
                    self.osd_manager.show_audio_delay(ms)
            except Exception as e:
                logging.error(f"Error setting delay: {e}")

    def adjust_subtitle_delay(self, delta):
        """Adjust subtitle delay by delta seconds."""
        if not self.player:
            return
        try:
            current = getattr(self, "sub_delay", 0.0)
            new_val = round(current + delta, 3)
            self.set_subtitle_delay(new_val)
        except Exception as e:
            logging.error(f"Error adjusting subtitle delay: {e}")

    def set_subtitle_delay(self, value, show_osd=True):
        """Set absolute subtitle delay in seconds."""
        self.sub_delay = value
        if hasattr(self, "subtitle_btn") and self.subtitle_btn:
            self.subtitle_btn.setDelay(value)
        if self.player:
            try:
                self.player["sub-delay"] = value
                # Show OSD notification via OSD Manager
                if show_osd and self.osd_manager:
                    ms = int(value * 1000)
                    self.osd_manager.show_subtitle_delay(ms)
            except Exception as e:
                logging.error(f"Error setting subtitle delay: {e}")

    @staticmethod
    def _escape_lavfi_path(path) -> str:
        """Build an FFmpeg-safe path string for use inside lavfi=[...] filters.

        Two levels of escaping are required (MPV option parser → FFmpeg filter parser).
        Strategy:
          1. Try relative path (no drive letter = no colon = no problem).
          2. Fallback: absolute path with double-escaped colon (\\\\: in Python → \\: in string → : in FFmpeg).
        Forward slashes are always used to avoid backslash escaping issues.
        """
        from pathlib import Path as P

        abs_path = P(path).resolve()

        # Prefer relative path to avoid the colon in drive letter entirely
        try:
            rel = abs_path.relative_to(P.cwd().resolve())
            return str(rel).replace("\\", "/")
        except ValueError:
            pass

        # Absolute path: must double-escape colon for MPV→FFmpeg two-level parsing
        # MPV parses first:  \\: → \:
        # FFmpeg parses next: \: → :   (literal colon)
        s = str(abs_path).replace("\\", "/")
        s = s.replace(":", "\\\\:")  # double backslash + colon
        return s

    def _update_audio_filters(self, force_normal=False):
        """Rebuild and apply audio filter chain."""
        if not self.player:
            return

        if (
            self.secondary_audio_enabled
            and self.secondary_audio_track_id
            and not force_normal
        ):
            self._apply_dual_audio()
            return

        # Disable lavfi-complex when falling back to regular af chain
        try:
            self.player["lavfi-complex"] = ""
        except Exception:
            pass

        filters = []
        logging.debug(
            f"DEBUG: player._update_audio_filters() with opts: {self.audio_opts}"
        )

        try:
            # 1. Noise Reduction
            mode = self.audio_opts.get("noise_mode", "off")
            if mode == "standard":
                filters.append("afftdn=nf=-25")
            elif mode == "ai":
                if self.has_ai_model():
                    rnn_path = RESOURCES_DIR / "bin" / "bd.rnn"
                    escaped = self._escape_lavfi_path(rnn_path.absolute())
                    filters.append(f"arnndn=m={escaped}")
                else:
                    logging.warning("AI Model (bd.rnn) not found")

            # 2. De-esser
            if self.audio_opts.get("deesser", False):
                filters.append("deesser=i=0.4:f=0.5:m=0.5")

            # 3. Compressor
            if self.audio_opts.get("compressor", False):
                filters.append("dynaudnorm=f=75:g=25:p=0.55")

            # 4. Channel Mapping
            ch_mode = self.audio_opts.get("channel_mode", "normal")
            if ch_mode == "mono":
                filters.append("pan=stereo|c0=c0+c1|c1=c0+c1")
            elif ch_mode == "swap":
                filters.append("pan=stereo|c0=c1|c1=c0")

            if filters:
                af_cmd = "lavfi=[" + ",".join(filters) + "]"
                logging.debug(f"DEBUG: Applying audio filters: {af_cmd}")
                self.player.af = af_cmd

            else:
                logging.debug("DEBUG: Clearing audio filters")
                self.player.af = ""
        except Exception as e:
            logging.error(f"Error applying audio filters: {e}", exc_info=True)

    def set_noise_mode(self, mode):
        logging.debug(f"DEBUG: player.set_noise_mode('{mode}')")
        if self.audio_opts["noise_mode"] == mode:
            return  # No change

        self.audio_opts["noise_mode"] = mode
        # Sync to popup button
        if hasattr(self, "volume_btn"):
            self.volume_btn.popup.blockSignals(True)
            self.volume_btn.popup.setNoiseMode(mode)
            self.volume_btn.popup.blockSignals(False)
        self._update_audio_filters()

        # Show OSD notification
        if self.osd_manager:
            self.osd_manager.show_noise_mode(mode)

    def toggle_compressor(self, enabled):
        logging.debug(f"DEBUG: player.toggle_compressor({enabled})")
        if self.audio_opts["compressor"] == enabled:
            return

        self.audio_opts["compressor"] = enabled
        if hasattr(self, "volume_btn"):
            self.volume_btn.popup.blockSignals(True)
            self.volume_btn.popup.comp_btn.setChecked(enabled)
            self.volume_btn.popup.blockSignals(False)
        self._update_audio_filters()

        # Show OSD notification
        if self.osd_manager:
            self.osd_manager.show_compressor(enabled)

    def _on_deesser_toggled(self, enabled):
        logging.debug(f"DEBUG: player._on_deesser_toggled({enabled})")
        if self.audio_opts["deesser"] == enabled:
            return

        self.audio_opts["deesser"] = enabled
        if hasattr(self, "volume_btn"):
            self.volume_btn.popup.blockSignals(True)
            self.volume_btn.popup.deess_btn.setChecked(enabled)
            self.volume_btn.popup.blockSignals(False)
        self._update_audio_filters()

        # Show OSD notification
        if self.osd_manager:
            self.osd_manager.show_deesser(enabled)

    def _on_channel_mode_changed(self, mode):
        logging.debug(f"DEBUG: player._on_channel_mode_changed('{mode}')")
        if self.audio_opts["channel_mode"] == mode:
            return

        self.audio_opts["channel_mode"] = mode
        if hasattr(self, "volume_btn"):
            self.volume_btn.popup.blockSignals(True)
            self.volume_btn.popup.mono_btn.setChecked(mode == "mono")
            self.volume_btn.popup.blockSignals(False)
        self._update_audio_filters()

        # Show OSD notification
        if self.osd_manager:
            self.osd_manager.show_mono_mode(mode == "mono")

    def _on_audio_delay_changed(self, delay_sec):
        """Update audio delay in MPV."""
        self.audio_opts["delay"] = delay_sec
        if self.current_file and self.db:
            try:
                self.db.save_audio_delay(self.current_file, delay_sec)
                logging.debug(f"Saved audio delay {delay_sec}s for {self.current_file}")
            except Exception as e:
                logging.error(f"Error saving audio delay to DB: {e}")
        if self.player:
            try:
                self.player["audio-delay"] = delay_sec
                # Show OSD notification for audio delay
                if self.osd_manager:
                    ms = int(delay_sec * 1000)
                    self.osd_manager.show_audio_delay(ms)
                logging.debug(f"DEBUG: Audio delay set to {delay_sec}s")
            except Exception as e:
                logging.error(f"Error setting audio delay: {e}")

    def _on_subtitle_delay_changed(self, delay_sec):
        """Update subtitle delay in MPV."""
        self.sub_delay = delay_sec
        if self.current_file and self.db:
            try:
                self.db.save_subtitle_delay(self.current_file, delay_sec)
                logging.debug(f"Saved subtitle delay {delay_sec}s for {self.current_file}")
            except Exception as e:
                logging.error(f"Error saving subtitle delay to DB: {e}")
        if self.player:
            try:
                self.player["sub-delay"] = delay_sec
                # Show OSD notification for subtitle delay
                if self.osd_manager:
                    ms = int(delay_sec * 1000)
                    self.osd_manager.show_subtitle_delay(ms)
                logging.debug(f"DEBUG: Subtitle delay set to {delay_sec}s")
            except Exception as e:
                logging.error(f"Error setting subtitle delay: {e}")

    def has_ai_model(self):
        return (RESOURCES_DIR / "bin" / "bd.rnn").exists()

    # ==========================
    # Secondary Audio Methods
    # ==========================

    def toggle_secondary_audio(self, enabled):
        """Enable/disable secondary audio."""
        logging.info(f"🔊 toggle_secondary_audio({enabled}) called")
        self.secondary_audio_enabled = enabled

        if self.current_file and self.db:
            self.db.save_secondary_audio(
                self.current_file,
                self.secondary_audio_track_id,
                self.secondary_audio_volume,
                enabled,
            )
            logging.info(f"💾 Saved secondary audio state to DB")

        # Stop any pending debounce timer
        if hasattr(self, "secondary_volume_debounce_timer"):
            self.secondary_volume_debounce_timer.stop()
            logging.info(f"⏱️ Stopped debounce timer")

        # When disabling secondary audio, first clear lavfi-complex, then switch to primary track
        if not enabled:
            logging.info(
                f"🔄 Secondary audio disabled - clearing filters and switching to primary track"
            )

            # First, clear lavfi-complex and apply normal filters
            logging.info(f"🎵 Calling _apply_dual_audio() to clear lavfi-complex")
            self._apply_dual_audio()

            # Then, with a delay, switch to primary audio track
            try:
                # Get the selected primary audio track
                tracks, selected_audio_id = self.db.load_audio_tracks(self.current_file)
                if selected_audio_id:
                    # Find the index of the selected track in the popup
                    for i in range(self.volume_btn.popup.audioCount()):
                        if self.volume_btn.popup.audioItemData(i) == selected_audio_id:
                            logging.info(
                                f"🔄 Scheduling switch to primary track index {i}, id {selected_audio_id}"
                            )
                            # Delay the track switch to allow lavfi-complex to clear first
                            QTimer.singleShot(
                                100, lambda idx=i: self.change_audio_track(idx)
                            )
                            break
            except Exception as e:
                logging.error(
                    f"❌ Error switching to primary track: {e}", exc_info=True
                )
        else:
            # When enabling, apply dual audio immediately
            logging.info(f"🎵 Calling _apply_dual_audio() immediately")
            self._apply_dual_audio()

    def set_secondary_audio_track(self, track_id):
        """Set secondary audio track."""
        logging.info(f"🔊 set_secondary_audio_track({track_id}) called")
        self.secondary_audio_track_id = track_id

        if self.current_file and self.db:
            self.db.save_secondary_audio(
                self.current_file,
                track_id,
                self.secondary_audio_volume,
                self.secondary_audio_enabled,
            )
            logging.info(f"💾 Saved secondary audio track to DB")

        if self.secondary_audio_enabled:
            # Stop any pending debounce timer
            if hasattr(self, "secondary_volume_debounce_timer"):
                self.secondary_volume_debounce_timer.stop()
                logging.info(f"⏱️ Stopped debounce timer")

            # Apply immediately when changing tracks
            logging.info(f"🎵 Calling _apply_dual_audio() immediately")
            self._apply_dual_audio()
        else:
            logging.info(f"⚠️ Secondary audio disabled, not applying filter")

    def set_secondary_audio_volume(self, volume):
        """Set secondary audio volume (0-100)."""
        logging.info(f"🔊 set_secondary_audio_volume({volume}) called")
        self.secondary_audio_volume = volume

        if self.current_file and self.db:
            self.db.save_secondary_audio(
                self.current_file,
                self.secondary_audio_track_id,
                volume,
                self.secondary_audio_enabled,
            )
            logging.info(f"💾 Saved secondary audio volume to DB")

        if self.secondary_audio_enabled:
            logging.info(f"⏱️ Starting debounce timer (300ms)")
            # Debounce: only apply filter after user stops adjusting (300ms delay)
            self.secondary_volume_debounce_timer.stop()
            self.secondary_volume_debounce_timer.start(300)
        else:
            logging.info(f"⚠️ Secondary audio disabled, not applying filter")

    def _get_mpv_track_id(self, track):
        """Get MPV track ID for a given track."""
        logging.info(f"🔍 _get_mpv_track_id() called with track: {track}")

        try:
            track_type = track["track_type"]
            logging.info(f"🔍 Track type: {track_type}")

            if track_type == "embedded":
                # For embedded tracks, match by ff-index
                stream_index = track["stream_index"]
                logging.info(f"🔍 Embedded track stream_index: {stream_index}")

                if stream_index is None:
                    logging.error("❌ Embedded track has no stream_index")
                    return None

                # Search MPV track list for embedded track with matching ff-index
                track_list = self.player.track_list
                logging.info(
                    f"🔍 Searching {len(track_list)} MPV tracks for embedded audio with ff-index={stream_index}"
                )

                for t in track_list:
                    if t.get("type") == "audio" and not t.get("external", False):
                        ff_index = t.get("ff-index")
                        mpv_id = t.get("id")
                        logging.info(
                            f"   - Embedded audio: MPV ID={mpv_id}, ff-index={ff_index}"
                        )

                        if ff_index == stream_index:
                            logging.info(
                                f"✅ Embedded track resolved: stream_index={stream_index}, mpv_id={mpv_id}"
                            )
                            return mpv_id

                logging.error(
                    f"❌ Could not find embedded track with stream_index={stream_index}"
                )
                return None

            elif track_type == "external":
                audio_file_path = track["audio_file_path"]
                logging.info(f"🔍 External track path: {audio_file_path}")

                if not audio_file_path:
                    logging.error("❌ External track has no audio_file_path")
                    return None

                if not Path(audio_file_path).exists():
                    logging.error(
                        f"❌ External audio file not found: {audio_file_path}"
                    )
                    return None

                logging.info(f"✅ External file exists: {audio_file_path}")

                # Check if already loaded
                logging.info("🔍 Checking if track already loaded in MPV...")
                track_list = self.player.track_list
                logging.info(f"🔍 Current MPV track list has {len(track_list)} tracks")

                for t in track_list:
                    if t.get("type") == "audio":
                        ext_filename = t.get("external-filename")
                        logging.info(
                            f"   - Audio track ID={t.get('id')}, external-filename={ext_filename}"
                        )
                        if ext_filename == audio_file_path:
                            logging.info(
                                f"✅ External track already loaded: {audio_file_path}, mpv_id={t['id']}"
                            )
                            return t["id"]

                # Load external track
                logging.info(f"📂 Loading external audio track: {audio_file_path}")
                try:
                    self.player.command("audio-add", audio_file_path, "auto")
                    logging.info(f"✅ audio-add command executed")
                except Exception as e:
                    if "-12" in str(e):
                        logging.warning(
                            f"⚠️ audio-add failed with -12. MPV may still be loading. Retrying in 1s..."
                        )
                        QTimer.singleShot(1000, self._apply_dual_audio)
                    else:
                        logging.error(
                            f"❌ Error executing audio-add command: {e}", exc_info=True
                        )
                    return None

                # Get the newly added track ID
                logging.info("🔍 Searching for newly added track...")
                track_list = self.player.track_list
                logging.info(f"🔍 Updated track list has {len(track_list)} tracks")

                for t in track_list:
                    if t.get("type") == "audio":
                        ext_filename = t.get("external-filename")
                        logging.info(
                            f"   - Audio track ID={t.get('id')}, external-filename={ext_filename}"
                        )
                        if ext_filename == audio_file_path:
                            logging.info(
                                f"✅ External track loaded: {audio_file_path}, mpv_id={t['id']}"
                            )
                            return t["id"]

                logging.error(
                    f"❌ Could not find MPV track ID for external file: {audio_file_path}"
                )
                return None
            else:
                logging.error(f"❌ Unknown track type: {track_type}")
                return None

        except Exception as e:
            logging.error(f"❌ Error getting MPV track ID: {e}", exc_info=True)
            return None

    def _apply_dual_audio(self):
        """Apply dual audio mixing with MPV."""
        logging.info("=" * 80)
        logging.info("🔊 _apply_dual_audio() CALLED")
        logging.info("=" * 80)

        if not self.player or not self.current_file:
            logging.error("❌ No player or current_file")
            return

        try:
            logging.info(f"📋 Secondary audio enabled: {self.secondary_audio_enabled}")
            logging.info(
                f"📋 Secondary audio track ID: {self.secondary_audio_track_id}"
            )
            logging.info(f"📋 Secondary audio volume: {self.secondary_audio_volume}")

            # If secondary audio is disabled, just apply normal filters
            if not self.secondary_audio_enabled or not self.secondary_audio_track_id:
                logging.info(
                    "⚠️ Secondary audio disabled or no track selected - applying normal filters"
                )
                self._update_audio_filters(force_normal=True)
                return

            # Get track info from DB
            logging.info("📂 Loading audio tracks from DB...")
            primary_tracks, primary_id = self.db.load_audio_tracks(self.current_file)
            logging.info(f"📂 Primary track ID: {primary_id}")
            logging.info(
                f"📂 Available tracks: {len(primary_tracks) if primary_tracks else 0}"
            )

            if not primary_id:
                logging.warning("❌ No primary audio track selected")
                self._update_audio_filters(force_normal=True)
                return

            logging.info("📂 Getting track info from DB...")
            primary_track = next((t for t in primary_tracks if t["id"] == primary_id), None)
            if not primary_track:
                primary_track = self.db.get_track_info("audio_tracks", primary_id)

            secondary_track = next((t for t in primary_tracks if t["id"] == self.secondary_audio_track_id), None)
            if not secondary_track and primary_tracks:
                # secondary_audio_track_id is stale (track ID changed after rescan).
                # Strategy: find the best match inside the CURRENT video's tracks list.
                old_track = self.db.get_track_info("audio_tracks", self.secondary_audio_track_id)
                if old_track:
                    old_path = old_track.get("audio_file_path") or ""
                    old_idx  = old_track.get("stream_index")
                    old_type = old_track.get("track_type")
                    
                    for t in primary_tracks:
                        if t.get("track_type") == old_type:
                            if old_path and t.get("audio_file_path") == old_path:
                                secondary_track = t
                                logging.info(
                                    f"🔊 Matched stale secondary ID {self.secondary_audio_track_id} → current track {t['id']} by file path"
                                )
                                break
                            if old_idx is not None and t.get("stream_index") == old_idx:
                                secondary_track = t
                                logging.info(
                                    f"🔊 Matched stale secondary ID {self.secondary_audio_track_id} → current track {t['id']} by stream_index"
                                )
                                break

                # Update DB and memory with current secondary track ID if it was stale
                if secondary_track:
                    old_id = self.secondary_audio_track_id
                    self.secondary_audio_track_id = secondary_track["id"]
                    logging.info(
                        f"🔊 Updating stale secondary_audio_track_id {old_id} → {self.secondary_audio_track_id} in DB"
                    )
                    try:
                        self.db.save_secondary_audio(
                            self.current_file,
                            self.secondary_audio_track_id,
                            self.secondary_audio_volume,
                            self.secondary_audio_enabled,
                        )
                    except Exception as e:
                        logging.warning(f"🔊 Could not update secondary_audio_track_id in DB: {e}")

            if not secondary_track:
                secondary_track = self.db.get_track_info(
                    "audio_tracks", self.secondary_audio_track_id
                )

            logging.info(f"📂 Primary track: {primary_track}")
            logging.info(f"📂 Secondary track: {secondary_track}")

            if not primary_track or not secondary_track:
                logging.warning("❌ Could not load track info for dual audio")
                self._update_audio_filters(force_normal=True)
                return

            # Validate tracks are different
            if primary_id == self.secondary_audio_track_id:
                logging.error(
                    "❌ Primary and secondary tracks are the same - cannot mix"
                )
                if self.osd_manager:
                    self.osd_manager.show_osd("Cannot mix same audio track")
                self._update_audio_filters(force_normal=True)
                return

            # Get current MPV track list for debugging
            try:
                track_list = self.player.track_list
                logging.info(f"🎵 MPV track list ({len(track_list)} tracks):")
                for t in track_list:
                    if t.get("type") == "audio":
                        logging.info(
                            f"   - Track ID={t.get('id')}, type={t.get('type')}, "
                            f"external={t.get('external', False)}, "
                            f"selected={t.get('selected', False)}, "
                            f"filename={t.get('external-filename', 'N/A')}"
                        )
            except Exception as e:
                logging.error(f"❌ Error getting track list: {e}")

            # Get MPV track IDs
            logging.info("🔍 Resolving MPV track IDs...")
            primary_mpv_id = self._get_mpv_track_id(primary_track)
            secondary_mpv_id = self._get_mpv_track_id(secondary_track)

            logging.info(f"🔍 Primary MPV ID: {primary_mpv_id}")
            logging.info(f"🔍 Secondary MPV ID: {secondary_mpv_id}")

            if primary_mpv_id is None or secondary_mpv_id is None:
                logging.error("❌ Could not resolve MPV track IDs")
                if self.osd_manager:
                    self.osd_manager.show_osd("Secondary audio track not found")
                self._update_audio_filters(force_normal=True)
                return

            # Validate MPV track IDs are different
            if primary_mpv_id == secondary_mpv_id:
                logging.error(
                    "❌ Primary and secondary MPV IDs are identical - cannot mix"
                )
                if self.osd_manager:
                    self.osd_manager.show_osd("Cannot mix same audio track")
                self._update_audio_filters(force_normal=True)
                return

            # Build mixing filter
            sec_vol = self.secondary_audio_volume / 100.0
            logging.info(f"🔊 Secondary volume (normalized): {sec_vol}")

            # Simplified mixing filter using lavfi-complex pad names
            # Normalize formats before mixing to prevent compatibility issues
            mix_filters = [
                f"[aid{primary_mpv_id}]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a1]",
                f"[aid{secondary_mpv_id}]volume={sec_vol},aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a2]",
                "[a1][a2]amix=inputs=2:duration=longest:dropout_transition=0,volume=2.0[amixed]",
            ]

            logging.info("🎛️ Base mixing filters:")
            for f in mix_filters:
                logging.info(f"   {f}")

            # Add DSP filters after mixing
            dsp_filters = []

            # Noise reduction
            mode = self.audio_opts.get("noise_mode", "off")
            if mode == "standard":
                dsp_filters.append("afftdn=nf=-25")
            elif mode == "ai":
                if self.has_ai_model():
                    rnn_path = RESOURCES_DIR / "bin" / "bd.rnn"
                    escaped = self._escape_lavfi_path(rnn_path.absolute())
                    dsp_filters.append(f"arnndn=m={escaped}")

            # De-esser
            if self.audio_opts.get("deesser", False):
                dsp_filters.append("deesser=i=0.4:f=0.5:m=0.5")

            # Compressor
            if self.audio_opts.get("compressor", False):
                dsp_filters.append("dynaudnorm=f=75:g=25:p=0.55")

            # Channel mode
            ch_mode = self.audio_opts.get("channel_mode", "normal")
            if ch_mode == "mono":
                dsp_filters.append("pan=stereo|c0=c0+c1|c1=c0+c1")
            elif ch_mode == "swap":
                dsp_filters.append("pan=stereo|c0=c1|c1=c0")

            if dsp_filters:
                logging.info(f"🎛️ DSP filters: {dsp_filters}")

            # Combine all filters
            if dsp_filters:
                all_filters = mix_filters + [f"[amixed]{dsp_filters[0]}[adsp0]"]
                for i, f in enumerate(dsp_filters[1:], 1):
                    all_filters.append(f"[adsp{i - 1}]{f}[adsp{i}]")
                all_filters.append(
                    f"[adsp{len(dsp_filters) - 1}]aformat=sample_fmts=s16:channel_layouts=stereo[ao]"
                )
            else:
                all_filters = mix_filters + [
                    "[amixed]aformat=sample_fmts=s16:channel_layouts=stereo[ao]"
                ]

            af_cmd = ";".join(all_filters)
            logging.info("=" * 80)
            logging.info(f"🎵 FINAL LAVFI-COMPLEX COMMAND:")
            logging.info(f"   {af_cmd}")
            logging.info("=" * 80)

            # Apply lavfi-complex
            try:
                self.player.af = ""  # Clear normal af
            except Exception:
                pass

            self.player["lavfi-complex"] = af_cmd

            logging.info(f"✅ Dual audio lavfi-complex applied successfully")

            # Verify filter was applied
            try:
                current_config = self.player["lavfi-complex"]
                logging.info(f"🔍 Current lavfi-complex property: {current_config}")
            except Exception as e:
                logging.error(f"❌ Error reading lavfi-complex property: {e}")

        except Exception as e:
            logging.error(f"❌ Error applying dual audio: {e}", exc_info=True)
            # Graceful fallback: show OSD notification and use single audio
            if self.osd_manager:
                self.osd_manager.show_osd("Secondary audio failed, using primary only")
            self._update_audio_filters(force_normal=True)

    def seek_relative(self, seconds):
        """Seek relative to current position."""
        if not self.player:
            return
        try:
            self.player.seek(seconds, "relative")
            # Show OSD notification for seek
            if self.osd_manager:
                self.osd_manager.show_seek(seconds)
        except Exception as e:
            logging.error(f"Error seeking: {e}")

    def seek_prev_phrase(self):
        """Seek to the previous subtitle phrase and resume playback."""
        if not self.player:
            return
        try:
            # Hide the translation popup and reset hover paused state
            if self.translation_popup:
                self.translation_popup.hide()
            self._paused_by_hover = False

            # Seek to previous subtitle
            self.player.command("sub-seek", -1)
            
            # Resume playback
            self.player.pause = False
            if self.taskbar_progress:
                self.taskbar_progress.set_normal()
            if self.osd_manager:
                self.osd_manager.show_pause_state(False)
        except Exception as e:
            logging.error(f"Error seeking to previous phrase: {e}")

    def seek_next_phrase(self):
        """Seek to the next subtitle phrase and resume playback."""
        if not self.player:
            return
        try:
            # Hide the translation popup and reset hover paused state
            if self.translation_popup:
                self.translation_popup.hide()
            self._paused_by_hover = False

            # Seek to next subtitle
            self.player.command("sub-seek", 1)

            # Resume playback
            self.player.pause = False
            if self.taskbar_progress:
                self.taskbar_progress.set_normal()
            if self.osd_manager:
                self.osd_manager.show_pause_state(False)
        except Exception as e:
            logging.error(f"Error seeking to next phrase: {e}")

    def replay_current_phrase(self):
        """Replay the current subtitle phrase from the beginning."""
        if not self.player:
            return
        try:
            # Hide the translation popup and reset hover paused state
            if self.translation_popup:
                self.translation_popup.hide()
            self._paused_by_hover = False

            # To replay the current phrase reliably (even when already at the start),
            # we seek forward to the next phrase, then seek backward to the start of the previous phrase.
            self.player.command("sub-seek", 1)
            self.player.command("sub-seek", -1)

            # Resume playback
            self.player.pause = False
            if self.taskbar_progress:
                self.taskbar_progress.set_normal()
            if self.osd_manager:
                self.osd_manager.show_pause_state(False)
        except Exception as e:
            logging.error(f"Error replaying current phrase: {e}")

    def seek_to_percent(self, percent):
        """Seek to a specific percentage of video duration."""
        if not self.player:
            return
        try:
            duration = self.player.duration
            if not duration or duration <= 0:
                logging.warning("Cannot seek to percent: duration not available")
                return
            
            # Calculate target position
            target_seconds = (percent / 100.0) * duration
            
            # Seek to absolute position
            self.player.seek(target_seconds, "absolute")
            
            # Show OSD notification
            if self.osd_manager:
                self.osd_manager.show_seek_percent(percent)
                
            logging.info(f"Seeked to {percent}% ({target_seconds:.2f}s / {duration:.2f}s)")
        except Exception as e:
            logging.error(f"Error seeking to percent: {e}")

    def frame_step(self):
        """Step forward one frame."""
        self.video_widget.frame_step()
        # Show OSD notification for frame step
        if self.osd_manager:
            self.osd_manager.show_frame_step(forward=True)

    def frame_back_step(self):
        """Step backward one frame."""
        self.video_widget.frame_back_step()
        # Show OSD notification for frame step
        if self.osd_manager:
            self.osd_manager.show_frame_step(forward=False)

    def screenshot_to_clipboard(self):
        """Screenshot to clipboard."""
        return self.video_widget.screenshot_to_clipboard()

    def on_zoom_changed(self, zoom_level):
        """Handle zoom change."""
        pass

    def reset_zoom(self):
        """Reset zoom via button."""
        self.video_widget.reset_zoom_pan()

    def zoom_in(self):
        """Increase zoom level."""
        self.video_widget.zoom_in()

    def zoom_out(self):
        """Decrease zoom level."""
        self.video_widget.zoom_out()

    def rotate_video(self, clockwise=True):
        """Rotate video 90° clockwise or counter-clockwise."""
        if not self.player:
            return
        current = getattr(self, '_rotation_angle', 0)
        if clockwise:
            current = (current + 90) % 360
        else:
            current = (current - 90) % 360
        self._rotation_angle = current
        try:
            self.player["video-rotate"] = current
        except Exception as e:
            logging.error(f"Error setting rotation: {e}")
            self._rotation_angle = 0

    def set_zoom_mode(self, enabled):
        """Set zoom state for Z key (hold)."""
        self.video_widget.z_key_pressed = enabled
        if enabled:
            self.video_widget.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.video_widget.setCursor(Qt.CursorShape.ArrowCursor)

    def setup_mpv(self):
        try:
            import mpv

            self.player = mpv.MPV(
                wid=str(int(self.video_widget.winId())),
                vo="gpu",
                hwdec="auto-safe",  # Enable safe hardware decoding
                sid="no",  # Disable subtitles by default
                keep_open=True,
                idle=True,
                osc=False,
                osd_level=1,
                osd_bar=False,
                osd_on_seek=False,
                input_default_bindings=False,
                input_vo_keyboard=False,
                cursor_autohide="no",
                ad_lavc_threads=2,
                ad_lavc_downmix="no",
                audio_fallback_to_null="yes",  # Do not stop on audio error
                demuxer_lavf_o="fflags=+genpts+igndts",  # Ignore timing problems
                log_handler=print,
                loglevel="info",
            )

            # Apply initial subtitle styles
            self._apply_subtitle_styles()

            @self.player.property_observer("time-pos")
            def time_observer(_name, value):
                if value is not None:
                    # self.position_updated(int(value * 1000))
                    self.mpv_time_pos_changed.emit(int(value * 1000))

            @self.player.property_observer("duration")
            def duration_observer(_name, value):
                if value is not None:
                    # self.duration_changed(int(value * 1000))
                    self.mpv_duration_changed.emit(int(value * 1000))

            @self.player.property_observer("pause")
            def pause_observer(_name, value):
                # self.state_changed(value)
                self.mpv_pause_changed.emit(value)

            @self.player.property_observer("sub-text")
            def sub_text_observer(_name, value):
                self.mpv_sub_text_changed.emit(value or "")

            try:
                @self.player.property_observer("secondary-sub-text")
                def secondary_sub_text_observer(_name, value):
                    self.mpv_secondary_sub_text_changed.emit(value or "")
            except Exception as e:
                logging.error(f"Error observing secondary-sub-text: {e}")

            @self.player.property_observer("eof-reached")
            def eof_observer(_name, value):
                if value:
                    self.video_finished.emit()

            @self.player.property_observer("playback-restart")
            def playback_restart_observer(_name, value):
                if value:
                    saved_pos = getattr(self, "saved_position", 0)
                    attempted = getattr(self, "position_restore_attempted", True)

                    logging.debug(
                        f"DEBUG: playback-restart event. value={value}, saved={saved_pos}, attempted={attempted}"
                    )

                    # Position restoration fallback: if _on_file_loaded already did it, skip
                    if saved_pos > 0 and not attempted:
                        logging.info(
                            f"DEBUG: playback-restart: scheduling position restoration ({saved_pos}s)"
                        )
                        QTimer.singleShot(50, self.restore_position)
                    elif saved_pos > 0:
                        logging.debug(
                            f"DEBUG: Skip restoration: saved={saved_pos}, attempted={attempted}"
                        )

            @self.player.property_observer("core-idle")
            def core_idle_observer(_name, value):
                logging.debug(f"DEBUG: core-idle={value}")

            @self.player.event_callback("file-loaded")
            def file_loaded_callback(_event):
                logging.info("DEBUG: MPV Event: file-loaded")
                # Emit signal to run post-load initialization on the main thread
                self.mpv_file_loaded.emit()

            # Connect file-loaded signal to main-thread handler
            self.mpv_file_loaded.connect(self._on_file_loaded)

            self.video_widget.set_player(self.player)

            # Initialize OSD Manager
            from osd_manager import OSDManager

            self.osd_manager = OSDManager(self.player)

            # Load OSD enabled state from config if available
            if hasattr(self, "config") and self.config:
                self.osd_manager.set_enabled(self.config.get_show_osd())

            # Share OSD Manager with video_widget for zoom notifications
            self.video_widget.osd_manager = self.osd_manager

            logging.info("MPV initialized successfully")
            logging.info(f"libmpv version: {self.player.mpv_version}")

        except Exception as e:
            logging.error(f"Error initializing MPV: {e}")
            # Do not raise here to allow app to start even without libmpv
            self.player = None

    def _timer_wrapper(self, name, func, *args):
        """Debug wrapper for timers"""
        logging.debug(f"Timer [{name}] START")
        try:
            func(*args)
        except Exception as e:
            logging.error(f"Timer [{name}] EXCEPTION: {e}", exc_info=True)
        logging.debug(f"Timer [{name}] END")

    def _ensure_playing(self):
        """Ensure video plays after loading."""
        try:
            if self.player and self.player.pause:
                self.player.pause = False
        except Exception as e:
            logging.error(f"Error ensuring playback: {e}")

    def _on_file_loaded(self):
        """
        Called on the main thread when MPV fires the 'file-loaded' event.
        Replaces the old QTimer chain (100/300/500/600/750/800ms) with immediate
        sequential initialization now that MPV has confirmed the file is open.
        """
        filepath = self._pending_file_path
        if not filepath:
            logging.debug("_on_file_loaded: no pending file path, skipping")
            return

        # Guard: only initialize if this is still the active file
        if self.current_file != filepath:
            logging.warning(
                f"_on_file_loaded: file changed (pending={filepath}, current={self.current_file}), skipping"
            )
            self._pending_file_path = None
            return

        logging.info(f"🎬 _on_file_loaded: running post-load initialization for {filepath}")

        try:
            # 1. Load subtitle tracks list into UI
            self.load_subtitle_tracks(filepath)
        except Exception as e:
            logging.error(f"_on_file_loaded: load_subtitle_tracks error: {e}", exc_info=True)

        try:
            # 2. Load audio tracks into UI + cache results to avoid duplicate DB call in restore_audio_track
            self.load_audio_tracks(filepath)
        except Exception as e:
            logging.error(f"_on_file_loaded: load_audio_tracks error: {e}", exc_info=True)

        try:
            # 3. Restore saved audio track (uses _cached_audio_data set by load_audio_tracks)
            self.restore_audio_track(filepath)
        except Exception as e:
            logging.error(f"_on_file_loaded: restore_audio_track error: {e}", exc_info=True)

        try:
            # 4. Restore saved subtitle track
            self.restore_subtitle_track(filepath)
        except Exception as e:
            logging.error(f"_on_file_loaded: restore_subtitle_track error: {e}", exc_info=True)

        try:
            # 4b. Restore saved secondary subtitle track
            self._restore_secondary_subtitle(filepath)
        except Exception as e:
            logging.error(f"_on_file_loaded: _restore_secondary_subtitle error: {e}", exc_info=True)

        try:
            # 5. Restore secondary audio (if enabled)
            self._restore_secondary_audio(filepath)
        except Exception as e:
            logging.error(f"_on_file_loaded: _restore_secondary_audio error: {e}", exc_info=True)

        try:
            # 5b. Restore saved subtitle delay
            saved_sub_delay = self.db.get_subtitle_delay(filepath) if self.db else 0.0
            sub_delay = saved_sub_delay if saved_sub_delay is not None else 0.0
            self.set_subtitle_delay(sub_delay, show_osd=False)
            logging.info(f"🎬 Restored subtitle delay {sub_delay}s for: {filepath}")
        except Exception as e:
            logging.error(f"_on_file_loaded: restore subtitle delay error: {e}", exc_info=True)

        try:
            # 5c. Restore saved audio delay
            saved_audio_delay = self.db.get_audio_delay(filepath) if self.db else 0.0
            audio_delay = saved_audio_delay if saved_audio_delay is not None else 0.0
            self.set_audio_delay(audio_delay, show_osd=False)
            logging.info(f"🎬 Restored audio delay {audio_delay}s for: {filepath}")
        except Exception as e:
            logging.error(f"_on_file_loaded: restore audio delay error: {e}", exc_info=True)

        try:
            # 6. Set play/pause state
            if self.auto_play_pending:
                self._ensure_playing()
                self.auto_play_pending = False
            else:
                self._load_paused()
        except Exception as e:
            logging.error(f"_on_file_loaded: play/pause state error: {e}", exc_info=True)

        # 7. Restore position (triggered by playback-restart observer but also attempt here as fallback)
        if self.saved_position > 0 and not self.position_restore_attempted:
            try:
                self.restore_position()
            except Exception as e:
                logging.error(f"_on_file_loaded: restore_position error: {e}", exc_info=True)

        self.is_loading = False
        self._pending_file_path = None
        logging.info("🎬 _on_file_loaded: initialization complete")

    def set_ffmpeg_path(self, path):
        """Set FFmpeg path for preview generation."""
        if hasattr(self, "preview_popup"):
            self.preview_popup.ffmpeg_path = path
        if hasattr(self, "thumb_provider"):
            self.thumb_provider.ffmpeg_path = path

    def load_video(self, file_path, saved_position=0, volume=100, auto_play=True, inherit_speed=False):
        """
        Load video
        file_path: path to file
        saved_position: saved position in seconds
        volume: saved volume in % (default 100)
        auto_play: automatically start playback
        inherit_speed: whether to inherit current speed if no saved speed exists
        """
        logging.info(f"🎬 ========== LOADING VIDEO ==========")
        logging.info(f"🎬 File: {file_path}")
        logging.info(f"🎬 Saved position: {saved_position}s")
        logging.info(f"🎬 Volume: {volume}%")
        logging.info(f"🎬 Auto-play: {auto_play}")
        logging.info(f"🎬 Inherit speed: {inherit_speed}")

        if not str(file_path).startswith(r"\\") and not str(file_path).startswith("//"):
            if not Path(file_path).exists():
                logging.error(f"🎬 ❌ File does not exist: {file_path}")
                return False

        if not self.player:
            # Try to re-initialize MPV if DLL was just downloaded or found
            if setup_mpv_dll():
                logging.debug("🎬 Attempting to initialize MPV (DLL found)...")
                self.setup_mpv()

            if not self.player:
                logging.error("🎬 ❌ Cannot load video, player not initialized")
                return False

        # Save speed and delays of current video before switching
        if self.current_file and self.db:
            try:
                self.db.save_video_speed(self.current_file, self.get_current_speed())
                self.db.save_subtitle_delay(self.current_file, getattr(self, "sub_delay", 0.0))
                self.db.save_audio_delay(self.current_file, self.audio_opts.get("delay", 0.0))
                logging.info(f"🎬 Saved speed {self.get_current_speed()} & delays for: {self.current_file}")
            except Exception as e:
                logging.error(f"🎬 Error saving speed/delays in load_video: {e}")

        # Restore per-video speed
        if self.db:
            try:
                saved_speed = self.db.get_video_speed(file_path)
                if saved_speed is not None:
                    logging.info(f"🎬 Restoring saved speed {saved_speed} for: {file_path}")
                    self.set_speed(saved_speed)
                elif not inherit_speed:
                    logging.info(f"🎬 No saved speed for: {file_path}, resetting to 1.0")
                    self.set_speed(1.0)
                else:
                    logging.info(f"🎬 No saved speed for: {file_path}, inheriting current speed {self.get_current_speed()}")
            except Exception as e:
                logging.error(f"🎬 Error restoring speed in load_video: {e}")

        self.current_file = file_path
        self.saved_position = saved_position
        self.position_restore_attempted = False
        self.is_loading = True
        self.auto_play_pending = auto_play
        logging.debug(
            f"🎬 Internal state: current_file={file_path}, saved_position={saved_position}, auto_play_pending={auto_play}"
        )

        # Update preview popup video path
        if hasattr(self, "preview_popup"):
            self.preview_popup.set_video(str(file_path))

        self.video_widget.reset_zoom_pan(show_osd=False)

        try:
            # Set volume BEFORE loading video
            if volume is None:
                volume = 100

            logging.debug(f"🎬 Setting volume to {volume}%")
            try:
                self.player.volume = volume
            except Exception as e:
                logging.error(f"🎬 ❌ Error setting volume: {e}")

            # Update volume UI
            if hasattr(self, "volume_btn"):
                self.volume_btn.popup.slider.blockSignals(True)
                self.volume_btn.popup.slider.setValue(int(volume))
                self.volume_btn.popup.slider.blockSignals(False)
                self.volume_btn._update_icon(int(volume))

            # Reset audio filters to prevent issues if dual audio was enabled on the previous video
            logging.debug(f"🎬 Clearing audio filters before loading new video")
            try:
                self.player["lavfi-complex"] = ""
                self.player.af = ""
                logging.debug("🎬 ✅ Audio filters cleared")
            except Exception as e:
                logging.error(f"🎬 ❌ Error clearing audio filters before load: {e}")

            logging.info(f"🎬 Calling MPV loadfile: {file_path}")
            self.player.sid = "no"
            # Store pending path so _on_file_loaded() knows which file to initialize
            self._pending_file_path = file_path
            self._cached_audio_data = None  # Clear stale cache
            self._cached_subtitle_data = None  # Clear stale subtitle cache
            self.player.loadfile(file_path)
            logging.info(f"🎬 ✅ MPV loadfile completed")
            self._apply_subtitle_styles()
            self.play_btn.setEnabled(True)
            self.progress_slider.setEnabled(True)

            # Load markers immediately (pure DB read, no MPV needed)
            logging.debug(f"🎬 Calling load_markers")
            self.load_markers(file_path)
            logging.debug(f"🎬 load_markers completed")
            # All remaining initialization runs in _on_file_loaded()
            # which is called when MPV emits the file-loaded event

            logging.info(f"🎬 ========== VIDEO LOADING INITIATED ==========")
            return True

        except Exception as e:
            logging.error(f"🎬 ❌ Error loading video: {e}", exc_info=True)
            self.is_loading = False
            self.auto_play_pending = False
            return False

    def unload_video(self):
        """Stop playback and clear player state."""
        if not self.player:
            return

        try:
            file_to_unload = self.current_file
            logging.info(f"Unloading video: {file_to_unload}")

            # Save speed and delays of current video before unloading
            if file_to_unload and self.db:
                try:
                    self.db.save_video_speed(file_to_unload, self.get_current_speed())
                    self.db.save_subtitle_delay(file_to_unload, getattr(self, "sub_delay", 0.0))
                    self.db.save_audio_delay(file_to_unload, self.audio_opts.get("delay", 0.0))
                    logging.info(f"🎬 Saved speed {self.get_current_speed()} & delays for: {file_to_unload}")
                except Exception as e:
                    logging.error(f"🎬 Error saving speed/delays in unload_video: {e}")

            # Reset current file FIRST so other methods (like save_progress) know we're stopping
            self.current_file = None
            self.saved_position = 0

            # Use 'stop' command only if we actually had a file
            if file_to_unload:
                try:
                    self.player["lavfi-complex"] = ""
                    self.player.af = ""
                    self.player.command("stop")
                except:
                    pass

            # Reset UI
            self.play_btn.setIcon(self.icons.get("play", QIcon()))
            self.play_btn.setEnabled(False)
            self.progress_slider.setValue(0)
            self.progress_slider.setEnabled(False)
            self.progress_slider.set_markers([], 0)
            self.time_label.setText("00:00 / 00:00")

            if hasattr(self, "video_widget"):
                self.video_widget.update()

            if hasattr(self, "subtitle_overlay") and self.subtitle_overlay:
                self.subtitle_overlay.set_text("")
                self.subtitle_overlay.hide()
            if hasattr(self, "translation_popup") and self.translation_popup:
                self.translation_popup.hide()
            self._paused_by_hover = False
            if hasattr(self, "hover_check_timer"):
                self.hover_check_timer.stop()

        except Exception as e:
            logging.error(f"Error unloading video: {e}")

    def _load_paused(self):
        """Load video in paused mode."""
        logging.debug(f"_load_paused called")
        if not self.player:
            return
        try:
            self.player.pause = True
            # Position restoration now handled by playback-restart event
            logging.debug(f"_load_paused finished")
        except Exception as e:
            logging.error(f"Error loading paused: {e}")

    def _start_playback(self):
        """Start playback after loading."""
        logging.debug(f"_start_playback called")
        if not self.player:
            return
        try:
            if self.player.pause:
                self.player.pause = False
            # Position restoration now handled by playback-restart event
            logging.debug(f"_start_playback finished")
        except Exception as e:
            logging.error(f"Error starting playback: {e}")

    # ADDED: Methods for audio tracks
    def load_audio_tracks(self, filepath):
        """Load list of audio tracks from DB."""
        logging.info(f"🔊 ========== LOADING AUDIO TRACKS ==========")
        logging.info(f"🔊 File: {filepath}")

        self.volume_btn.popup.clearAudio()
        self.volume_btn.popup.clearSecondaryAudio()
        self.audio_track_ids = []

        if not self.db:
            logging.error(f"🔊 ❌ Database not available")
            return

        try:
            tracks, selected_audio_id = self.db.load_audio_tracks(filepath)

            if not tracks:
                self.volume_btn.popup.addAudioItem(tr("player.no_tracks"), None)
                self.audio_track_ids.append(None)
                logging.warning(f"🔊 ⚠️ No audio tracks found in database")
                return

            logging.info(f"🔊 Found {len(tracks)} audio track(s) in database")
            logging.info(f"🔊 Selected audio ID from DB: {selected_audio_id}")

            selected_index = 0
            for i, track in enumerate(tracks):
                track_id = track.get("id")
                track_type = track.get("track_type", "unknown")
                stream_index = track.get("stream_index")
                title = track.get("title", "")
                language = track.get("language", "")
                codec = track.get("codec", "")
                is_default = track.get("is_default", 0)
                audio_file_name = track.get("audio_file_name", "")
                audio_file_path = track.get("audio_file_path", "")

                logging.info(f"🔊 Track {i + 1}:")
                logging.info(f"🔊   ID: {track_id}")
                logging.info(f"🔊   Type: {track_type}")
                logging.info(f"🔊   Stream Index: {stream_index}")
                logging.info(f"🔊   Title: {title}")
                logging.info(f"🔊   Language: {language}")
                logging.info(f"🔊   Codec: {codec}")
                logging.info(f"🔊   Is Default: {is_default}")
                if track_type == "external":
                    logging.info(f"🔊   File Name: {audio_file_name}")
                    logging.info(f"🔊   File Path: {audio_file_path}")

                label = format_audio_track_name(track)

                if track.get("is_default"):
                    label += f" [{tr('player.default')}]"

                # Add to primary list
                self.volume_btn.popup.addAudioItem(label, track_id)

                # Add to secondary list
                self.volume_btn.popup.addSecondaryAudioItem(label, track_id)

                self.audio_track_ids.append(track_id)
                if track_id == selected_audio_id:
                    selected_index = i
                    logging.info(f"🔊   ✅ This track is selected (index {i})")

            self.volume_btn.popup.setAudioIndex(selected_index)
            logging.info(f"🔊 Set UI audio index to: {selected_index}")

            # Load secondary audio settings
            sec_track_id, sec_volume, sec_enabled = self.db.load_secondary_audio(
                filepath
            )

            self.secondary_audio_track_id = sec_track_id
            self.secondary_audio_volume = sec_volume
            self.secondary_audio_enabled = sec_enabled

            logging.info(f"🔊 Secondary audio settings:")
            logging.info(f"🔊   Track ID: {sec_track_id}")
            logging.info(f"🔊   Volume: {sec_volume}")
            logging.info(f"🔊   Enabled: {sec_enabled}")

            # Update UI
            self.volume_btn.popup.setSecondaryEnabled(sec_enabled)
            self.volume_btn.popup.setSecondaryVolume(sec_volume)

            if sec_track_id:
                for i, track in enumerate(tracks):
                    if track.get("id") == sec_track_id:
                        self.volume_btn.popup.setSecondaryAudioIndex(i)
                        logging.info(f"🔊 Set secondary audio UI index to: {i}")
                        break

            logging.info(f"🔊 ========== AUDIO TRACKS LOADED ==========")
            # Cache results for restore_audio_track() to avoid a duplicate DB call
            self._cached_audio_data = (tracks, selected_audio_id)
        except Exception as e:
            logging.error(f"🔊 ❌ Error loading audio tracks: {e}", exc_info=True)


    def change_audio_track(self, index):
        """Switch audio track on selection."""
        if not self.player:
            return
        if index < 0 or not self.current_file:
            return

        track_id = self.volume_btn.popup.audioItemData(index)
        if track_id is None:
            return

        if not self.db:
            return

        try:
            track = self.db.get_track_info("audio_tracks", track_id)
        except Exception as e:
            logging.error(f"❌ DB error: {e}")
            return

        if not track:
            logging.warning("❌ Track not found")
            return

        track_type = track["track_type"]
        stream_index = track["stream_index"]
        audio_file_path = track["audio_file_path"]

        try:
            logging.info(f"🔄 Switching: {track_type}, stream={stream_index}")

            was_playing = not self.player.pause
            self.player.pause = True

            if track_type == "embedded":
                # FIXED: MPV uses 1-based indexing
                # But stream_index is already correct from DB
                aid = int(stream_index) if stream_index is not None else 1

                # KEY FIX: Reset external tracks first
                try:
                    current_tracks = self.player.track_list
                    for t in current_tracks:
                        if t.get("type") == "audio" and t.get("external", False):
                            self.player.command("audio-remove", t["id"])
                except:
                    pass

                # Now switch to embedded
                self.player.aid = aid
                logging.info(f"✅ Embedded aid={aid}")

            elif track_type == "external" and audio_file_path:
                if Path(audio_file_path).exists():
                    # Remove old external tracks
                    try:
                        current_tracks = self.player.track_list
                        for t in current_tracks:
                            if t.get("type") == "audio" and t.get("external", False):
                                self.player.command("audio-remove", t["id"])
                    except:
                        pass

                    # Add and select new one
                    self.player.command("audio-add", audio_file_path, "select")
                    logging.info(f"✅ External: {audio_file_path}")
                else:
                    logging.error(f"❌ File not found: {audio_file_path}")

            # Resume playback
            QTimer.singleShot(
                200, lambda: setattr(self.player, "pause", not was_playing)
            )

            # Save to DB
            self.db.save_selected_audio(self.current_file, track_id)

            # Show OSD notification for audio track change
            if self.osd_manager:
                track_title = track.get("title") or track.get("track_type", "Unknown")
                self.osd_manager.show_audio_track(track_title)

        except Exception as e:
            logging.error(f"❌ Switch error: {e}", exc_info=True)

    def restore_audio_track(self, filepath):
        """Restore saved audio track when loading video."""
        logging.info(f"🔊 ========== RESTORING AUDIO TRACK ==========")
        logging.info(f"🔊 File: {filepath}")

        if not self.db or not self.player:
            logging.error(
                f"🔊 ❌ Cannot restore: db={self.db is not None}, player={self.player is not None}"
            )
            return

        # Check if we're still loading the same file
        if self.current_file != filepath:
            logging.warning(
                f"🔊 ⚠️ File changed during loading. Current: {self.current_file}, Expected: {filepath}"
            )
            return

        try:
            # Use cached data from load_audio_tracks() if available to avoid duplicate DB query
            if self._cached_audio_data is not None:
                tracks, selected_audio_id = self._cached_audio_data
                logging.info("🔊 Using cached audio track data (skipping DB query)")
            else:
                tracks, selected_audio_id = self.db.load_audio_tracks(filepath)

            if not selected_audio_id:
                logging.warning("🔊 ⚠️ No saved audio track - selecting first available")
                if tracks:
                    track = tracks[0]
                    track_id = track["id"]
                    self.db.save_selected_audio(filepath, track_id)

                    track_type = track["track_type"]
                    stream_index = track["stream_index"]
                    audio_file_path = track["audio_file_path"]

                    logging.info(f"🔊 Saving first track as default:")
                    logging.info(f"🔊   Track ID: {track_id}")
                    logging.info(f"🔊   Type: {track_type}")
                    logging.info(f"🔊   Stream Index: {stream_index}")

                    if track_type == "embedded":
                        aid = int(stream_index) if stream_index is not None else 1
                        try:
                            self.player.aid = aid
                            logging.info(f"🔊 ✅ Set MPV aid={aid} (embedded)")
                        except Exception as e:
                            logging.error(
                                f"🔊 ❌ Error setting aid: {e}", exc_info=True
                            )
                    elif track_type == "external" and audio_file_path:
                        if Path(audio_file_path).exists():
                            try:
                                self.player.command(
                                    "audio-add", audio_file_path, "select"
                                )
                                logging.info(
                                    f"🔊 ✅ Added external audio: {audio_file_path}"
                                )
                            except Exception as e:
                                logging.error(
                                    f"🔊 ❌ Error adding external audio: {e}",
                                    exc_info=True,
                                )
                        else:
                            logging.error(
                                f"🔊 ❌ External audio file not found: {audio_file_path}"
                            )

                    for i in range(self.volume_btn.popup.audioCount()):
                        if self.volume_btn.popup.audioItemData(i) == track_id:
                            self.volume_btn.popup.setAudioIndex(i)
                            logging.info(f"🔊 Set UI index to: {i}")
                            break
                logging.info(f"🔊 ========== AUDIO TRACK RESTORED (DEFAULT) ==========")
                return

            track = next((t for t in tracks if t["id"] == selected_audio_id), None)

            if not track and tracks:
                # selected_audio_id is stale (track ID changed after rescan).
                # Strategy: find the best match inside the CURRENT video's tracks list.
                old_track = self.db.get_track_info("audio_tracks", selected_audio_id)
                if old_track:
                    old_path = old_track.get("audio_file_path") or ""
                    old_idx  = old_track.get("stream_index")
                    old_type = old_track.get("track_type")
                    
                    for t in tracks:
                        if t.get("track_type") == old_type:
                            if old_path and t.get("audio_file_path") == old_path:
                                track = t
                                logging.info(
                                    f"🔊 Matched stale ID {selected_audio_id} → current track {t['id']} by file path"
                                )
                                break
                            if old_idx is not None and t.get("stream_index") == old_idx:
                                track = t
                                logging.info(
                                    f"🔊 Matched stale ID {selected_audio_id} → current track {t['id']} by stream_index"
                                )
                                break

                # Fallback to the first track if still no match
                if not track:
                    track = tracks[0]
                    logging.info(
                        f"🔊 Stale ID {selected_audio_id} not found, falling back to first track {track['id']}"
                    )

            if not track:
                logging.error(
                    f"🔊 ❌ Audio track {selected_audio_id} not found — no suitable track in current list"
                )
                return

            # Update DB with current track ID if it was stale
            if track["id"] != selected_audio_id:
                logging.info(
                    f"🔊 Updating stale selected_audio_id {selected_audio_id} → {track['id']} in DB"
                )
                try:
                    self.db.save_selected_audio(filepath, track["id"])
                except Exception as e:
                    logging.warning(f"🔊 Could not update selected_audio_id in DB: {e}")

            track_type = track["track_type"]
            stream_index = track["stream_index"]
            audio_file_path = track["audio_file_path"]

            logging.info(f"🔊 Track details:")
            logging.info(f"🔊   Type: {track_type}")
            logging.info(f"🔊   Stream Index: {stream_index}")
            if track_type == "external":
                logging.info(f"🔊   File Path: {audio_file_path}")

            if track_type == "embedded":
                aid = int(stream_index) if stream_index is not None else 1
                try:
                    logging.info(f"🔊 Setting MPV aid={aid}")
                    self.player.aid = aid
                    logging.info(f"🔊 ✅ Restored embedded audio track (aid={aid})")
                except Exception as e:
                    logging.error(f"🔊 ❌ Error setting aid: {e}", exc_info=True)

            elif track_type == "external" and audio_file_path:
                if Path(audio_file_path).exists():
                    try:
                        logging.info(
                            f"🔊 Executing MPV command: audio-add {audio_file_path} select"
                        )
                        self.player.command("audio-add", audio_file_path, "select")
                        logging.info(
                            f"🔊 ✅ Restored external audio track: {audio_file_path}"
                        )
                    except Exception as e:
                        if "-12" in str(e):
                            logging.warning(
                                f"🔊 ⚠️ audio-add failed with error -12 (MPV still loading). Retrying in 1s..."
                            )
                            QTimer.singleShot(
                                1000, lambda: self.restore_audio_track(filepath)
                            )
                        else:
                            logging.error(
                                f"🔊 ❌ Error adding external audio: {e}", exc_info=True
                            )
                else:
                    logging.error(
                        f"🔊 ❌ External audio file not found: {audio_file_path}"
                    )

            logging.info(f"🔊 ========== AUDIO TRACK RESTORED ==========")
        except Exception as e:
            logging.error(f"🔊 ❌ Error in restore_audio_track: {e}", exc_info=True)

    def _restore_secondary_audio(self, filepath):
        """Restore secondary audio after loading."""
        logging.info(f"🔊 ========== RESTORING SECONDARY AUDIO ==========")
        logging.info(f"🔊 File: {filepath}")
        logging.info(f"🔊 Secondary audio enabled: {self.secondary_audio_enabled}")
        logging.info(f"🔊 Secondary audio track ID: {self.secondary_audio_track_id}")
        logging.info(f"🔊 Secondary audio volume: {self.secondary_audio_volume}")

        if self.secondary_audio_enabled:
            logging.info(f"🔊 Applying dual audio mix...")
            self._apply_dual_audio()
        else:
            logging.info(f"🔊 Secondary audio disabled, skipping")

        logging.info(f"🔊 ========== SECONDARY AUDIO RESTORE COMPLETE ==========")

    def detach_video_widget(self):
        """Detach video widget for PiP mode."""
        logging.debug("detach_video_widget called")
        # Included in layout?
        if self.video_widget.parent() == self.video_container:
            logging.debug("Removing video_widget from video_container layout")
            self.video_container.layout().removeWidget(self.video_widget)

        # The widget will be reparented by FloatingVideoWindow
        self.video_widget.setParent(None)
        self.video_widget.show()  # Ensure it's not hidden
        return self.video_widget

    def reattach_video_widget(self, widget):
        """Reattach video widget after PiP mode."""
        logging.debug("reattach_video_widget called")
        if widget != self.video_widget:
            logging.error("trying to reattach different widget")
            return

        # Add back to our layout
        logging.debug("Adding video_widget back to container layout")
        self.video_container.layout().addWidget(self.video_widget)
        # Ensure it is visible and has focus if needed
        self.video_widget.show()
        self.video_widget.setFocus()
        logging.debug("reattach_video_widget finished")

    # ===================== SUBTITLES =====================
    def load_subtitle_tracks(self, filepath):
        """Load list of subtitles from DB."""
        logging.info(f"📝 ========== LOADING SUBTITLE TRACKS ==========")
        logging.info(f"📝 File: {filepath}")

        popup = self.subtitle_btn.popup
        popup.clear()
        self.subtitle_btn.clearSecondary()

        if not self.db:
            logging.error(f"📝 ❌ Database not available")
            self.subtitle_btn.set_enabled_state(False)
            self._cached_subtitle_data = ([], None, 0)
            return

        try:
            tracks, selected_subtitle_id, subtitles_enabled = (
                self.db.load_subtitle_tracks(filepath)
            )

            logging.info(f"📝 load_subtitle_tracks: DB returned tracks count={len(tracks)}, selected_subtitle_id={selected_subtitle_id}, subtitles_enabled={subtitles_enabled}")

            if not tracks:
                logging.warning(f"📝 ⚠️ No subtitle tracks found in database, disabling subtitles.")
                self.subtitle_btn.set_enabled_state(False)
                self._cached_subtitle_data = ([], None, 0)
                logging.info(f"📝 load_subtitle_tracks: set subtitles_enabled=False in button/UI (no tracks)")
                return

            logging.info(f"📝 Found {len(tracks)} subtitle track(s) in database")
            logging.info(f"📝 Selected subtitle ID from DB: {selected_subtitle_id}")
            logging.info(f"📝 Subtitles enabled: {subtitles_enabled}")

            selected_index = 0

            for idx, track in enumerate(tracks):
                track_id = track["id"]
                track_type = track["track_type"]
                stream_index = track["stream_index"]
                subtitle_file_name = track["subtitle_file_name"]
                subtitle_file_path = track.get("subtitle_file_path", "")
                language = track["language"]
                title = track["title"]
                codec = track["codec"]
                is_default = track["is_default"]
                is_forced = track["is_forced"]

                logging.info(f"📝 Track {idx + 1}:")
                logging.info(f"📝   ID: {track_id}")
                logging.info(f"📝   Type: {track_type}")
                logging.info(f"📝   Stream Index: {stream_index}")
                logging.info(f"📝   Language: {language}")
                logging.info(f"📝   Title: {title}")
                logging.info(f"📝   Codec: {codec}")
                logging.info(f"📝   Is Default: {is_default}")
                logging.info(f"📝   Is Forced: {is_forced}")
                if track_type == "external":
                    logging.info(f"📝   File Name: {subtitle_file_name}")
                    logging.info(f"📝   File Path: {subtitle_file_path}")

                if track_type == "embedded":
                    label = f"#{stream_index}"
                    if language:
                        label += f" [{language}]"
                    if title:
                        label += f" - {title}"
                    if codec:
                        label += f" ({codec})"
                else:  # external
                    label = f"📄 {subtitle_file_name or tr('player.external_audio')}"
                    if language:
                        label += f" [{language}]"

                if is_default:
                    label += f" [{tr('player.default')}]"
                if is_forced:
                    label += f" [{tr('player.forced')}]"

                popup.addItem(label, track_id)
                self.subtitle_btn.addSecondaryItem(label, track_id)

                if track_id == selected_subtitle_id:
                    selected_index = idx
                    logging.info(f"📝   ✅ This track is selected (index {idx})")

            # Sync button state with saved subtitles_enabled
            if selected_subtitle_id:
                popup.setCurrentIndex(selected_index)
                logging.info(f"📝 Set UI subtitle index to: {selected_index}")

            # Set button state based on subtitles_enabled from DB
            self.subtitle_btn.set_enabled_state(bool(subtitles_enabled))
            logging.info(
                f"📝 Set subtitle button enabled state to: {bool(subtitles_enabled)}"
            )

            logging.info(f"📝 ========== SUBTITLE TRACKS LOADED ==========")
            self._cached_subtitle_data = (tracks, selected_subtitle_id, subtitles_enabled)

        except Exception as e:
            logging.error(f"📝 ❌ Error loading subtitle tracks: {e}", exc_info=True)
            self.subtitle_btn.set_enabled_state(False)
            self._cached_subtitle_data = ([], None, 0)

    def toggle_subtitles(self, enabled):
        """Toggle subtitles on/off."""
        if not self.player:
            return

        popup = self.subtitle_btn.popup
        if enabled:
            # Turn on — use previously selected track or first if none selected
            if popup.count() > 0:
                # Use the last selected index if valid, otherwise use 0
                index_to_use = popup.selected_index if popup.selected_index >= 0 else 0
                popup.setCurrentIndex(index_to_use)
                self.change_subtitle_track(index_to_use)
        else:
            # Turn off (but keep selected_index intact for next enable)
            try:
                self.player.sid = "no"
                logging.info("🔇 Subtitles disabled")
            except:
                pass

            # Show OSD notification for subtitles disabled
            if self.osd_manager:
                self.osd_manager.show_subtitle_off()

        # Save on/off state for current video
        if self.current_file and self.db:
            self.db.update_subtitle_enabled(self.current_file, enabled)

        self._update_subtitle_visibility()

    def toggle_subtitles_hotkey(self):
        """Toggle subtitles on/off via hotkey."""
        if not self.player:
            return
        new_state = not self.subtitle_btn.subtitles_enabled
        self.subtitle_btn.set_enabled_state(new_state)
        self.toggle_subtitles(new_state)

    def change_subtitle_style(self, property_name, value):
        """Change subtitle style in MPV."""
        if not self.player:
            return

        try:
            if property_name == "sub-color":
                # Convert HEX to MPV format (ARGB)
                hex_color = value.lstrip("#")
                self.player.sub_color = f"#FF{hex_color.upper()}"
                self.sub_color = value
                self.subtitle_style_changed.emit("sub-color", value)
                logging.info(f"📝 Subtitle color: {value}")
            elif property_name == "sub-secondary-color":
                self.secondary_sub_color = value
                self.subtitle_style_changed.emit("sub-secondary-color", value)
                logging.info(f"📝 Secondary subtitle color: {value}")
            elif property_name == "sub-border-color":
                hex_color = value.lstrip("#")
                self.player.sub_border_color = f"#FF{hex_color.upper()}"
                self.sub_border_color = value
                self.subtitle_style_changed.emit("sub-border-color", value)
                logging.info(f"📝 Subtitle border color: {value}")
            elif property_name == "sub-scale":
                # value is delta (+5 or -5)
                current_scale = getattr(self.player, "sub_scale", 1.0)
                new_scale = max(0.5, min(3.0, current_scale + value / 100.0))
                self.player.sub_scale = new_scale
                self.sub_scale = new_scale
                self.subtitle_style_changed.emit("sub-scale", new_scale)
                logging.info(f"📝 Subtitle scale: {new_scale:.2f}")
            elif property_name == "translation-target-lang":
                self.subtitle_style_changed.emit("translation-target-lang", value)
                logging.info(f"📝 Subtitle translation target language: {value}")
            elif property_name == "sub-bg-opacity":
                self.sub_bg_opacity = value
                self.subtitle_style_changed.emit("sub-bg-opacity", value)
                logging.info(f"📝 Subtitle background opacity: {value}")

            if hasattr(self, "subtitle_overlay") and self.subtitle_overlay:
                self.subtitle_overlay.set_subtitle_style(
                    self.sub_color, self.sub_border_color, self.sub_scale,
                    getattr(self, "secondary_sub_color", None),
                    getattr(self, "sub_bg_opacity", 70)
                )
        except Exception as e:
            logging.error(f"Error changing subtitle style: {e}", exc_info=True)

    # ===================== MARKERS =====================
    def load_markers(self, file_path):
        """Load markers from DB and update slider."""
        if self.db:
            self.markers = self.db.get_markers(file_path)
            self.progress_slider.set_markers(
                self.markers, self.player.duration if self.player else 0
            )

            # Update Gallery
            if self.marker_gallery:
                self.marker_gallery.set_markers(self.markers)
                # Request thumbnails
                if self.markers:
                    for m in self.markers:
                        self.thumb_provider.get_thumbnail(
                            file_path, m["position_seconds"], m["id"]
                        )

    def add_marker(self, timestamp=None):
        """Add marker at specified position or current position."""
        logging.debug("add_marker called")  # DEBUG
        if not self.player or not self.current_file:
            logging.debug("No player or file")  # DEBUG
            return

        # Get position
        if timestamp is not None:
            pos = timestamp
        else:
            try:
                pos = self.player.time_pos or 0
                logging.debug(f"Current pos: {pos}")  # DEBUG
            except Exception as e:
                logging.debug(f"Error getting time_pos: {e}")  # DEBUG
                pos = 0

        # Pause playback
        was_playing = not self.player.pause
        if was_playing:
            self.player.pause = True

        try:
            # Generate default label (e.g., "Marker 3")
            marker_count = len(self.markers) if hasattr(self, "markers") else 0
            default_label = (
                f"{tr('player.default_marker_label') or 'Marker'} {marker_count + 1}"
            )

            # Show dialog - Pass empty label to keep field clear
            duration = self.progress_slider.maximum() / 1000.0
            logging.debug(
                f"Opening dialog... Default label fallback: {default_label}, duration: {duration}"
            )  # DEBUG
            dlg = MarkerDialog(self, pos, label="", max_duration=duration)
            if dlg.exec():
                label, color, new_pos = dlg.get_data()

                # Apply default if input is empty
                if not label:
                    label = default_label

                logging.debug(
                    f"Dialog accepted, label: '{label}', color: '{color}', pos: {new_pos}"
                )  # DEBUG

                if label:
                    # Save to DB
                    if self.db:
                        logging.debug(
                            f"Saving to DB: {self.current_file}, {new_pos}, {label}, {color}"
                        )  # DEBUG
                        self.db.add_marker(self.current_file, new_pos, label, color)
                        # Reload to update UI
                        logging.debug("Reloading markers...")  # DEBUG
                        self.load_markers(self.current_file)
                        self.markers_changed.emit(self.current_file)
                        # Show OSD notification for marker added
                        if self.osd_manager:
                            self.osd_manager.show_marker_added(label)
                    else:
                        logging.error("Error - self.db is None")  # DEBUG
            else:
                logging.debug("Dialog rejected")  # DEBUG
        except Exception as e:
            logging.error(f"❌ CRASH in add_marker: {e}", exc_info=True)

        # Resume if needed
        if was_playing:
            self.player.pause = False

    def edit_marker(self, marker_data):
        """Edit an existing marker."""
        if not self.db or not self.current_file:
            return

        m_id = marker_data.get("id")
        pos = marker_data.get("position_seconds", 0)
        label = marker_data.get("label", "")
        color = marker_data.get("color", "#FFD700")

        # Pause playback
        was_playing = not self.player.pause
        if was_playing:
            self.player.pause = True

        try:
            duration = self.progress_slider.maximum() / 1000.0
            dlg = MarkerDialog(
                self, pos, label=label, color=color, max_duration=duration
            )
            dlg.setWindowTitle(tr("player.edit_marker_title") or "Edit Marker")
            if dlg.exec():
                new_label, new_color, new_pos = dlg.get_data()
                if (
                    new_label or new_pos != pos
                ):  # Allow saving even if label is empty but pos changed
                    self.db.update_marker(m_id, new_label, new_color, position=new_pos)
                    self.load_markers(self.current_file)
                    self.markers_changed.emit(self.current_file)
        except Exception as e:
            logging.error(f"Error editing marker: {e}", exc_info=True)

        if was_playing:
            self.player.pause = False

    def toggle_marker_gallery(self):
        """Toggle marker gallery visibility."""
        logging.debug(
            f"toggle_marker_gallery, visible={self.marker_gallery.isVisible() if self.marker_gallery else 'None'}"
        )
        if not self.marker_gallery:
            return

        if self.marker_gallery.isVisible():
            self.marker_gallery.hide()
            # Show OSD notification
            if self.osd_manager:
                marker_count = len(self.markers) if self.markers else 0
                self.osd_manager.show_bookmarks_gallery(False, marker_count)
        else:
            self._update_gallery_geometry()
            self.marker_gallery.show()
            self.marker_gallery.raise_()
            # Ensure markers are up to date and have thumbnails
            if self.current_file and self.markers:
                for m in self.markers:
                    self.thumb_provider.get_thumbnail(
                        self.current_file, m["position_seconds"], m["id"]
                    )
            # Show OSD notification
            if self.osd_manager:
                marker_count = len(self.markers) if self.markers else 0
                self.osd_manager.show_bookmarks_gallery(True, marker_count)

    def _on_marker_thumbnail_ready(self, request_id, pixmap):
        """Slot called when a marker thumbnail is generated."""
        logging.debug(
            f"VideoPlayerWidget._on_marker_thumbnail_ready: req_id={request_id}"
        )
        if self.marker_gallery:
            # request_id is marker_{id} or ts_{timestamp}
            if request_id.startswith("marker_"):
                m_id = int(request_id.replace("marker_", ""))
                logging.debug(f"Updating gallery thumbnail for marker_id={m_id}")
                self.marker_gallery.update_thumbnail(m_id, pixmap)
            elif request_id.startswith("ts_"):
                ts = int(request_id.replace("ts_", ""))
                logging.debug(f"Updating gallery thumbnail for timestamp={ts}")
                self.marker_gallery.update_thumbnail(ts, pixmap)
            else:
                logging.error(f"Unknown request_id format: {request_id}")

    def _on_marker_gallery_seek(self, seconds):
        """Seek to marker position and hide gallery."""
        if self.player:
            self.player.seek(seconds, "absolute", "exact")
            # self.marker_gallery.hide() # Optional: hide on seek? User didn't specify.

    def delete_marker(self, marker_id):
        """Delete marker with confirmation."""
        from PyQt6.QtWidgets import QMessageBox

        res = QMessageBox.question(
            self,
            tr("player.delete_marker_title") or "Delete Marker",
            tr("player.delete_marker_confirm")
            or "Are you sure you want to delete this marker?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if res == QMessageBox.StandardButton.Yes:
            if self.db:
                self.db.delete_marker(marker_id)
                self.load_markers(self.current_file)
            self.markers_changed.emit(self.current_file)
            # Show OSD notification for marker deleted
            if self.osd_manager:
                self.osd_manager.show_marker_deleted()

    def set_subtitle_styles(self, color, border_color, scale, secondary_color=None, bg_opacity=70):
        """Set initial subtitle styles."""
        self.sub_color = color
        self.sub_border_color = border_color
        self.sub_scale = scale
        self.sub_bg_opacity = bg_opacity
        if secondary_color is not None:
            self.secondary_sub_color = secondary_color

        # Also sync with popup
        if hasattr(self, "subtitle_btn"):
            self.subtitle_btn.popup.text_color = color
            self.subtitle_btn.popup.outline_color = border_color
            if secondary_color is not None:
                self.subtitle_btn.popup.secondary_text_color = secondary_color
            if hasattr(self.subtitle_btn.popup, "setBgOpacity"):
                self.subtitle_btn.popup.setBgOpacity(bg_opacity)
            self.subtitle_btn.popup._update_text_color_btn()
            if hasattr(self.subtitle_btn.popup, "_update_secondary_text_color_btn"):
                self.subtitle_btn.popup._update_secondary_text_color_btn()
            self.subtitle_btn.popup._update_outline_color_btn()
            if self.config:
                interactive = self.config.get_interactive_subtitles()
                self.subtitle_btn.popup.setInteractiveSubtitlesEnabled(interactive)
                target_lang = self.config.get_translation_target_lang()
                self.subtitle_btn.setTranslationTargetLang(target_lang)
                hover_only = self.config.get_secondary_subtitle_hover_only()
                self.subtitle_btn.setSecondaryHoverOnly(hover_only)

        if self.player:
            self._apply_subtitle_styles()

        if hasattr(self, "subtitle_overlay") and self.subtitle_overlay:
            self.subtitle_overlay.set_subtitle_style(
                color, border_color, scale,
                getattr(self, "secondary_sub_color", None),
                bg_opacity
            )
            if self.config:
                hover_only = self.config.get_secondary_subtitle_hover_only()
                self.subtitle_overlay.set_secondary_hover_only(hover_only)

    def _apply_subtitle_styles(self):
        """Apply stored subtitle styles to MPV player."""
        if not self.player:
            return

        try:
            # Color
            hex_color = self.sub_color.lstrip("#")
            self.player.sub_color = f"#FF{hex_color.upper()}"

            # Border
            hex_border = self.sub_border_color.lstrip("#")
            self.player.sub_border_color = f"#FF{hex_border.upper()}"

            # Scale
            self.player.sub_scale = self.sub_scale
        except Exception as e:
            logging.error(f"Error applying subtitle styles: {e}", exc_info=True)

        if hasattr(self, "subtitle_overlay") and self.subtitle_overlay:
            self.subtitle_overlay.set_subtitle_style(
                self.sub_color, self.sub_border_color, self.sub_scale,
                getattr(self, "secondary_sub_color", None),
                getattr(self, "sub_bg_opacity", 70)
            )

    def _map_ffprobe_to_mpv_sid(self, ffprobe_stream_index):
        """Map ffprobe global stream index to MPV subtitle track id."""
        if not self.player or ffprobe_stream_index is None:
            return None
        try:
            tracks = self.player.track_list or []
            logging.info(f"📝 MPV track-list: {tracks}")
            for t in tracks:
                if t.get("type") == "sub":
                    ff_idx = t.get("ff-index") if t.get("ff-index") is not None else t.get("ff_index")
                    if ff_idx is not None and int(ff_idx) == int(ffprobe_stream_index):
                        logging.info(f"📝 Mapped ffprobe stream index {ffprobe_stream_index} to MPV SID {t.get('id')}")
                        return t.get("id")
            
            # Fallback: if ff-index is not found, map by order of subtitle streams in the database
            if self.db and self.current_file:
                db_tracks, _, _ = self.db.load_subtitle_tracks(self.current_file)
                embedded_db_tracks = [t for t in db_tracks if t.get("track_type") == "embedded"]
                embedded_db_tracks.sort(key=lambda x: x.get("stream_index", 0))
                for i, track in enumerate(embedded_db_tracks):
                    if int(track.get("stream_index", 0)) == int(ffprobe_stream_index):
                        fallback_sid = i + 1
                        logging.info(f"📝 Fallback mapped stream index {ffprobe_stream_index} to order-based SID {fallback_sid}")
                        return fallback_sid
        except Exception as e:
            logging.error(f"Error mapping ffprobe stream index to MPV SID: {e}", exc_info=True)
        return None

    def change_subtitle_track(self, index):
        """Switch subtitles on selection."""
        if not self.player:
            return
        if index < 0:
            return

        popup = self.subtitle_btn.popup
        track_id = popup.itemData(index)

        # Update button state
        if track_id is not None:
            self.subtitle_btn.set_enabled_state(True)

        # If "Off" is selected
        if track_id is None:
            try:
                self.player.sid = "no"
                logging.info("🔇 Subtitles disabled")
            except:
                pass
            self._save_selected_subtitle(None)
            # Show OSD notification for subtitles disabled
            if self.osd_manager:
                self.osd_manager.show_subtitle_off()
            return

        if not self.db:
            return

        try:
            track = self.db.get_track_info("subtitle_tracks", track_id)
            if not track:
                return

            track_type = track["track_type"]
            stream_index = track["stream_index"]
            subtitle_file_path = track["subtitle_file_path"]

            if track_type == "embedded":
                # Use sid for embedded subtitles
                try:
                    mpv_sid = self._map_ffprobe_to_mpv_sid(stream_index)
                    if mpv_sid is not None:
                        self.player.sid = mpv_sid
                        logging.info(
                            f"📝 Switched to embedded subtitle track (ffprobe={stream_index}, mpv_sid={mpv_sid})"
                        )
                    else:
                        self.player.sid = stream_index
                        logging.warning(
                            f"📝 Switched to embedded subtitle track using raw stream_index {stream_index} (mapping failed)"
                        )
                except Exception as e:
                    logging.error(f"Error setting subtitle track: {e}", exc_info=True)
            else:
                # Use sub-add for external subtitles
                if subtitle_file_path and Path(subtitle_file_path).exists():
                    try:
                        self.player.command("sub-add", subtitle_file_path, "select")
                        logging.info(
                            f"📝 Loaded external subtitle: {subtitle_file_path}"
                        )
                    except Exception as e:
                        logging.error(
                            f"Error loading external subtitle: {e}", exc_info=True
                        )
                else:
                    logging.error(f"❌ Subtitle file not found: {subtitle_file_path}")

            self._save_selected_subtitle(track_id)

            # Show OSD notification for subtitle track change
            if self.osd_manager:
                track_title = track.get("title") or track.get("track_type", "Unknown")
                self.osd_manager.show_subtitle_on(track_title)

        except Exception as e:
            logging.error(f"Error changing subtitle track: {e}", exc_info=True)

        self._update_subtitle_visibility()

    def _save_selected_subtitle(self, track_id):
        """Save selected subtitles to DB."""
        if not self.current_file or not self.db:
            return

        try:
            # If track_id is None, it means subtitles are turned off
            subtitles_enabled = 0 if track_id is None else 1
            self.db.save_selected_subtitle(
                self.current_file, track_id, subtitles_enabled
            )
        except Exception as e:
            logging.error(f"Error saving selected subtitle: {e}", exc_info=True)

    def restore_subtitle_track(self, filepath):
        """Restore saved subtitles when loading video."""
        logging.info(f"📝 ========== RESTORING SUBTITLE TRACK ==========")
        logging.info(f"📝 File: {filepath}")

        if not self.db or not self.player:
            logging.error(
                f"📝 ❌ Cannot restore: db={self.db is not None}, player={self.player is not None}"
            )
            return

        try:
            if self._cached_subtitle_data is not None:
                tracks, selected_subtitle_id, subtitles_enabled = self._cached_subtitle_data
                logging.info(f"📝 Using cached subtitle data (skipping DB query)")
            else:
                tracks, selected_subtitle_id, subtitles_enabled = (
                    self.db.load_subtitle_tracks(filepath)
                )

            logging.info(f"📝 Subtitles enabled from DB: {subtitles_enabled}")
            logging.info(f"📝 Selected subtitle ID from DB: {selected_subtitle_id}")

            if not subtitles_enabled:
                logging.info(f"📝 Subtitles disabled, setting MPV sid='no'")
                try:
                    self.player.sid = "no"
                    logging.info(f"📝 ✅ MPV sid='no' set successfully")
                except Exception as e:
                    logging.error(f"📝 ❌ Error setting sid='no': {e}", exc_info=True)
                logging.info(
                    f"📝 ========== SUBTITLE TRACK RESTORED (DISABLED) =========="
                )
                self._update_subtitle_visibility()
                return

            if not selected_subtitle_id:
                logging.warning(f"📝 ⚠️ No selected subtitle ID, setting MPV sid='no' to be safe")
                try:
                    self.player.sid = "no"
                except Exception as e:
                    logging.error(f"Error setting sid='no': {e}")
                logging.info(f"📝 ========== SUBTITLE TRACK RESTORED (NONE) ==========")
                self._update_subtitle_visibility()
                return

            track = next((t for t in tracks if t["id"] == selected_subtitle_id), None)

            if not track and tracks:
                # selected_subtitle_id is stale (track ID changed after rescan).
                # Strategy: find the best match inside the CURRENT video's tracks list.

                # Step 1: query DB for the old track to get its file path / stream_index
                old_track = self.db.get_track_info("subtitle_tracks", selected_subtitle_id)
                if old_track:
                    old_path = old_track.get("subtitle_file_path") or ""
                    old_idx  = old_track.get("stream_index")
                    old_type = old_track.get("track_type")
                    # Try to find a track in the current list with the same file path or stream_index
                    for t in tracks:
                        if t.get("track_type") == old_type:
                            if old_path and t.get("subtitle_file_path") == old_path:
                                track = t
                                logging.info(
                                    f"📝 Matched stale ID {selected_subtitle_id} → current track {t['id']} by file path"
                                )
                                break
                            if old_idx is not None and t.get("stream_index") == old_idx:
                                track = t
                                logging.info(
                                    f"📝 Matched stale ID {selected_subtitle_id} → current track {t['id']} by stream_index"
                                )
                                break

                # Step 2: if still not matched and there is only one track, use it
                if not track and len(tracks) == 1:
                    track = tracks[0]
                    logging.info(
                        f"📝 Using only available track {track['id']} as fallback for stale ID {selected_subtitle_id}"
                    )

            if not track:
                logging.error(
                    f"📝 ❌ Subtitle track {selected_subtitle_id} not found — no suitable track in current list"
                )
                try:
                    self.player.sid = "no"
                except Exception as e:
                    logging.error(f"Error setting sid='no': {e}")
                self._update_subtitle_visibility()
                return

            track_type = track["track_type"]
            stream_index = track["stream_index"]
            subtitle_file_path = track["subtitle_file_path"]

            # If we resolved a stale ID to a current track, update DB to avoid the fallback next time
            if track["id"] != selected_subtitle_id:
                logging.info(
                    f"📝 Updating stale selected_subtitle_id {selected_subtitle_id} → {track['id']} in DB"
                )
                try:
                    self.db.save_selected_subtitle(filepath, track["id"])
                except Exception as e:
                    logging.warning(f"📝 Could not update selected_subtitle_id in DB: {e}")

            logging.info(f"📝 Track details:")
            logging.info(f"📝   Type: {track_type}")
            logging.info(f"📝   Stream Index: {stream_index}")
            if track_type == "external":
                logging.info(f"📝   File Path: {subtitle_file_path}")

            if track_type == "embedded":
                try:
                    mpv_sid = self._map_ffprobe_to_mpv_sid(stream_index)
                    if mpv_sid is not None:
                        logging.info(f"📝 Setting MPV sid={mpv_sid}")
                        self.player.sid = mpv_sid
                        logging.info(
                            f"📝 ✅ Restored embedded subtitle track (ffprobe={stream_index}, mpv_sid={mpv_sid})"
                        )
                    else:
                        logging.info(f"📝 Setting MPV sid={stream_index} (raw)")
                        self.player.sid = stream_index
                        logging.info(
                            f"📝 ✅ Restored embedded subtitle track using raw stream_index (sid={stream_index})"
                        )
                except Exception as e:
                    logging.error(f"📝 ❌ Error restoring subtitle: {e}", exc_info=True)
            else:
                if subtitle_file_path and Path(subtitle_file_path).exists():
                    try:
                        logging.info(
                            f"📝 Executing MPV command: sub-add {subtitle_file_path} select"
                        )
                        self.player.command("sub-add", subtitle_file_path, "select")
                        logging.info(
                            f"📝 ✅ Restored external subtitle: {subtitle_file_path}"
                        )
                    except Exception as e:
                        logging.error(
                            f"📝 ❌ Error loading external subtitle: {e}", exc_info=True
                        )
                else:
                    logging.error(
                        f"📝 ❌ External subtitle file not found: {subtitle_file_path}"
                    )

            logging.info(f"📝 ========== SUBTITLE TRACK RESTORED ==========")

        except Exception as e:
            logging.error(f"📝 ❌ Subtitle restore error: {e}", exc_info=True)

        self._update_subtitle_visibility()

    def duration_changed(self, duration_ms):
        self.progress_slider.setRange(0, duration_ms)
        # Refresh markers and ensure duration is synced to slider for context menu
        self.progress_slider.set_markers(
            self.markers if hasattr(self, "markers") else [], duration_ms / 1000.0
        )

    def restore_position(self):
        logging.info(
            f"DEBUG: restore_position entry: saved={self.saved_position}, attempted={self.position_restore_attempted}"
        )
        if (
            not self.player
            or self.saved_position <= 0
            or self.position_restore_attempted
        ):
            logging.debug(f"DEBUG: restore_position skipped (ready conditions not met)")
            return

        try:
            # Check if duration is available for bounds checking
            duration = getattr(self.player, "duration", 0)
            if duration and duration > 0:
                if self.saved_position >= duration:
                    logging.warning(
                        f"Saved position {self.saved_position} is beyond duration {duration}. Capping."
                    )
                    self.saved_position = max(0, duration - 1)
            else:
                logging.debug(
                    "DEBUG: Duration not yet available in restore_position, proceeding anyway"
                )

            # Use 'absolute' + 'exact' to ensure we end up precisely where we want
            logging.info(f"🚀 Restoring position to {self.saved_position:.2f}s")
            self.player.seek(self.saved_position, "absolute", "exact")
            self.position_restore_attempted = True
            logging.debug(f"DEBUG: restore_position command successfully sent")
        except Exception as e:
            if "-12" in str(e):
                logging.warning(
                    f"⚠️ Error in restore_position: {e} (MPV may not be ready)"
                )
            else:
                logging.error(f"❌ Error in restore_position: {e}", exc_info=True)

    def restart_video(self):
        try:
            self.player.seek(0, "absolute")
            self.saved_position = 0
            self.position_restore_attempted = True
            if self.player.pause:
                self.player.pause = False
        except Exception as e:
            logging.error(f"Error restarting video: {e}", exc_info=True)

    def set_position(self, position_ms):
        if not self.slider_updating:
            try:
                self.player.seek(position_ms / 1000.0, "absolute", "exact")
            except Exception as e:
                logging.error(f"Error seeking: {e}", exc_info=True)

    def _on_slider_pressed(self):
        self.is_seeking_slider = True

    def _on_slider_released(self):
        self.is_seeking_slider = False
        # Ensure final position is applied
        self.set_position(self.progress_slider.value())

    def play_pause(self):
        """Toggle play/pause."""
        if not self.current_file:
            return

        try:
            self.player.pause = not self.player.pause

            if (
                not self.player.pause
                and self.saved_position > 0
                and not self.position_restore_attempted
            ):
                QTimer.singleShot(200, self.restore_position)

            if self.taskbar_progress:
                if self.player.pause:
                    self.taskbar_progress.set_paused()
                else:
                    self.taskbar_progress.set_normal()

            if not self.player.pause:
                if self.translation_popup:
                    self.translation_popup.hide()
                self._paused_by_hover = False

            # Show OSD notification for pause/play state
            if self.osd_manager:
                self.osd_manager.show_pause_state(self.player.pause)

        except Exception as e:
            logging.error(f"Error toggling playback: {e}", exc_info=True)

    def stop(self):
        try:
            if self.player:
                self.player.stop()
        except Exception as e:
            logging.error(f"Error stopping playback: {e}", exc_info=True)

    def position_updated(self, position_ms):
        if self.is_seeking_slider:
            return

        self.slider_updating = True
        self.progress_slider.setValue(position_ms)
        self.slider_updating = False

        current_sec = position_ms // 1000

        try:
            total_sec = int(self.player.duration or 0)
        except:
            total_sec = 0

        self.time_label.setText(
            tr(
                "player.time_format",
                current=self.format_time(current_sec),
                total=self.format_time(total_sec),
            )
        )

        if self.current_file:
            self.position_changed.emit(current_sec, self.current_file)

        if self.taskbar_progress and total_sec > 0:
            try:
                is_playing = not self.player.pause
            except:
                is_playing = False

            self.taskbar_progress.update_for_playback(
                is_playing=is_playing, current=current_sec, total=total_sec
            )

    def state_changed(self, is_paused):
        if is_paused:
            self.play_btn.setIcon(self.icons["play"])
            self.play_btn.setToolTip(tr("player.play"))
        else:
            self.play_btn.setIcon(self.icons["pause"])
            self.play_btn.setToolTip(tr("player.pause"))
        self.pause_changed.emit(is_paused)

    def change_volume(self, value):
        try:
            if self.player:
                self.player.volume = value
                # Show OSD notification for volume change
                if self.osd_manager:
                    self.osd_manager.show_volume(value)
        except Exception as e:
            logging.error(f"Error changing volume: {e}", exc_info=True)

    def change_speed(self, value):
        speed = value / 10.0
        try:
            if self.player:
                self.player.speed = speed
                self.speed_label.setText(tr("player.speed", speed=f"{speed:.1f}"))
                # Show OSD notification for speed change (but not during state restoration)
                if self.osd_manager and not self._restoring_state:
                    self.osd_manager.show_speed(speed)
        except Exception as e:
            logging.error(f"Error changing speed: {e}", exc_info=True)

    def get_current_speed(self) -> float:
        """Returns the current playback speed as a float (e.g. 1.0, 1.5, 2.0)."""
        return self.speed_slider.value() / 10.0

    def set_speed(self, speed: float):
        """Sets playback speed from a float value, updating slider and MPV."""
        try:
            val = int(round(speed * 10.0))
            val = max(5, min(30, val))
            self._restoring_state = True
            self.speed_slider.setValue(val)
            self._restoring_state = False
            if self.player:
                self.player.speed = val / 10.0
            self.speed_label.setText(tr("player.speed", speed=f"{val/10.0:.1f}"))
        except Exception as e:
            logging.error(f"Error setting speed: {e}", exc_info=True)
            self._restoring_state = False

    @staticmethod
    def format_time(seconds):
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def update_texts(self):
        speed = self.speed_slider.value() / 10.0
        self.speed_label.setText(tr("player.speed", speed=f"{speed:.1f}"))
        # Update tooltips and buttons
        self.volume_btn.update_texts()
        self.subtitle_btn.update_texts()
        if hasattr(self, "sub_settings_btn"):
            self.sub_settings_btn.setToolTip(tr("player.tooltip_subtitle_settings"))
        if hasattr(self, "vol_settings_btn"):
            self.vol_settings_btn.setToolTip(tr("player.tooltip_volume_settings"))
        self.play_btn.setToolTip(
            tr("player.play")
            if self.player and self.player.pause
            else tr("player.pause")
        )
        # Update player control button tooltips
        self.prev_video_btn.setToolTip(tr("player.tooltip_prev_video"))
        self.next_video_btn.setToolTip(tr("player.tooltip_next_video"))
        self.pip_btn.setToolTip(tr("player.tooltip_pip"))
        self.fullscreen_btn.setToolTip(tr("player.tooltip_fullscreen"))
        self.speed_slider.setToolTip(tr("player.tooltip_speed"))
        if hasattr(self, "subtitle_overlay") and self.subtitle_overlay:
            self.subtitle_overlay.update_texts()

    def moveEvent(self, event):
        """Keep gallery overlay in sync when window moves."""
        super().moveEvent(event)
        if hasattr(self, "marker_gallery") and self.marker_gallery:
            self._update_gallery_geometry()
            QTimer.singleShot(0, self._update_gallery_geometry)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "marker_gallery") and self.marker_gallery:
            self._update_gallery_geometry()
            QTimer.singleShot(0, self._update_gallery_geometry)

    def _update_gallery_geometry(self):
        if not self.marker_gallery:
            return

        # Get coordinates of the WHOLE player widget
        global_top_left = self.mapToGlobal(QPoint(0, 0))

        w = self.width()
        h = self.marker_gallery.height()
        total_h = self.height()

        # Position at the bottom of the player window with 10px margin
        self.marker_gallery.setGeometry(
            global_top_left.x(),
            global_top_left.y() + total_h - h - 10,  # 10px margin from bottom
            w,
            h,
        )
        self.marker_gallery.raise_()

    def _update_subtitle_visibility(self):
        if not self.player:
            logging.info("📝 _update_subtitle_visibility: player not initialized")
            return
        try:
            is_interactive = self.config.get_interactive_subtitles() if self.config else False
            is_enabled = self.subtitle_btn.subtitles_enabled
            is_secondary_enabled = self.subtitle_btn.popup.secondary_enabled_cb.isChecked()
            is_secondary_effective = is_secondary_enabled and is_enabled
            
            logging.info(
                f"📝 _update_subtitle_visibility: subtitles_enabled (button state)={is_enabled}, "
                f"is_interactive={is_interactive}, is_secondary_enabled={is_secondary_enabled}, "
                f"is_secondary_effective={is_secondary_effective}"
            )
            
            if is_enabled and is_interactive:
                self.player.sub_visibility = "no"
                sub_text = self.player.sub_text or ""
                self.subtitle_overlay.set_text(sub_text)
                logging.info(f"📝 _update_subtitle_visibility: Interactive subs ON (hiding native, overlay len={len(sub_text)})")
            else:
                self.player.sub_visibility = "yes" if is_enabled else "no"
                self.subtitle_overlay.set_text("")
                logging.info(f"📝 _update_subtitle_visibility: Native subs visibility set to '{self.player.sub_visibility}' (is_enabled={is_enabled})")
                if not is_secondary_effective or not is_interactive:
                    self.subtitle_overlay.hide()
                    logging.info("📝 _update_subtitle_visibility: Hiding subtitle overlay (secondary not effective or not interactive)")
                    if self.translation_popup:
                        self.translation_popup.hide()

            # Handle secondary subtitles
            try:
                if is_secondary_effective and is_interactive:
                    self.player['secondary-sub-visibility'] = "no"
                    sub2_text = self.player['secondary-sub-text'] or ""
                    self.subtitle_overlay.set_secondary_text(sub2_text)
                    logging.info(f"📝 _update_subtitle_visibility: Interactive secondary subs ON (overlay len={len(sub2_text)})")
                else:
                    self.player['secondary-sub-visibility'] = "yes" if is_secondary_effective else "no"
                    self.subtitle_overlay.set_secondary_text("")
                    logging.info(f"📝 _update_subtitle_visibility: Native secondary subs visibility set to '{self.player['secondary-sub-visibility']}'")
            except Exception as e:
                logging.debug(f"Could not set secondary-sub-visibility or get secondary-sub-text: {e}")
                
        except Exception as e:
            logging.error(f"Error updating subtitle visibility: {e}")

    def toggle_interactive_subtitles(self, enabled):
        """Toggles interactive subtitle mode."""
        if self.config:
            self.config.set_interactive_subtitles(enabled)
            
        self._update_subtitle_visibility()

    def _on_secondary_sub_text_changed(self, text):
        is_interactive = self.config.get_interactive_subtitles() if self.config else False
        is_enabled = self.subtitle_btn.subtitles_enabled
        is_secondary_enabled = self.subtitle_btn.popup.secondary_enabled_cb.isChecked()
        is_secondary_effective = is_secondary_enabled and is_enabled
        if is_interactive and is_secondary_effective:
            self.subtitle_overlay.set_secondary_text(text or "")
        else:
            self.subtitle_overlay.set_secondary_text("")

    def _on_secondary_hover_only_changed(self, enabled):
        """Handle toggling of showing secondary subtitles only on hover."""
        logging.info(f"📝 _on_secondary_hover_only_changed({enabled}) called")
        if self.config:
            self.config.set_secondary_subtitle_hover_only(enabled)
        if hasattr(self, "subtitle_overlay") and self.subtitle_overlay:
            self.subtitle_overlay.set_secondary_hover_only(enabled)

    def _on_secondary_subtitle_toggled(self, enabled):
        """Enable/disable secondary subtitle."""
        logging.info(f"📝 _on_secondary_subtitle_toggled({enabled}) called")
        if not self.player:
            return

        popup = self.subtitle_btn.popup
        if enabled:
            # Turn on — use previously selected track or first if none selected
            index_to_use = popup.secondary_selected_index if popup.secondary_selected_index >= 0 else 0
            popup.setSecondaryIndex(index_to_use)
            track_id = popup.secondaryItemData(index_to_use)
            self._on_secondary_subtitle_changed(track_id)
        else:
            # Turn off
            try:
                self.player["secondary-sid"] = "no"
                logging.info("🔇 Secondary subtitles disabled in MPV")
            except Exception as e:
                logging.error(f"Error disabling secondary-sid in MPV: {e}")
                
            if self.current_file and self.db:
                track_id = popup.secondaryItemData(popup.secondary_selected_index) if popup.secondary_selected_index >= 0 else None
                self.db.save_secondary_subtitle(self.current_file, track_id, False)

        self._update_subtitle_visibility()

    def _on_secondary_subtitle_changed(self, track_id):
        """Switch secondary subtitle track on selection by track ID."""
        if not self.player:
            return
        if not self.current_file:
            return

        popup = self.subtitle_btn.popup

        # If "None" or similar is selected, track_id is None
        if track_id is None:
            try:
                self.player["secondary-sid"] = "no"
                logging.info("🔇 Secondary subtitles disabled (no track)")
            except Exception as e:
                logging.error(f"Error setting secondary-sid to 'no': {e}")
            if self.current_file and self.db:
                self.db.save_secondary_subtitle(self.current_file, None, False)
            self._update_subtitle_visibility()
            return

        if not self.db:
            return

        try:
            track = self.db.get_track_info("subtitle_tracks", track_id)
            if not track:
                return

            track_type = track["track_type"]
            stream_index = track["stream_index"]
            subtitle_file_path = track["subtitle_file_path"]

            logging.info(f"🔄 Switching secondary subtitle track: {track_type}, stream={stream_index}")

            if track_type == "embedded":
                try:
                    mpv_sid = self._map_ffprobe_to_mpv_sid(stream_index)
                    if mpv_sid is not None:
                        self.player["secondary-sid"] = mpv_sid
                        logging.info(f" Switched secondary-sid to embedded {mpv_sid}")
                    else:
                        self.player["secondary-sid"] = stream_index
                        logging.warning(f" Switched secondary-sid to raw {stream_index}")
                except Exception as e:
                    logging.error(f"Error setting secondary-sid: {e}")
            else:
                # External subtitle
                if subtitle_file_path and Path(subtitle_file_path).exists():
                    try:
                        mpv_sid = self._get_mpv_subtitle_track_id(track)
                        if mpv_sid is not None:
                            self.player["secondary-sid"] = mpv_sid
                            logging.info(f" Switched secondary-sid to external track MPV ID {mpv_sid}")
                        else:
                            logging.error(f"Could not load/find external track for secondary subtitle: {subtitle_file_path}")
                    except Exception as e:
                        logging.error(f"Error loading external secondary subtitle: {e}")
                else:
                    logging.error(f"❌ Secondary subtitle file not found: {subtitle_file_path}")

            # Save selection to DB
            is_enabled = self.subtitle_btn.popup.secondary_enabled_cb.isChecked()
            self.db.save_secondary_subtitle(self.current_file, track_id, is_enabled)

        except Exception as e:
            logging.error(f"Error changing secondary subtitle: {e}", exc_info=True)

        self._update_subtitle_visibility()

    def _get_mpv_subtitle_track_id(self, track):
        """Get MPV subtitle track ID for a given subtitle track."""
        logging.info(f"🔍 _get_mpv_subtitle_track_id() called with track: {track}")
        try:
            track_type = track["track_type"]
            if track_type == "embedded":
                stream_index = track["stream_index"]
                return self._map_ffprobe_to_mpv_sid(stream_index)
            elif track_type == "external":
                subtitle_file_path = track["subtitle_file_path"]
                if not subtitle_file_path:
                    return None
                if not Path(subtitle_file_path).exists():
                    return None

                # Check if already loaded
                track_list = self.player.track_list
                for t in track_list:
                    if t.get("type") == "sub":
                        ext_filename = t.get("external-filename")
                        if ext_filename == subtitle_file_path:
                            return t["id"]

                # Load external subtitle
                try:
                    self.player.command("sub-add", subtitle_file_path, "auto")
                except Exception as e:
                    logging.error(f"Error executing sub-add command: {e}")
                    return None

                # Find the newly added track
                track_list = self.player.track_list
                for t in track_list:
                    if t.get("type") == "sub":
                        ext_filename = t.get("external-filename")
                        if ext_filename == subtitle_file_path:
                            return t["id"]
        except Exception as e:
            logging.error(f"Error getting MPV subtitle track ID: {e}")
        return None

    def _restore_secondary_subtitle(self, filepath):
        """Restore secondary subtitle track when loading video."""
        logging.info(f"📝 ========== RESTORING SECONDARY SUBTITLE ==========")
        logging.info(f"📝 File: {filepath}")

        if not self.db or not self.player:
            return

        try:
            sec_track_id, sec_enabled = self.db.load_secondary_subtitle(filepath)
            
            logging.info(f"📝 Secondary subtitle ID from DB: {sec_track_id}")
            logging.info(f"📝 Secondary subtitle enabled from DB: {sec_enabled}")

            self.subtitle_btn.popup.setSecondaryEnabled(sec_enabled)

            popup = self.subtitle_btn.popup
            found_index = -1
            if sec_track_id is not None:
                for i in range(popup.secondary_list_widget.count()):
                    if popup.secondaryItemData(i) == sec_track_id:
                        found_index = i
                        popup.setSecondaryIndex(i)
                        break

            if sec_enabled and sec_track_id is not None:
                track = self.db.get_track_info("subtitle_tracks", sec_track_id)
                if track:
                    track_type = track["track_type"]
                    stream_index = track["stream_index"]
                    subtitle_file_path = track["subtitle_file_path"]

                    if track_type == "embedded":
                        mpv_sid = self._map_ffprobe_to_mpv_sid(stream_index)
                        if mpv_sid is not None:
                            self.player["secondary-sid"] = mpv_sid
                        else:
                            self.player["secondary-sid"] = stream_index
                    elif track_type == "external":
                        mpv_sid = self._get_mpv_subtitle_track_id(track)
                        if mpv_sid is not None:
                            self.player["secondary-sid"] = mpv_sid
            else:
                try:
                    self.player["secondary-sid"] = "no"
                except Exception as e:
                    logging.debug(f"Could not set secondary-sid to 'no': {e}")

            logging.info(f"📝 ========== SECONDARY SUBTITLE RESTORE COMPLETE ==========")
        except Exception as e:
            logging.error(f"Error restoring secondary subtitle: {e}", exc_info=True)

        self._update_subtitle_visibility()

    def _on_subtitle_word_hovered(self, word, global_pos):
        if not word or not self.player:
            return

        # Pause playback if playing
        if not self.player.pause:
            self._paused_by_hover = True
            self.player.pause = True
            if self.taskbar_progress:
                self.taskbar_progress.set_paused()
            if self.osd_manager:
                self.osd_manager.show_pause_state(True)

        # Show translation popup
        if self.translation_popup:
            if self.config:
                target_lang = self.config.get_translation_target_lang()
            else:
                from translator import tr as global_translator
                target_lang = global_translator.current_lang
            self.translation_popup.show_translation(word, target_lang, global_pos)

        if hasattr(self, "hover_check_timer"):
            self.hover_check_timer.start(100)

    def _on_subtitle_selection_selected(self, text, global_pos):
        if not text or not self.player:
            return

        # Check if this was a persistent translation request (e.g. via hotkey)
        is_persistent = getattr(self, "_persistent_translation", False)
        self._persistent_translation = False

        # Pause playback if playing
        if not self.player.pause:
            if not is_persistent:
                self._paused_by_hover = True
            else:
                self._paused_by_hover = False
            self.player.pause = True
            if self.taskbar_progress:
                self.taskbar_progress.set_paused()
            if self.osd_manager:
                self.osd_manager.show_pause_state(True)
        else:
            if is_persistent:
                self._paused_by_hover = False

        # Show translation popup
        if self.translation_popup:
            if self.config:
                target_lang = self.config.get_translation_target_lang()
            else:
                from translator import tr as global_translator
                target_lang = global_translator.current_lang
            self.translation_popup.show_translation(text, target_lang, global_pos)

        # Only start hover check timer if this is NOT a persistent translation
        if not is_persistent and hasattr(self, "hover_check_timer"):
            self.hover_check_timer.start(100)

    def _on_subtitle_hover_cleared(self):
        from PyQt6.QtGui import QCursor
        
        # Hide the translation popup if the mouse is not over the popup
        over_popup = False
        if hasattr(self, "translation_popup") and self.translation_popup and self.translation_popup.isVisible():
            over_popup = self.translation_popup.rect().contains(self.translation_popup.mapFromGlobal(QCursor.pos()))
            
        if not over_popup:
            if self.translation_popup:
                # Start a 300ms grace period instead of hiding immediately.
                # This gives the user time to move the cursor across the 4px gap.
                self.translation_popup.hide_timer.start(300)

    def _on_subtitle_area_entered(self):
        if not self.player:
            return
        # Pause playback immediately
        if not self.player.pause:
            self._paused_by_hover = True
            self.player.pause = True
            if self.taskbar_progress:
                self.taskbar_progress.set_paused()
            if self.osd_manager:
                self.osd_manager.show_pause_state(True)
        # Start the hover check timer to track when the mouse leaves the area
        if hasattr(self, "hover_check_timer"):
            self.hover_check_timer.start(100)

    def _on_hover_check_timeout(self):
        if not self.player:
            self.hover_check_timer.stop()
            return
            
        # If player is not paused, we shouldn't do anything or check
        if not self.player.pause:
            self.hover_check_timer.stop()
            self._paused_by_hover = False
            return
            
        from PyQt6.QtGui import QCursor
        
        # Determine if mouse is over subtitle overlay or translation popup
        over_overlay = False
        if hasattr(self, "subtitle_overlay") and self.subtitle_overlay and self.subtitle_overlay.isVisible():
            over_overlay = self.subtitle_overlay.rect().contains(self.subtitle_overlay.mapFromGlobal(QCursor.pos()))
            
        over_popup = False
        if hasattr(self, "translation_popup") and self.translation_popup and self.translation_popup.isVisible():
            over_popup = self.translation_popup.rect().contains(self.translation_popup.mapFromGlobal(QCursor.pos()))
            
        if not over_overlay and not over_popup:
            # Check if we are in the grace period
            if (hasattr(self, "translation_popup") and self.translation_popup 
                    and self.translation_popup.hide_timer.isActive()):
                # Still in grace period, do nothing (keep waiting)
                return
                
            self.hover_check_timer.stop()
            if self.translation_popup:
                self.translation_popup.hide()
            self._resume_playback_if_paused_by_hover()

    def _resume_playback_if_paused_by_hover(self):
        if getattr(self, "_paused_by_hover", False):
            self._paused_by_hover = False
            if self.player:
                self.player.pause = False
                if self.taskbar_progress:
                    self.taskbar_progress.set_normal()
                if self.osd_manager:
                    self.osd_manager.show_pause_state(False)

    def _on_sub_text_changed(self, text):
        is_interactive = self.config.get_interactive_subtitles() if self.config else False
        is_enabled = self.subtitle_btn.subtitles_enabled
        if is_interactive and is_enabled:
            if self.translation_popup:
                self.translation_popup.hide()
            self.subtitle_overlay.set_text(text)
            if not text:
                self._resume_playback_if_paused_by_hover()

    def translate_current_subtitle(self):
        """Translate the current full subtitle phrase."""
        if not self.player:
            return
        
        self._persistent_translation = True
        
        # Pause playback if playing
        if not self.player.pause:
            self._paused_by_hover = False
            self.player.pause = True
            if self.taskbar_progress:
                self.taskbar_progress.set_paused()
            if self.osd_manager:
                self.osd_manager.show_pause_state(True)
        else:
            self._paused_by_hover = False

        if hasattr(self, "subtitle_overlay") and self.subtitle_overlay:
            self.subtitle_overlay.trigger_translation()
