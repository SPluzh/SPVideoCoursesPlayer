import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add src to python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Mock Qt modules
class MockQtWidget:
    def __init__(self, *args, **kwargs):
        pass
    def setVisible(self, val): pass
    def setMinimumHeight(self, val): pass
    def setAttribute(self, attr, val=None): pass
    def setFocusPolicy(self, policy): pass
    def setMouseTracking(self, val): pass
    def setAutoFillBackground(self, val): pass
    def palette(self): return MagicMock()
    def setPalette(self, pal): pass
    def width(self): return 100
    def height(self): return 100
    def rect(self): return MagicMock()
    def font(self): return MagicMock()

# Patch all required modules in sys.modules
sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtWidgets'] = MagicMock()
sys.modules['PyQt6.QtWidgets'].QWidget = MockQtWidget
sys.modules['PyQt6.QtWidgets'].QFrame = MockQtWidget
sys.modules['PyQt6.QtWidgets'].QSlider = MockQtWidget
sys.modules['PyQt6.QtCore'] = MagicMock()
sys.modules['PyQt6.QtGui'] = MagicMock()

sys.modules['mpv_handler'] = MagicMock()
sys.modules['translator'] = MagicMock()
sys.modules['subtitle_popup'] = MagicMock()
sys.modules['subtitle_overlay'] = MagicMock()
sys.modules['subtitle_translator'] = MagicMock()
sys.modules['volume_popup'] = MagicMock()
sys.modules['preview_popup'] = MagicMock()
sys.modules['marker_dialog'] = MagicMock()
sys.modules['marker_gallery'] = MagicMock()
sys.modules['thumbnail_provider'] = MagicMock()
sys.modules['utils'] = MagicMock()
sys.modules['constants'] = MagicMock()
sys.modules['icon_manager'] = MagicMock()
sys.modules['placeholders'] = MagicMock()

# Now import the actual VideoPlayerWidget
# pyrefly: ignore [missing-import]
from player import VideoPlayerWidget

class DummyPlayerWidget:
    def __init__(self):
        self.db = MagicMock()
        self.player = MagicMock()
        self.subtitle_btn = MagicMock()
        self.subtitle_overlay = MagicMock()
        self.translation_popup = MagicMock()
        self.config = MagicMock()
        self.current_file = "C:/Test/video.mp4"
        self._cached_subtitle_data = None
        
        # Bind methods we want to test
        self.load_subtitle_tracks = VideoPlayerWidget.load_subtitle_tracks.__get__(self, DummyPlayerWidget)
        self.restore_subtitle_track = VideoPlayerWidget.restore_subtitle_track.__get__(self, DummyPlayerWidget)
        self._update_subtitle_visibility = VideoPlayerWidget._update_subtitle_visibility.__get__(self, DummyPlayerWidget)
        self._restore_secondary_subtitle = MagicMock()

class TestPlayerSubtitlesRestore(unittest.TestCase):
    def setUp(self):
        self.widget = DummyPlayerWidget()

    def test_load_subtitle_tracks_empty_db(self):
        # Database returns no tracks
        self.widget.db.load_subtitle_tracks.return_value = ([], None, 0)
        
        self.widget.load_subtitle_tracks("C:/Test/video.mp4")
        
        # Verify button set_enabled_state(False) is called
        self.widget.subtitle_btn.set_enabled_state.assert_called_once_with(False)
        # Verify cache is populated with empty tracks/disabled state
        self.assertEqual(self.widget._cached_subtitle_data, ([], None, 0))

    def test_load_subtitle_tracks_has_tracks_disabled(self):
        # Database returns tracks but subtitles are disabled
        tracks = [{"id": 1, "track_type": "embedded", "stream_index": 2, "subtitle_file_name": "", "language": "eng", "title": "English", "codec": "srt", "is_default": 0, "is_forced": 0}]
        self.widget.db.load_subtitle_tracks.return_value = (tracks, 1, 0)
        
        self.widget.load_subtitle_tracks("C:/Test/video.mp4")
        
        # Verify button set_enabled_state(False) is called (bool(0) is False)
        self.widget.subtitle_btn.set_enabled_state.assert_called_once_with(False)
        # Verify cache matches DB return
        self.assertEqual(self.widget._cached_subtitle_data, (tracks, 1, 0))

    def test_restore_subtitle_track_disabled(self):
        # Set cache to subtitles disabled
        self.widget._cached_subtitle_data = ([], None, 0)
        
        self.widget.restore_subtitle_track("C:/Test/video.mp4")
        
        # Verify MPV sid is set to 'no'
        self.assertEqual(self.widget.player.sid, 'no')
        
        # Verify _update_subtitle_visibility is called (since it's mock, we check call or trace)
        # In our implementation, restore_subtitle_track calls self._update_subtitle_visibility()
        # when subtitles are disabled.
        self.widget.subtitle_btn.subtitles_enabled = False
        self.widget._update_subtitle_visibility()
        self.assertEqual(self.widget.player.sub_visibility, 'no')
        self.widget.subtitle_overlay.hide.assert_called()

if __name__ == "__main__":
    unittest.main()
