
import sys
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QPalette

from mpv_handler import setup_mpv_dll, MPVVideoWidget
from translator import tr
from subtitle_popup import SubtitleButton
from volume_popup import VolumeButton

ROOT_DIR = Path(__file__).parent
RESOURCES_DIR = ROOT_DIR / "resources"

class ClickableSlider(QSlider):
    """Slider that jumps to click position."""
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos_ratio = event.position().x() / self.width()
            value = int(self.minimum() + pos_ratio * (self.maximum() - self.minimum()))
            self.setValue(value)
            self.sliderMoved.emit(value)
        super().mousePressEvent(event)


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

    def __init__(self, parent=None):
        super().__init__(parent)
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
        self.setup_ui()
        self.setup_mpv()

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

        layout.addWidget(self.video_container, 1)

        control_panel = QWidget()
        control_panel.setObjectName("controlPanel")
        panel_layout = QHBoxLayout(control_panel)
        panel_layout.setContentsMargins(0, 5, 0, 0)

        self.icons = {}
        for name in ["prev_frame", "next_frame", "play", "pause", "screenshot", "next", "prev"]:
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

        self.frame_back_btn = QPushButton()
        self.frame_back_btn.setIcon(self.icons['prev_frame'])
        self.frame_back_btn.setFixedSize(30, 30)
        self.frame_back_btn.setToolTip(tr('player.tooltip_frame_back'))
        self.frame_back_btn.clicked.connect(self.frame_back_step)
        self.frame_back_btn.setEnabled(False)
        panel_layout.addWidget(self.frame_back_btn)

        self.play_btn = QPushButton()
        self.play_btn.setIcon(self.icons['play'])
        self.play_btn.setObjectName("playBtn")
        self.play_btn.setFixedHeight(30)
        self.play_btn.clicked.connect(self.play_pause)
        self.play_btn.setEnabled(False)
        panel_layout.addWidget(self.play_btn)

        self.frame_step_btn = QPushButton()
        self.frame_step_btn.setIcon(self.icons['next_frame'])
        self.frame_step_btn.setFixedSize(30, 30)
        self.frame_step_btn.setToolTip(tr('player.tooltip_frame_step'))
        self.frame_step_btn.clicked.connect(self.frame_step)
        self.frame_step_btn.setEnabled(False)
        panel_layout.addWidget(self.frame_step_btn)

        # Next Video Button
        self.next_video_btn = QPushButton()
        self.next_video_btn.setIcon(self.icons['next'])
        self.next_video_btn.setFixedSize(30, 30)
        self.next_video_btn.setToolTip(tr('player.tooltip_next_video'))
        self.next_video_btn.clicked.connect(self.next_video_requested.emit)
        self.next_video_btn.setEnabled(False)
        panel_layout.addWidget(self.next_video_btn)

        self.progress_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.sliderMoved.connect(self.set_position)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.progress_slider.setEnabled(False)
        panel_layout.addWidget(self.progress_slider, 1)

        self.time_label = QLabel("00:00 / 00:00")
        panel_layout.addWidget(self.time_label)


        # Subtitle button: Left click - select, Right click - toggle
        self.subtitle_btn = SubtitleButton()
        self.subtitle_btn.subtitleToggled.connect(self.toggle_subtitles)
        self.subtitle_btn.subtitleChanged.connect(self.change_subtitle_track)
        self.subtitle_btn.popup.styleChanged.connect(self.change_subtitle_style)
        panel_layout.addWidget(self.subtitle_btn)

        self.screenshot_btn = QPushButton()
        self.screenshot_btn.setIcon(self.icons['screenshot'])
        self.screenshot_btn.setFixedSize(30, 30)
        self.screenshot_btn.setToolTip(tr('player.tooltip_screenshot'))
        self.screenshot_btn.clicked.connect(self.screenshot_to_clipboard)
        self.screenshot_btn.setEnabled(False)
        panel_layout.addWidget(self.screenshot_btn)

        self.reset_zoom_btn = QPushButton("100%")
        self.reset_zoom_btn.setFixedWidth(80)
        self.reset_zoom_btn.setFixedHeight(30)
        self.reset_zoom_btn.setToolTip(tr('player.tooltip_zoom'))
        self.reset_zoom_btn.clicked.connect(self.reset_zoom)
        panel_layout.addWidget(self.reset_zoom_btn)

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

        layout.addWidget(control_panel)

        self.video_widget.toggle_play_pause.connect(self.play_pause)

    def frame_step(self):
        """Step forward one frame."""
        self.video_widget.frame_step()

    def frame_back_step(self):
        """Step backward one frame."""
        self.video_widget.frame_back_step()

    def screenshot_to_clipboard(self):
        """Screenshot to clipboard."""
        if self.video_widget.screenshot_to_clipboard():
            self.show_screenshot_notification()

    def show_screenshot_notification(self):
        """Show screenshot notification."""
        original_icon = self.screenshot_btn.icon()
        self.screenshot_btn.setIcon(QIcon())
        self.screenshot_btn.setText("✓")
        
        def restore():
            self.screenshot_btn.setText("")
            self.screenshot_btn.setIcon(original_icon)
            
        QTimer.singleShot(1000, restore)

    def on_zoom_changed(self, zoom_level):
        """Handle zoom change."""
        zoom_percent = int(100 * (2 ** zoom_level))
        self.reset_zoom_btn.setText(f"{zoom_percent}%")

    def reset_zoom(self):
        """Reset zoom via button."""
        self.video_widget.reset_zoom_pan()

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
        self.position_restore_attempted = False
        self.is_loading = True
        self.auto_play_pending = auto_play

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
            self.frame_back_btn.setEnabled(True)
            self.frame_step_btn.setEnabled(True)
            self.prev_video_btn.setEnabled(True)
            self.next_video_btn.setEnabled(True)
            self.screenshot_btn.setEnabled(True)

            # ADDED: Load audio tracks
            QTimer.singleShot(200, lambda: self.load_audio_tracks(file_path))
            
            # Load tracks info from DB and restore state
            QTimer.singleShot(100, lambda: self.load_subtitle_tracks(file_path))
            QTimer.singleShot(200, lambda: self.restore_subtitle_track(file_path))

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
        self.frame_back_btn.setToolTip(tr('player.tooltip_frame_back'))
        self.frame_step_btn.setToolTip(tr('player.tooltip_frame_step'))
        self.screenshot_btn.setToolTip(tr('player.tooltip_screenshot'))
        self.reset_zoom_btn.setToolTip(tr('player.tooltip_zoom'))
        self.volume_btn.update_texts()
        self.subtitle_btn.update_texts()
        self.play_btn.setToolTip(tr('player.play') if self.player and self.player.pause else tr('player.pause'))
