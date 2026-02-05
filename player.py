
import sys
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QSizePolicy, QStylePainter, QStyleOptionSlider, QStyle, QToolTip, QMenu
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QIcon, QColor, QPalette, QPainter, QPen, QBrush

from mpv_handler import setup_mpv_dll, MPVVideoWidget
from translator import tr
from subtitle_popup import SubtitleButton
from volume_popup import VolumeButton
from preview_popup import PreviewPopup
from marker_dialog import MarkerDialog
from marker_gallery import MarkerGalleryWidget
from thumbnail_provider import ThumbnailProvider

ROOT_DIR = Path(__file__).parent
RESOURCES_DIR = ROOT_DIR / "resources"

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
            # print("DEBUG: ClickableSlider paintEvent start") # DEBUG
            super().paintEvent(event)
            
            # Ensure duration is a valid number
            duration = self.duration if self.duration is not None else 0
            
            if not self.markers or duration <= 0:
                # print("DEBUG: No markers or zero duration") # DEBUG
                return

            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            w = self.width()
            h = self.height()
            
            # Draw markers
            for marker in self.markers:
                pos_sec = marker.get('position_seconds', 0)
                m_color = marker.get('color', '#FFD700')
                if pos_sec > self.duration: continue
                
                # Ratio 0..1
                ratio = pos_sec / self.duration
                x = int(ratio * w)
                
                # Draw tick mark with marker color
                painter.setPen(QPen(QColor(m_color), 2))
                tick_h = 8
                y = (h - tick_h) // 2
                painter.drawLine(x, y, x, y + tick_h)
            
            painter.end()
            # print("DEBUG: ClickableSlider paintEvent end") # DEBUG
        except Exception as e:
            print(f"❌ ERROR in ClickableSlider.paintEvent: {e}")
            import traceback
            traceback.print_exc()

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
                if abs(m.get('position_seconds', 0) - click_sec) < tolerance_sec:
                    target_marker = m
                    break
            
            menu = QMenu(self)
            add_action = menu.addAction(tr('player.add_marker_title') or "Add Marker")
            
            edit_action = None
            delete_action = None
            
            if target_marker:
                menu.addSeparator()
                edit_action = menu.addAction(tr('player.edit_marker') or "Edit Marker")
                delete_action = menu.addAction(tr('player.delete_marker') or "Delete Marker")
                
            action = menu.exec(event.globalPos())
            if action == add_action:
                self.add_marker_requested.emit(click_sec)
            elif edit_action and action == edit_action:
                self.marker_edit_requested.emit(target_marker)
            elif delete_action and action == delete_action:
                self.marker_delete_requested.emit(target_marker.get('id'))
        except Exception as e:
            print(f"❌ Error in ClickableSlider.contextMenuEvent: {e}")
            import traceback
            traceback.print_exc()


class VideoPlayerWidget(QWidget):
    """MPV-based player with audio track support."""
    video_finished = pyqtSignal()
    position_changed = pyqtSignal(int, str)
    request_hide_main_window = pyqtSignal()
    request_show_main_window = pyqtSignal()
    pause_changed = pyqtSignal(bool)
    subtitle_style_changed = pyqtSignal(str, object)
    next_video_requested = pyqtSignal()
    prev_video_requested = pyqtSignal()
    markers_changed = pyqtSignal(str) # file_path
    toggle_fullscreen_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        print("DEBUG: VideoPlayerWidget init start") # DEBUG
        self.db = None
        self.current_file = None
        self.saved_position = 0
        self.position_restore_attempted = False
        self.slider_updating = False
        self.is_seeking_slider = False
        self.taskbar_progress = None
        self.is_loading = False
        self.auto_play_pending = False
        self.player = None
        self.sub_color = "#FFFFFF"
        self.sub_border_color = "#000000"
        self.sub_scale = 1.0
        self.sub_scale = 1.0
        self.markers = [] 
        
        # Marker Gallery & Thumbnailing
        self.thumb_provider = ThumbnailProvider(self)
        self.thumb_provider.finished.connect(self._on_marker_thumbnail_ready)
        self.marker_gallery = None # Created in setup_ui
        print("DEBUG: Calling setup_ui") # DEBUG
        self.setup_ui()
        print("DEBUG: Calling setup_mpv") # DEBUG
        self.setup_mpv()
        print("DEBUG: VideoPlayerWidget init done") # DEBUG

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
        container_layout.addWidget(self.video_widget, 1)

        # Marker Gallery Overlay (Horizontal) - Independent window to avoid Airspace issue
        self.marker_gallery = MarkerGalleryWidget(self)
        self.marker_gallery.hide()
        self.marker_gallery.seek_requested.connect(self._on_marker_gallery_seek)
        self.marker_gallery.edit_requested.connect(self.edit_marker)
        self.marker_gallery.delete_requested.connect(self.delete_marker)

        layout.addWidget(self.video_container, 1)

        control_panel = QWidget()
        control_panel.setObjectName("controlPanel")
        panel_layout = QHBoxLayout(control_panel)
        panel_layout.setContentsMargins(0, 5, 0, 0)

        self.icons = {}
        for name in ["play", "pause", "next", "prev"]:
            path = RESOURCES_DIR / "icons" / f"{name}.png"
            if path.exists():
                self.icons[name] = QIcon(str(path))
            else:
                 self.icons[name] = QIcon()

        # Previous Video Button
        self.prev_video_btn = QPushButton()
        self.prev_video_btn.setIcon(self.icons['prev'])
        self.prev_video_btn.setFixedSize(30, 30)
        self.prev_video_btn.setToolTip(tr('player.tooltip_prev_video'))
        self.prev_video_btn.clicked.connect(self.prev_video_requested.emit)
        self.prev_video_btn.setEnabled(False)
        panel_layout.addWidget(self.prev_video_btn)

        self.play_btn = QPushButton()
        self.play_btn.setIcon(self.icons['play'])
        self.play_btn.setObjectName("playBtn")
        self.play_btn.setFixedHeight(30)
        self.play_btn.clicked.connect(self.play_pause)
        self.play_btn.setEnabled(False)
        panel_layout.addWidget(self.play_btn)


        # Next Video Button
        self.next_video_btn = QPushButton()
        self.next_video_btn.setIcon(self.icons['next'])
        self.next_video_btn.setFixedSize(30, 30)
        self.next_video_btn.setToolTip(tr('player.tooltip_next_video'))
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
        panel_layout.addWidget(self.time_label)


        # Subtitle button: Left click - select, Right click - toggle
        self.subtitle_btn = SubtitleButton()
        self.subtitle_btn.subtitleToggled.connect(self.toggle_subtitles)
        self.subtitle_btn.subtitleChanged.connect(self.change_subtitle_track)
        self.subtitle_btn.popup.styleChanged.connect(self.change_subtitle_style)
        panel_layout.addWidget(self.subtitle_btn)



        self.volume_btn = VolumeButton()
        self.volume_btn.volumeChanged.connect(self.change_volume)
        self.volume_btn.audioChanged.connect(self.change_audio_track)
        panel_layout.addWidget(self.volume_btn)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(5, 30)
        self.speed_slider.setValue(10)
        self.speed_slider.valueChanged.connect(self.change_speed)
        panel_layout.addWidget(self.speed_slider)

        self.speed_label = QLabel(tr('player.speed', speed='1.0'))
        panel_layout.addWidget(self.speed_label)

        # Ensure buttons don't take focus to avoid breaking global hotkeys
        for btn in [self.prev_video_btn, self.play_btn, self.next_video_btn, 
                    self.subtitle_btn, self.volume_btn]:
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # Sliders should also not take focus if we want Space to always work for play/pause
        self.progress_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.speed_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout.addWidget(control_panel)

        self.video_widget.toggle_play_pause.connect(self.play_pause)

        # Preview Popup
        self.preview_popup = PreviewPopup(self.video_widget)
        self.progress_slider.hovered.connect(self._on_slider_hovered)
        self.progress_slider.hover_left.connect(self._on_slider_left)

    def _on_slider_hovered(self, value, global_pos):
        """Show preview popup on slider hover."""
        if not getattr(self, 'show_preview', True):
            return
            
        if not self.player or not self.current_file or not self.player.duration:
            return
            
        duration = self.player.duration
        if duration <= 0: return

        # Calculate time in seconds
        # slider value is in milliseconds (set by duration_changed)
        seconds = value / 1000.0
        
        # Check for nearby markers
        marker_text = ""
        for m in self.markers:
            m_sec = m['position_seconds']
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
        if not self.player: return
        try:
            is_muted = getattr(self.player, 'mute', False)
            self.player.mute = not is_muted
            # Update volume button UI if needed
            current_vol = self.player.volume
            self.volume_btn._update_icon(0 if self.player.mute else current_vol)
        except Exception as e:
            print(f"Error toggling mute: {e}")

    def adjust_volume(self, delta):
        """Adjust volume by delta percentage."""
        if not self.player: return
        try:
            current = self.player.volume or 0
            new_vol = max(0, min(100, current + delta))
            self.player.volume = new_vol
            # Update UI
            self.volume_btn.popup.slider.blockSignals(True)
            self.volume_btn.popup.slider.setValue(int(new_vol))
            self.volume_btn.popup.slider.blockSignals(False)
            self.volume_btn._update_icon(int(new_vol))
            if hasattr(self.volume_btn.popup, '_update_label'):
                self.volume_btn.popup._update_label(int(new_vol))
        except Exception as e:
            print(f"Error adjusting volume: {e}")

    def adjust_speed(self, delta):
        """Adjust playback speed by delta."""
        if not self.player: return
        try:
            # speed_slider range is 5 (0.5x) to 30 (3.0x)
            current_slider_val = self.speed_slider.value()
            # delta is e.g. 0.1, which corresponds to 1 unit on slider
            slider_delta = int(delta * 10)
            new_val = max(5, min(30, current_slider_val + slider_delta))
            self.speed_slider.setValue(new_val)
            # change_speed is already connected to valueChanged
        except Exception as e:
            print(f"Error adjusting speed: {e}")

    def seek_relative(self, seconds):
        """Seek relative to current position."""
        if not self.player: return
        try:
            self.player.seek(seconds, 'relative')
        except Exception as e:
            print(f"Error seeking: {e}")

    def frame_step(self):
        """Step forward one frame."""
        self.video_widget.frame_step()

    def frame_back_step(self):
        """Step backward one frame."""
        self.video_widget.frame_back_step()

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
                vo='gpu',
                hwdec='auto-safe',
                sid='no', # Disable subtitles by default
                keep_open=True,
                idle=True,
                osc=False,
                osd_level=0,
                osd_bar=False,
                osd_on_seek=False,
                input_default_bindings=False,
                input_vo_keyboard=False,
                cursor_autohide='no',
                ad_lavc_threads=2,
                ad_lavc_downmix='no',
                audio_fallback_to_null='yes',  # Do not stop on audio error
                demuxer_lavf_o='fflags=+genpts+igndts',  # Ignore timing problems
                log_handler=print,
                loglevel='warn'
            )
            
            # Apply initial subtitle styles
            self._apply_subtitle_styles()

            @self.player.property_observer('time-pos')
            def time_observer(_name, value):
                if value is not None:
                    self.position_updated(int(value * 1000))

            @self.player.property_observer('duration')
            def duration_observer(_name, value):
                if value is not None:
                    self.duration_changed(int(value * 1000))

            @self.player.property_observer('pause')
            def pause_observer(_name, value):
                self.state_changed(value)

            @self.player.property_observer('eof-reached')
            def eof_observer(_name, value):
                if value:
                    self.video_finished.emit()

            @self.player.property_observer('playback-restart')
            def playback_restart_observer(_name, value):
                if value and self.is_loading:
                    self.is_loading = False
                    if self.auto_play_pending:
                        QTimer.singleShot(50, self._ensure_playing)
                        self.auto_play_pending = False

            self.video_widget.set_player(self.player)
            print("MPV initialized successfully")
            print("libmpv version:", self.player.mpv_version)

        except Exception as e:
            print(f"Error initializing MPV: {e}")
            # Do not raise here to allow app to start even without libmpv
            self.player = None

    def _ensure_playing(self):
        """Ensure video plays after loading."""
        try:
            if self.player and self.player.pause:
                self.player.pause = False
        except Exception as e:
            print(f"Error ensuring playback: {e}")

    def set_ffmpeg_path(self, path):
        """Set FFmpeg path for preview generation."""
        if hasattr(self, 'preview_popup'):
            self.preview_popup.ffmpeg_path = path
        if hasattr(self, 'thumb_provider'):
            self.thumb_provider.ffmpeg_path = path

    def load_video(self, file_path, saved_position=0, volume=100, auto_play=True):
        """
        Load video
        file_path: path to file
        saved_position: saved position in seconds
        volume: saved volume in % (default 100)
        auto_play: automatically start playback
        """
        if not Path(file_path).exists():
            return False

        if not self.player:
            # Try to re-initialize MPV if DLL was just downloaded or found
            if setup_mpv_dll():
                print("VideoPlayerWidget: Attempting to initialize MPV (DLL found)...")
                self.setup_mpv()
            
            if not self.player:
                print("VideoPlayerWidget: Cannot load video, player not initialized")
                return False

        self.current_file = file_path
        self.saved_position = saved_position
        self.saved_position = saved_position
        self.position_restore_attempted = False
        self.is_loading = True
        self.auto_play_pending = auto_play
        
        # Update preview popup video path
        if hasattr(self, 'preview_popup'):
            self.preview_popup.set_video(str(file_path))

        self.video_widget.reset_zoom_pan()

        try:
            # Set volume BEFORE loading video
            if volume is None:
                volume = 100
            
            try:
                self.player.volume = volume
            except Exception as e:
                print(f"Error setting volume: {e}")

            # Update volume UI
            if hasattr(self, 'volume_btn'):
                self.volume_btn.popup.slider.blockSignals(True)
                self.volume_btn.popup.slider.setValue(int(volume))
                self.volume_btn.popup.slider.blockSignals(False)
                self.volume_btn._update_icon(int(volume))
                if hasattr(self.volume_btn.popup, '_update_label'):
                    self.volume_btn.popup._update_label(int(volume))

            self.player.sid = 'no'
            self.player.loadfile(file_path)
            self._apply_subtitle_styles()
            self.play_btn.setEnabled(True)
            self.progress_slider.setEnabled(True)
            self.prev_video_btn.setEnabled(True)
            self.next_video_btn.setEnabled(True)

            # ADDED: Load audio tracks
            QTimer.singleShot(200, lambda: self.load_audio_tracks(file_path))
            
            # Load tracks info from DB and restore state
            QTimer.singleShot(100, lambda: self.load_subtitle_tracks(file_path))
            QTimer.singleShot(200, lambda: self.restore_subtitle_track(file_path))
            
            # Load markers
            self.load_markers(file_path)

            if auto_play:
                QTimer.singleShot(100, self._start_playback)
            else:
                QTimer.singleShot(100, self._load_paused)

            return True

        except Exception as e:
            print(f"Error loading video: {e}")
            self.is_loading = False
            self.auto_play_pending = False
            return False

    def _load_paused(self):
        """Load video in paused mode."""
        if not self.player: return
        try:
            self.player.pause = True
            if self.saved_position > 0 and not self.position_restore_attempted:
                QTimer.singleShot(150, self.restore_position)
        except Exception as e:
            print(f"Error loading paused: {e}")

    def _start_playback(self):
        """Start playback after loading."""
        if not self.player: return
        try:
            if self.player.pause:
                self.player.pause = False
            if self.saved_position > 0 and not self.position_restore_attempted:
                QTimer.singleShot(150, self.restore_position)
        except Exception as e:
            print(f"Error starting playback: {e}")

    # ADDED: Methods for audio tracks
    def load_audio_tracks(self, filepath):
        """Load list of audio tracks from DB."""
        self.volume_btn.popup.clearAudio()

        if not self.db:
            return

        try:
            tracks, selected_audio_id = self.db.load_audio_tracks(filepath)

            if not tracks:
                self.volume_btn.popup.addAudioItem(tr('player.no_tracks'), None)
                return

            selected_index = 0

            for idx, track in enumerate(tracks):
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
                    label = f"{stream_index}"
                    if language:
                        label += f" [{language}]"
                    if title:
                        label += f" - {title}"
                    if codec:
                        label += f" ({codec})"
                    if channels:
                        label += f" {channels}ch"
                else:  # external
                    label = f"{audio_file_name or tr('player.external_audio')}"
                    if language:
                        label += f" [{language}]"

                if is_default:
                    label += f" [{tr('player.default')}]"

                self.volume_btn.popup.addAudioItem(label, track_id)

                if track_id == selected_audio_id:
                    selected_index = idx

            if tracks:
                self.volume_btn.popup.setAudioIndex(selected_index)

            # ADDED: Restore selected track
            QTimer.singleShot(300, lambda: self.restore_audio_track(filepath))

        except Exception as e:
            print(f"Error loading audio tracks: {e}")

    def change_audio_track(self, index):
        """Switch audio track on selection."""
        if not self.player: return
        if index < 0 or not self.current_file:
            return

        track_id = self.volume_btn.popup.audioItemData(index)
        if track_id is None:
            return

        if not self.db:
            return

        try:
            track = self.db.get_track_info('audio_tracks', track_id)
        except Exception as e:
            print(f"❌ DB error: {e}")
            return

        if not track:
            print("❌ Track not found")
            return

        track_type = track['track_type']
        stream_index = track['stream_index']
        audio_file_path = track['audio_file_path']

        try:
            print(f"🔄 Switching: {track_type}, stream={stream_index}")
            
            was_playing = not self.player.pause
            self.player.pause = True

            if track_type == 'embedded':
                # FIXED: MPV uses 1-based indexing
                # But stream_index is already correct from DB
                aid = int(stream_index) if stream_index is not None else 1
                
                # KEY FIX: Reset external tracks first
                try:
                    current_tracks = self.player.track_list
                    for t in current_tracks:
                        if t.get('type') == 'audio' and t.get('external', False):
                            self.player.command('audio-remove', t['id'])
                except:
                    pass
                
                # Now switch to embedded
                self.player.aid = aid
                print(f"✅ Embedded aid={aid}")

            elif track_type == 'external' and audio_file_path:
                if Path(audio_file_path).exists():
                    # Remove old external tracks
                    try:
                        current_tracks = self.player.track_list
                        for t in current_tracks:
                            if t.get('type') == 'audio' and t.get('external', False):
                                self.player.command('audio-remove', t['id'])
                    except:
                        pass
                    
                    # Add and select new one
                    self.player.command('audio-add', audio_file_path, 'select')
                    print(f"✅ External: {audio_file_path}")
                else:
                    print(f"❌ File not found: {audio_file_path}")

            # Resume playback
            QTimer.singleShot(200, lambda: setattr(self.player, 'pause', not was_playing))

            # Save to DB
            self.db.save_selected_audio(self.current_file, track_id)

        except Exception as e:
            print(f"❌ Switch error: {e}")
            import traceback
            traceback.print_exc()
            QTimer.singleShot(100, lambda: setattr(self.player, 'pause', False))


    def restore_audio_track(self, filepath):
        """Restore saved audio track when loading video."""
        if not self.db or not self.player:
            return

        try:
            tracks, selected_audio_id = self.db.load_audio_tracks(filepath)
            
            if not selected_audio_id:
                print("⏩ No saved audio track - selecting first available")
                if tracks:
                    track = tracks[0]
                    track_id = track['id']
                    self.db.save_selected_audio(filepath, track_id)
                    
                    track_type = track['track_type']
                    stream_index = track['stream_index']
                    audio_file_path = track['audio_file_path']
                    
                    print(f"💾 Saved first track: {track_type}, stream={stream_index}")
                    
                    if track_type == 'embedded':
                        aid = int(stream_index) if stream_index is not None else 1
                        self.player.aid = aid
                    elif track_type == 'external' and audio_file_path:
                        if Path(audio_file_path).exists():
                            self.player.command('audio-add', audio_file_path, 'select')
                    
                    for i in range(self.volume_btn.popup.audioCount()):
                        if self.volume_btn.popup.audioItemData(i) == track_id:
                            self.volume_btn.popup.setAudioIndex(i)
                            break
                return

            track = self.db.get_track_info('audio_tracks', selected_audio_id)
            if not track:
                return

            track_type = track['track_type']
            stream_index = track['stream_index']
            audio_file_path = track['audio_file_path']
            
            # Application logic (outside DB lock)
            print(f"🔄 Restoring saved: {track_type}, stream={stream_index}")

            if track_type == 'embedded':
                aid = int(stream_index) if stream_index is not None else 1
                self.player.aid = aid
                print(f"✅ Restored embedded aid={aid}")

            elif track_type == 'external' and audio_file_path:
                if Path(audio_file_path).exists():
                    self.player.command('audio-add', audio_file_path, 'select')
                    print(f"✅ Restored external: {audio_file_path}")
                else:
                    print(f"❌ External file not found: {audio_file_path}")

        except Exception as e:
            print(f"❌ Restore error: {e}")
            import traceback
            traceback.print_exc()

    # ===================== SUBTITLES =====================
    def load_subtitle_tracks(self, filepath):
        """Load list of subtitles from DB."""
        popup = self.subtitle_btn.popup
        popup.clear()

        if not self.db:
            return

        try:
            tracks, selected_subtitle_id, subtitles_enabled = self.db.load_subtitle_tracks(filepath)
            
            if not tracks:
                return

            selected_index = 0

            for idx, track in enumerate(tracks):
                track_id = track['id']
                track_type = track['track_type']
                stream_index = track['stream_index']
                subtitle_file_name = track['subtitle_file_name']
                language = track['language']
                title = track['title']
                codec = track['codec']
                is_default = track['is_default']
                is_forced = track['is_forced']

                if track_type == 'embedded':
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

                if track_id == selected_subtitle_id:
                    selected_index = idx

            # Sync button state with saved subtitles_enabled
            if selected_subtitle_id:
                popup.setCurrentIndex(selected_index)
            
            # Set button state based on subtitles_enabled from DB
            self.subtitle_btn.set_enabled_state(bool(subtitles_enabled))

            # Restore state is now handled in load_video for better timing control
            # QTimer.singleShot(400, lambda: self.restore_subtitle_track(filepath))

        except Exception as e:
            print(f"Error loading subtitle tracks: {e}")

    def toggle_subtitles(self, enabled):
        """Toggle subtitles on/off."""
        if not self.player:
            return
        
        popup = self.subtitle_btn.popup
        if enabled:
            # Turn on — select first track if exists
            if popup.count() > 0:
                popup.setCurrentIndex(0)
                self.change_subtitle_track(0)
        else:
            # Turn off
            try:
                self.player.sid = 'no'
                print("🔇 Subtitles disabled")
            except:
                pass
            self._save_selected_subtitle(None)
        
        # Save on/off state for current video
        if self.current_file and self.db:
            self.db.update_subtitle_enabled(self.current_file, enabled)

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
                hex_color = value.lstrip('#')
                self.player.sub_color = f"#FF{hex_color.upper()}"
                self.sub_color = value
                self.subtitle_style_changed.emit("sub-color", value)
                print(f"📝 Subtitle color: {value}")
            elif property_name == "sub-border-color":
                hex_color = value.lstrip('#')
                self.player.sub_border_color = f"#FF{hex_color.upper()}"
                self.sub_border_color = value
                self.subtitle_style_changed.emit("sub-border-color", value)
                print(f"📝 Subtitle border color: {value}")
            elif property_name == "sub-scale":
                # value is delta (+5 or -5)
                current_scale = getattr(self.player, 'sub_scale', 1.0)
                new_scale = max(0.5, min(3.0, current_scale + value / 100.0))
                self.player.sub_scale = new_scale
                self.sub_scale = new_scale
                self.subtitle_style_changed.emit("sub-scale", new_scale)
                print(f"📝 Subtitle scale: {new_scale:.2f}")
        except Exception as e:
            print(f"Error changing subtitle style: {e}")

    # ===================== MARKERS =====================
    def load_markers(self, file_path):
        """Load markers from DB and update slider."""
        if self.db:
            self.markers = self.db.get_markers(file_path)
            self.progress_slider.set_markers(self.markers, self.player.duration if self.player else 0)
            
            # Update Gallery
            if self.marker_gallery:
                self.marker_gallery.set_markers(self.markers)
                # Request thumbnails
                if self.markers:
                    for m in self.markers:
                        self.thumb_provider.get_thumbnail(file_path, m['position_seconds'], m['id'])

    def add_marker(self, timestamp=None):
        """Add marker at specified position or current position."""
        print("DEBUG: add_marker called") # DEBUG
        if not self.player or not self.current_file:
            print("DEBUG: No player or file") # DEBUG
            return
            
        # Get position
        if timestamp is not None:
            pos = timestamp
        else:
            try:
                pos = self.player.time_pos or 0
                print(f"DEBUG: Current pos: {pos}") # DEBUG
            except Exception as e:
                print(f"DEBUG: Error getting time_pos: {e}") # DEBUG
                pos = 0
            
        # Pause playback
        was_playing = not self.player.pause
        if was_playing:
            self.player.pause = True
            
        try:
            # Generate default label (e.g., "Marker 3")
            marker_count = len(self.markers) if hasattr(self, 'markers') else 0
            default_label = f"{tr('player.default_marker_label') or 'Marker'} {marker_count + 1}"
            
            # Show dialog - Pass empty label to keep field clear
            duration = self.progress_slider.maximum() / 1000.0
            print(f"DEBUG: Opening dialog... Default label fallback: {default_label}, duration: {duration}") # DEBUG
            dlg = MarkerDialog(self, pos, label="", max_duration=duration)
            if dlg.exec():
                label, color, new_pos = dlg.get_data()
                
                # Apply default if input is empty
                if not label:
                    label = default_label
                
                print(f"DEBUG: Dialog accepted, label: '{label}', color: '{color}', pos: {new_pos}") # DEBUG
                
                if label:
                    # Save to DB
                    if self.db:
                        print(f"DEBUG: Saving to DB: {self.current_file}, {new_pos}, {label}, {color}") # DEBUG
                        self.db.add_marker(self.current_file, new_pos, label, color)
                        # Reload to update UI
                        print("DEBUG: Reloading markers...") # DEBUG
                        self.load_markers(self.current_file)
                        self.markers_changed.emit(self.current_file)
                    else:
                        print("DEBUG: Error - self.db is None") # DEBUG
            else:
                print("DEBUG: Dialog rejected") # DEBUG
        except Exception as e:
            import traceback
            print(f"❌ CRASH in add_marker: {e}")
            traceback.print_exc()
        
        # Resume if needed
        if was_playing:
            self.player.pause = False

    def edit_marker(self, marker_data):
        """Edit an existing marker."""
        if not self.db or not self.current_file:
            return
            
        m_id = marker_data.get('id')
        pos = marker_data.get('position_seconds', 0)
        label = marker_data.get('label', "")
        color = marker_data.get('color', "#FFD700")
        
        # Pause playback
        was_playing = not self.player.pause
        if was_playing:
            self.player.pause = True
            
        try:
            duration = self.progress_slider.maximum() / 1000.0
            dlg = MarkerDialog(self, pos, label=label, color=color, max_duration=duration)
            dlg.setWindowTitle(tr('player.edit_marker_title') or "Edit Marker")
            if dlg.exec():
                new_label, new_color, new_pos = dlg.get_data()
                if new_label or new_pos != pos: # Allow saving even if label is empty but pos changed
                    self.db.update_marker(m_id, new_label, new_color, position=new_pos)
                    self.load_markers(self.current_file)
                    self.markers_changed.emit(self.current_file)
        except Exception as e:
            print(f"Error editing marker: {e}")
            
        if was_playing:
            self.player.pause = False

    def toggle_marker_gallery(self):
        """Toggle marker gallery visibility."""
        print(f"DEBUG: toggle_marker_gallery, visible={self.marker_gallery.isVisible() if self.marker_gallery else 'None'}")
        if not self.marker_gallery:
            return
        
        if self.marker_gallery.isVisible():
            self.marker_gallery.hide()
        else:
            self._update_gallery_geometry()
            self.marker_gallery.show()
            self.marker_gallery.raise_()
            # Ensure markers are up to date and have thumbnails
            if self.current_file and self.markers:
                for m in self.markers:
                    self.thumb_provider.get_thumbnail(self.current_file, m['position_seconds'], m['id'])

    def _on_marker_thumbnail_ready(self, request_id, pixmap):
        """Slot called when a marker thumbnail is generated."""
        print(f"DEBUG: VideoPlayerWidget._on_marker_thumbnail_ready: req_id={request_id}")
        if self.marker_gallery:
            # request_id is marker_{id} or ts_{timestamp}
            if request_id.startswith("marker_"):
                m_id = int(request_id.replace("marker_", ""))
                print(f"DEBUG: Updating gallery thumbnail for marker_id={m_id}")
                self.marker_gallery.update_thumbnail(m_id, pixmap)
            else:
                print(f"DEBUG: Unknown request_id format: {request_id}")

    def _on_marker_gallery_seek(self, seconds):
        """Seek to marker position and hide gallery."""
        if self.player:
            self.player.time_pos = seconds
            # self.marker_gallery.hide() # Optional: hide on seek? User didn't specify.
            
    def delete_marker(self, marker_id):
        """Delete marker with confirmation."""
        from PyQt6.QtWidgets import QMessageBox
        
        res = QMessageBox.question(
            self, 
            tr('player.delete_marker_title') or "Delete Marker",
            tr('player.delete_marker_confirm') or "Are you sure you want to delete this marker?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if res == QMessageBox.StandardButton.Yes:
            if self.db:
                self.db.delete_marker(marker_id)
                self.load_markers(self.current_file)
            self.markers_changed.emit(self.current_file)

    def set_subtitle_styles(self, color, border_color, scale):
        """Set initial subtitle styles."""
        self.sub_color = color
        self.sub_border_color = border_color
        self.sub_scale = scale
        
        # Also sync with popup
        if hasattr(self, 'subtitle_btn'):
            self.subtitle_btn.popup.text_color = color
            self.subtitle_btn.popup.outline_color = border_color
            self.subtitle_btn.popup._update_text_color_btn()
            self.subtitle_btn.popup._update_outline_color_btn()
            
        if self.player:
            self._apply_subtitle_styles()

    def _apply_subtitle_styles(self):
        """Apply stored subtitle styles to MPV player."""
        if not self.player:
            return
        
        try:
            # Color
            hex_color = self.sub_color.lstrip('#')
            self.player.sub_color = f"#FF{hex_color.upper()}"
            
            # Border
            hex_border = self.sub_border_color.lstrip('#')
            self.player.sub_border_color = f"#FF{hex_border.upper()}"
            
            # Scale
            self.player.sub_scale = self.sub_scale
        except Exception as e:
            print(f"Error applying subtitle styles: {e}")

    def change_subtitle_track(self, index):
        """Switch subtitles on selection."""
        if not self.player: return
        if index < 0: return

        popup = self.subtitle_btn.popup
        track_id = popup.itemData(index)

        # Update button state
        self.subtitle_btn.set_enabled_state(True)

        # If "Off" is selected
        if track_id is None:
            try:
                self.player.sid = 'no'
                print("🔇 Subtitles disabled")
            except:
                pass
            self._save_selected_subtitle(None)
            return

        if not self.db:
            return

        try:
            track = self.db.get_track_info('subtitle_tracks', track_id)
            if not track:
                return

            track_type = track['track_type']
            stream_index = track['stream_index']
            subtitle_file_path = track['subtitle_file_path']

            if track_type == 'embedded':
                # Use sid for embedded subtitles
                try:
                    self.player.sid = stream_index
                    print(f"📝 Switched to embedded subtitle track {stream_index}")
                except Exception as e:
                    print(f"Error setting subtitle track: {e}")
            else:
                # Use sub-add for external subtitles
                if subtitle_file_path and Path(subtitle_file_path).exists():
                    try:
                        self.player.command('sub-add', subtitle_file_path, 'select')
                        print(f"📝 Loaded external subtitle: {subtitle_file_path}")
                    except Exception as e:
                        print(f"Error loading external subtitle: {e}")
                else:
                    print(f"❌ Subtitle file not found: {subtitle_file_path}")

            self._save_selected_subtitle(track_id)

        except Exception as e:
            print(f"Error changing subtitle track: {e}")

    def _save_selected_subtitle(self, track_id):
        """Save selected subtitles to DB."""
        if not self.current_file or not self.db:
            return

        try:
            # If track_id is None, it means subtitles are turned off
            subtitles_enabled = 0 if track_id is None else 1
            self.db.save_selected_subtitle(self.current_file, track_id, subtitles_enabled)
        except Exception as e:
            print(f"Error saving selected subtitle: {e}")

    def restore_subtitle_track(self, filepath):
        """Restore saved subtitles when loading video."""
        if not self.db or not self.player:
            return

        try:
            tracks, selected_subtitle_id, subtitles_enabled = self.db.load_subtitle_tracks(filepath)
            
            if not subtitles_enabled:
                try:
                    self.player.sid = 'no'
                except:
                    pass
                return
            
            if not selected_subtitle_id:
                return

            track = self.db.get_track_info('subtitle_tracks', selected_subtitle_id)
            if not track:
                return

            track_type = track['track_type']
            stream_index = track['stream_index']
            subtitle_file_path = track['subtitle_file_path']

            if track_type == 'embedded':
                try:
                    self.player.sid = stream_index
                except Exception as e:
                    print(f"❌ Error restoring subtitle: {e}")
            else:
                if subtitle_file_path and Path(subtitle_file_path).exists():
                    self.player.command('sub-add', subtitle_file_path, 'select')
                else:
                    print(f"❌ External subtitle file not found: {subtitle_file_path}")

        except Exception as e:
            print(f"❌ Subtitle restore error: {e}")



    def duration_changed(self, duration_ms):
        self.progress_slider.setRange(0, duration_ms)
        # Refresh markers and ensure duration is synced to slider for context menu
        self.progress_slider.set_markers(self.markers if hasattr(self, 'markers') else [], duration_ms / 1000.0)

    def restore_position(self):
        if self.saved_position > 0 and not self.position_restore_attempted:
            try:
                self.player.seek(self.saved_position, 'absolute')
                self.position_restore_attempted = True
            except Exception as e:
                print(f"Error restoring position: {e}")

    def restart_video(self):
        try:
            self.player.seek(0, 'absolute')
            self.saved_position = 0
            self.position_restore_attempted = True
            if self.player.pause:
                self.player.pause = False
        except Exception as e:
            print(f"Error restarting video: {e}")

    def set_position(self, position_ms):
        if not self.slider_updating:
            try:
                self.player.seek(position_ms / 1000.0, 'absolute')
            except Exception as e:
                print(f"Error seeking: {e}")

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

            if not self.player.pause and self.saved_position > 0 and not self.position_restore_attempted:
                QTimer.singleShot(200, self.restore_position)

            if self.taskbar_progress:
                if self.player.pause:
                    self.taskbar_progress.set_paused()
                else:
                    self.taskbar_progress.set_normal()

        except Exception as e:
            print(f"Error toggling playback: {e}")

    def stop(self):
        try:
            if self.player:
                self.player.stop()
        except Exception as e:
            print(f"Error stopping playback: {e}")

    def unload_video(self):
        """Unload current video and show placeholder"""
        try:
            if self.player:
                self.player.command('stop')
        except:
            pass
            
        self.current_file = None
        self.play_btn.setEnabled(False)
        self.progress_slider.setEnabled(False)
        self.progress_slider.setValue(0)
        self.time_label.setText("00:00 / 00:00")
        self.frame_back_btn.setEnabled(False)
        self.frame_step_btn.setEnabled(False)
        self.screenshot_btn.setEnabled(False)
        self.video_widget.update() # Force repaint for placeholder

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

        self.time_label.setText(tr('player.time_format',
                                   current=self.format_time(current_sec),
                                   total=self.format_time(total_sec)))

        if self.current_file:
            self.position_changed.emit(current_sec, self.current_file)

        if self.taskbar_progress and total_sec > 0:
            try:
                is_playing = not self.player.pause
            except:
                is_playing = False

            self.taskbar_progress.update_for_playback(
                is_playing=is_playing,
                current=current_sec,
                total=total_sec
            )

    def state_changed(self, is_paused):
        if is_paused:
            self.play_btn.setIcon(self.icons['play'])
            self.play_btn.setToolTip(tr('player.play'))
        else:
            self.play_btn.setIcon(self.icons['pause'])
            self.play_btn.setToolTip(tr('player.pause'))
        self.pause_changed.emit(is_paused)

    def change_volume(self, value):
        try:
            if self.player:
                self.player.volume = value
        except Exception as e:
            print(f"Error changing volume: {e}")

    def change_speed(self, value):
        speed = value / 10.0
        try:
            if self.player:
                self.player.speed = speed
                self.speed_label.setText(tr('player.speed', speed=f'{speed:.1f}'))
        except Exception as e:
            print(f"Error changing speed: {e}")

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
        self.speed_label.setText(tr('player.speed', speed=f'{speed:.1f}'))
        # Update tooltips and buttons
        self.volume_btn.update_texts()
        self.subtitle_btn.update_texts()
        self.play_btn.setToolTip(tr('player.play') if self.player and self.player.pause else tr('player.pause'))

    def moveEvent(self, event):
        """Keep gallery overlay in sync when window moves."""
        super().moveEvent(event)
        if hasattr(self, 'marker_gallery') and self.marker_gallery:
            self._update_gallery_geometry()
            QTimer.singleShot(0, self._update_gallery_geometry)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'marker_gallery') and self.marker_gallery:
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
            global_top_left.y() + total_h - h - 10, # 10px margin from bottom
            w, 
            h
        )
        self.marker_gallery.raise_()
