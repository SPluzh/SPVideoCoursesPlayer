
import sys
import os
import configparser
from pathlib import Path

from PyQt6.QtWidgets import QFrame, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QPainter, QPixmap, QKeyEvent, QMouseEvent, QCursor

from placeholders import draw_video_placeholder

# Define global paths locally to avoid circular imports from main
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

def setup_mpv_dll():
    """Set up the MPV DLL path for the application."""
    # Initial read for DLL setup (happens once at startup)
    config = configparser.ConfigParser()
    config_file = RESOURCES_DIR / 'settings.ini'
    if config_file.exists():
        config.read(config_file, encoding='utf-8')
    
    dll_path = resolve_binary_path(config, 'libmpv_path', 'bin/libmpv-2.dll')
    bin_dir = dll_path.parent
    if dll_path.exists():
        # Add to PATH for all versions
        os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
        # Specifically for Python 3.8+ on Windows
        if hasattr(os, 'add_dll_directory'):
            os.add_dll_directory(str(bin_dir))
        print(f"MPV DLL path set: {bin_dir}")
        return True
    else:
        # Try to find in current folder (backward compatibility)
        old_dll_path = ROOT_DIR / "libmpv-2.dll"
        if old_dll_path.exists():
            os.environ["PATH"] = str(ROOT_DIR) + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, 'add_dll_directory'):
                os.add_dll_directory(str(ROOT_DIR))
            print(f"MPV DLL path set: {ROOT_DIR} (legacy)")
            return True
        else:
            print(f"WARNING: libmpv-2.dll not found at {dll_path}")
            return False

class MPVVideoWidget(QFrame):
    """Video widget for MPV with fullscreen, zoom, and pan support."""
    requestfloatwindow = pyqtSignal()
    toggle_play_pause = pyqtSignal()
    zoom_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(300)
        self.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self.setAutoFillBackground(True)
        # We need to set the palette locally or import QColor/QPalette
        from PyQt6.QtGui import QPalette, QColor
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        self.setPalette(palette)

        self.is_fullscreen = False
        self.click_timer = QTimer()
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(self._handle_single_click)
        self.pending_single_click = False

        self.player = None

        self.zoom_level = 0.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.zoom_step = 0.1
        self.min_zoom = 0.0
        self.max_zoom = 5.0

        self.is_panning = False
        self.pan_start_pos = None
        self.pan_start_x = 0.0
        self.pan_start_y = 0.0

        self.z_key_pressed = False
        self.is_zooming_with_mouse = False
        self.zoom_start_pos = None
        self.zoom_start_level = 0.0

    def set_player(self, player):
        """Set reference to MPV player."""
        self.player = player

    def paintEvent(self, event):
        """Draw a beautiful placeholder when no video is loaded"""
        if self.player is None or not hasattr(self.player, 'filename') or self.player.filename is None:
            painter = QPainter(self)
            draw_video_placeholder(painter, self.rect())
            painter.end()
        else:
            super().paintEvent(event)

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        if not self.player:
            return super().wheelEvent(event)

        delta = event.angleDelta().y()
        old_zoom = self.zoom_level

        if delta > 0:
            self.zoom_level = min(self.zoom_level + self.zoom_step, self.max_zoom)
        elif delta < 0:
            self.zoom_level = max(self.zoom_level - self.zoom_step, self.min_zoom)

        if self.zoom_level != old_zoom:
            self._apply_zoom()
        event.accept()

    def _apply_zoom(self):
        """Apply current zoom level."""
        try:
            self.player.video_zoom = self.zoom_level
            self.zoom_changed.emit(self.zoom_level)

            if self.zoom_level <= 0:
                self.pan_x = 0.0
                self.pan_y = 0.0
                self.player.video_pan_x = 0.0
                self.player.video_pan_y = 0.0
        except Exception as e:
            print(f"Error setting zoom: {e}")

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape and self.is_fullscreen:
            self.is_fullscreen = False
            self.setWindowFlags(Qt.WindowType.SubWindow)
            self.showNormal()
            event.accept()
        elif event.key() == Qt.Key.Key_Z and not event.isAutoRepeat():
            self.z_key_pressed = True
            self.setCursor(Qt.CursorShape.SizeVerCursor)
            event.accept()
        elif event.key() == Qt.Key.Key_R:
            self.reset_zoom_pan()
            event.accept()
        elif event.key() == Qt.Key.Key_Plus or event.key() == Qt.Key.Key_Equal:
            self.zoom_in()
            event.accept()
        elif event.key() == Qt.Key.Key_Minus:
            self.zoom_out()
            event.accept()
        elif event.key() == Qt.Key.Key_0:
            self.reset_zoom_pan()
            event.accept()
        elif event.key() in (Qt.Key.Key_Comma, Qt.Key.Key_Less):
            self.frame_back_step()
            event.accept()
        elif event.key() in (Qt.Key.Key_Period, Qt.Key.Key_Greater):
            self.frame_step()
            event.accept()
        elif event.key() == Qt.Key.Key_S:
            self.screenshot_to_clipboard()
            event.accept()
        elif event.key() == Qt.Key.Key_Print:
            self.screenshot_to_clipboard()
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Z and not event.isAutoRepeat():
            self.z_key_pressed = False
            self.is_zooming_with_mouse = False
            self.zoom_start_pos = None
            if not self.is_panning:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            if self.z_key_pressed:
                self.is_zooming_with_mouse = True
                self.zoom_start_pos = event.position()
                self.zoom_start_level = self.zoom_level
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            else:
                self.is_panning = True
                self.pan_start_pos = event.position()
                self.pan_start_x = self.pan_x
                self.pan_start_y = self.pan_y
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton:
            if not self.click_timer.isActive():
                self.pending_single_click = True
                self.click_timer.start(250)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_zooming_with_mouse and self.player and self.zoom_start_pos:
            delta_y = self.zoom_start_pos.y() - event.position().y()
            sensitivity = 1.0 / 200.0
            new_zoom = self.zoom_start_level + delta_y * sensitivity
            new_zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))
            if abs(new_zoom - self.zoom_level) > 0.01:
                self.zoom_level = new_zoom
                self._apply_zoom()
            event.accept()
        elif self.is_panning and self.player and self.pan_start_pos:
            delta = event.position() - self.pan_start_pos
            zoom_factor = 2 ** self.zoom_level

            sensitivity_x = 1.0 / (self.width() * zoom_factor) if self.width() > 0 else 0
            sensitivity_y = 1.0 / (self.height() * zoom_factor) if self.height() > 0 else 0

            self.pan_x = self.pan_start_x + delta.x() * sensitivity_x
            self.pan_y = self.pan_start_y + delta.y() * sensitivity_y

            max_pan = max(0.0, 1.0 - (1.0 / zoom_factor))
            self.pan_x = max(-max_pan, min(max_pan, self.pan_x))
            self.pan_y = max(-max_pan, min(max_pan, self.pan_y))

            try:
                self.player.video_pan_x = self.pan_x
                self.player.video_pan_y = self.pan_y
            except Exception as e:
                print(f"Error setting pan: {e}")
            event.accept()
        else:
            if self.z_key_pressed:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            if self.is_zooming_with_mouse:
                self.is_zooming_with_mouse = False
                self.zoom_start_pos = None
            elif self.is_panning:
                self.is_panning = False
                self.pan_start_pos = None

            if self.z_key_pressed:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _handle_single_click(self):
        if self.pending_single_click:
            self.pending_single_click = False
            self.toggle_play_pause.emit()

    def _get_target_screen(self):
        """Find the screen that should contain this window or where the user is looking."""
        # 1. Try to find the screen by mouse position (most accurate for user intent)
        cursor_pos = QCursor.pos()
        for screen in QApplication.screens():
            if screen.geometry().contains(cursor_pos):
                return screen
        
        # 2. Try to find the screen by window center (most accurate for current placement)
        window = self.window()
        if window:
            window_center = window.geometry().center()
            for screen in QApplication.screens():
                if screen.geometry().contains(window_center):
                    return screen
            
            # 3. Fallback to the current window's screen association
            if window.screen():
                return window.screen()
        
        # 4. Final fallback
        return QApplication.primaryScreen()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.click_timer.stop()
            self.pending_single_click = False
            self.is_fullscreen = not self.is_fullscreen

            if self.is_fullscreen:
                screen = self._get_target_screen()
                screen_geometry = screen.geometry()
                
                self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
                self.show() # Ensure window handle is created/updated for the new window mode
                
                if self.windowHandle():
                    self.windowHandle().setScreen(screen)
                
                self.setGeometry(screen_geometry)
                self.showFullScreen()
            else:
                self.setWindowFlags(Qt.WindowType.SubWindow)
                self.showNormal()
            event.accept()
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.reset_zoom_pan()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def zoom_in(self):
        """Increase zoom level."""
        if self.player:
            self.zoom_level = min(self.zoom_level + self.zoom_step, self.max_zoom)
            self._apply_zoom()

    def zoom_out(self):
        """Decrease zoom level."""
        if self.player:
            self.zoom_level = max(self.zoom_level - self.zoom_step, self.min_zoom)
            self._apply_zoom()

    def reset_zoom_pan(self):
        """Reset zoom and pan to default values."""
        self.zoom_level = 0.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        if self.player:
            try:
                self.player.video_zoom = 0.0
                self.player.video_pan_x = 0.0
                self.player.video_pan_y = 0.0
                self.zoom_changed.emit(0.0)
            except Exception as e:
                print(f"Error resetting zoom/pan: {e}")

    def get_zoom_percent(self):
        """Get current zoom in percent."""
        return int(100 * (2 ** self.zoom_level))

    def frame_step(self):
        """Step forward one frame."""
        if self.player:
            try:
                if not self.player.pause:
                    self.player.pause = True
                self.player.frame_step()
            except Exception as e:
                print(f"Error frame step: {e}")

    def frame_back_step(self):
        """Step backward one frame."""
        if self.player:
            try:
                if not self.player.pause:
                    self.player.pause = True
                self.player.frame_back_step()
            except Exception as e:
                print(f"Error frame back step: {e}")

    def screenshot_to_clipboard(self):
        """Take screenshot of current frame to clipboard."""
        if not self.player:
            return False

        try:
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                temp_path = f.name

            self.player.screenshot_to_file(temp_path, includes='video')

            if os.path.exists(temp_path):
                pixmap = QPixmap(temp_path)
                if not pixmap.isNull():
                    QApplication.clipboard().setPixmap(pixmap)
                    print(f"Screenshot copied to clipboard ({pixmap.width()}x{pixmap.height()})")
                    os.remove(temp_path)
                    return True
                else:
                    print("Failed to load screenshot")
                    os.remove(temp_path)
        except Exception as e:
            print(f"Error taking screenshot: {e}")

        return False
