"""
OSD Manager for SPVideoCoursesPlayer

Centralized manager for all on-screen display (OSD) notifications.
Provides a consistent, extensible interface for showing user feedback.
"""

import logging
from translator import tr


class OSDManager:
    """Manages all OSD notifications through MPV's show_text API."""

    def __init__(self, player):
        """
        Initialize OSD Manager.

        Args:
            player: MPV player instance with show_text() method
        """
        self.player = player
        self.default_duration = 2500  # milliseconds (same as zoom)
        self.enabled = True  # OSD notifications enabled by default

    def set_enabled(self, enabled: bool):
        """
        Enable or disable OSD notifications.

        Args:
            enabled: True to enable OSD, False to disable
        """
        self.enabled = enabled

    def show_osd(self, message, duration=None):
        """
        Show a generic OSD message.

        Args:
            message: Text to display
            duration: Display duration in milliseconds (default: 2500ms)
        """
        if not self.enabled or not self.player:
            return

        try:
            duration = duration if duration is not None else self.default_duration
            self.player.show_text(message, duration)
        except Exception as e:
            logging.error(f"Error showing OSD: {e}", exc_info=True)

    def show_speed(self, speed):
        """
        Show playback speed OSD.

        Args:
            speed: Playback speed (e.g., 1.0, 1.5, 2.0)
        """
        message = tr("player.osd.speed", speed=f"{speed:.1f}")
        self.show_osd(message)

    def show_zoom(self, zoom_percent):
        """
        Show zoom level OSD.

        Args:
            zoom_percent: Zoom percentage (e.g., 100, 150, 200)
        """
        message = tr("player.zoom_level", percent=zoom_percent)
        self.show_osd(message)

    def show_volume(self, volume):
        """
        Show volume level OSD.

        Args:
            volume: Volume level 0-100
        """
        message = tr("player.osd.volume", volume=volume)
        self.show_osd(message)

    def show_audio_track(self, track_name):
        """
        Show audio track selection OSD.

        Args:
            track_name: Name of the selected audio track
        """
        message = tr("player.osd.audio_track", track=track_name)
        self.show_osd(message)

    def show_subtitle_on(self, track_name):
        """
        Show subtitle enabled OSD.

        Args:
            track_name: Name of the subtitle track
        """
        message = tr("player.osd.subtitle_on", track=track_name)
        self.show_osd(message)

    def show_subtitle_off(self):
        """
        Show subtitle disabled OSD.
        """
        message = tr("player.osd.subtitle_off")
        self.show_osd(message)

    def show_audio_delay(self, delay_ms):
        """
        Show audio delay OSD.

        Args:
            delay_ms: Audio delay in milliseconds (can be negative)
        """
        sign = "+" if delay_ms >= 0 else ""
        message = tr("player.osd.audio_delay", delay=f"{sign}{delay_ms}")
        self.show_osd(message)

    def show_screenshot(self, success=True):
        """
        Show screenshot result OSD.

        Args:
            success: Whether screenshot was successful
        """
        if success:
            message = tr("player.osd.screenshot_success")
        else:
            message = tr("player.osd.screenshot_failed")
        self.show_osd(message)

    def show_marker_added(self, marker_name):
        """
        Show marker added OSD.

        Args:
            marker_name: Name of the added marker
        """
        message = tr("player.osd.marker_added", name=marker_name)
        self.show_osd(message)

    def show_marker_deleted(self, marker_name=None):
        """
        Show marker deleted OSD.

        Args:
            marker_name: Name of the deleted marker (optional)
        """
        if marker_name:
            message = tr("player.osd.marker_deleted_named", name=marker_name)
        else:
            message = tr("player.osd.marker_deleted")
        self.show_osd(message)

    def show_pause_state(self, paused):
        """
        Show pause/play state OSD.

        Args:
            paused: True if paused, False if playing
        """
        if paused:
            message = tr("player.osd.paused")
        else:
            message = tr("player.osd.playing")
        self.show_osd(message)

    def show_next_video(self, video_name: str):
        """
        Show next video OSD.

        Args:
            video_name: Name of the next video
        """
        # Обрезаем имя файла до 50 символов
        if len(video_name) > 50:
            video_name = video_name[:47] + "..."
        message = tr("player.osd.playing_next", name=video_name)
        self.show_osd(message)

    def show_prev_video(self, video_name: str):
        """
        Show previous video OSD.

        Args:
            video_name: Name of the previous video
        """
        # Обрезаем имя файла до 50 символов
        if len(video_name) > 50:
            video_name = video_name[:47] + "..."
        message = tr("player.osd.playing_prev", name=video_name)
        self.show_osd(message)

    def show_always_on_top(self, enabled: bool):
        """
        Show always on top state OSD.

        Args:
            enabled: True if always on top is enabled, False otherwise
        """
        if enabled:
            message = tr("player.osd.always_on_top_enabled")
        else:
            message = tr("player.osd.always_on_top_disabled")
        self.show_osd(message)

    def show_seek(self, seconds):
        """
        Show seek OSD.

        Args:
            seconds: Number of seconds (positive for forward, negative for backward)
        """
        if seconds > 0:
            message = tr("player.osd.seek_forward", seconds=seconds)
        else:
            message = tr("player.osd.seek_backward", seconds=abs(seconds))
        self.show_osd(message)

    def show_seek_percent(self, percent):
        """
        Show seek to percentage OSD.

        Args:
            percent: Percentage to seek to (0-100)
        """
        message = tr("player.osd.seek_percent", percent=percent)
        self.show_osd(message, duration=1000)

    def show_frame_step(self, forward=True):
        """
        Show frame step OSD.

        Args:
            forward: True for next frame, False for previous frame
        """
        if forward:
            message = tr("player.osd.frame_forward")
        else:
            message = tr("player.osd.frame_backward")
        self.show_osd(message)

    def show_noise_mode(self, mode):
        """
        Show noise reduction mode OSD.

        Args:
            mode: Noise reduction mode ('off', 'standard', 'ai')
        """
        if mode == "off":
            message = tr("player.osd.noise_off")
        elif mode == "standard":
            message = tr("player.osd.noise_standard")
        elif mode == "ai":
            message = tr("player.osd.noise_ai")
        else:
            return
        self.show_osd(message)

    def show_compressor(self, enabled):
        """
        Show compressor state OSD.

        Args:
            enabled: True if compressor is enabled, False otherwise
        """
        message = tr(
            "player.osd.compressor_on" if enabled else "player.osd.compressor_off"
        )
        self.show_osd(message)

    def show_deesser(self, enabled):
        """
        Show de-esser state OSD.

        Args:
            enabled: True if de-esser is enabled, False otherwise
        """
        message = tr("player.osd.deesser_on" if enabled else "player.osd.deesser_off")
        self.show_osd(message)

    def show_mono_mode(self, enabled):
        """
        Show mono mode state OSD.

        Args:
            enabled: True if mono mode is enabled, False otherwise
        """
        message = tr("player.osd.mono_on" if enabled else "player.osd.mono_off")
        self.show_osd(message)

    def show_bookmarks_gallery(self, visible, count):
        """
        Show bookmarks gallery state OSD.

        Args:
            visible: True if gallery is now visible, False if hidden
            count: Number of bookmarks
        """
        if visible:
            message = tr("player.osd.bookmarks_shown", count=count)
        else:
            message = tr("player.osd.bookmarks_hidden")
        self.show_osd(message)
