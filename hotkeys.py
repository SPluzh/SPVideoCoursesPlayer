from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QKeyEvent
import ctypes
from ctypes import wintypes
import time
import logging


class GlobalHotkeyThread(QThread):
    action_triggered = pyqtSignal(str)
    action_state_changed = pyqtSignal(str, bool)  # action, is_pressed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True

        # Windows virtual key codes
        self.VK_MEDIA_NEXT_TRACK = 0xB0
        self.VK_MEDIA_PREV_TRACK = 0xB1
        self.VK_MEDIA_STOP = 0xB2
        self.VK_MEDIA_PLAY_PAUSE = 0xB3
        self.VK_VOLUME_MUTE = 0xAD
        self.VK_VOLUME_DOWN = 0xAE
        self.VK_VOLUME_UP = 0xAF
        self.VK_Z = 0x5A

    def run(self):
        logging.debug("GlobalHotkeyThread run enter")  # DEBUG
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            # Map VK codes to internal action names (Trigger items)
            trigger_vk_map = {
                self.VK_MEDIA_PLAY_PAUSE: "toggle_pause",
                self.VK_MEDIA_STOP: "pause",
                self.VK_MEDIA_NEXT_TRACK: "next_video",
                self.VK_MEDIA_PREV_TRACK: "prev_video",
            }

            # Map VK codes to state actions (Hold items)
            state_vk_map = {self.VK_Z: "zoom_mode"}

            # Last state for each key
            last_state = {
                vk: False
                for vk in (list(trigger_vk_map.keys()) + list(state_vk_map.keys()))
            }

            # Get current process ID once
            current_pid = kernel32.GetCurrentProcessId()

            while self.running:
                # Check if our application has focus using Windows API (thread-safe)
                has_focus = False
                foreground_hwnd = user32.GetForegroundWindow()
                if foreground_hwnd:
                    foreground_pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(
                        foreground_hwnd, ctypes.byref(foreground_pid)
                    )
                    if foreground_pid.value == current_pid:
                        has_focus = True

                # Process triggers (one-shot actions)
                for vk, action in trigger_vk_map.items():
                    is_down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
                    if is_down and not last_state[vk]:
                        if not has_focus:
                            self.action_triggered.emit(action)
                    last_state[vk] = is_down

                # Process state keys (Hold actions)
                for vk, action in state_vk_map.items():
                    is_down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
                    if is_down != last_state[vk]:
                        if not has_focus:
                            self.action_state_changed.emit(action, is_down)
                        last_state[vk] = is_down

                time.sleep(0.01)
        except Exception as e:
            logging.error(f"❌ CRASH in GlobalHotkeyThread: {e}", exc_info=True)

    def stop(self):
        self.running = False


class HotkeyManager(QObject):
    """Manages hotkey mappings and translates events to application actions."""

    global_action_triggered = pyqtSignal(str)
    global_action_state_changed = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Standard actions (no modifiers or specific modifiers handled separately)
        self.mappings = {
            Qt.Key.Key_Space: "toggle_pause",
            Qt.Key.Key_F: "toggle_fullscreen",
            Qt.Key.Key_Escape: "exit_fullscreen_or_pip",
            Qt.Key.Key_Left: "seek_backward",
            Qt.Key.Key_Right: "seek_forward",
            Qt.Key.Key_M: "toggle_mute",
            Qt.Key.Key_S: "take_screenshot",
            Qt.Key.Key_C: "toggle_subtitles",
            Qt.Key.Key_R: "reset_zoom",
            Qt.Key.Key_Z: "zoom_mode",
            Qt.Key.Key_Comma: "frame_back",
            Qt.Key.Key_Period: "frame_step",
            Qt.Key.Key_BracketLeft: "zoom_out",
            Qt.Key.Key_BracketRight: "zoom_in",
            Qt.Key.Key_B: "add_marker",
            Qt.Key.Key_G: "toggle_marker_gallery",
            Qt.Key.Key_P: "toggle_pip",
            Qt.Key.Key_L: "locate_video",
            Qt.Key.Key_T: "toggle_always_on_top",
            Qt.Key.Key_E: "expand_tree",
            Qt.Key.Key_W: "collapse_tree",
            # Fallback for Cyrillic layout (Russian)
            0x410: "toggle_fullscreen",  # RU A (where F is)
            0x44C: "toggle_mute",  # RU softign (where M is)
            0x42B: "take_screenshot",  # RU Y (where S is)
            0x441: "toggle_subtitles",  # RU S (where C is)
            0x41A: "reset_zoom",  # RU K (where R is)
            0x42F: "zoom_mode",  # RU YA (where Z is)
            0x431: "frame_back",  # RU B (where < is)
            0x44E: "frame_step",  # RU YU (where > is)
            0x445: "zoom_out",  # RU H (where [ is)
            0x445: "zoom_out",  # RU H (where [ is)
            0x44A: "zoom_in",  # RU TVZ (where ] is)
            0x418: "add_marker",  # RU I (where B is)
            0x41F: "toggle_marker_gallery",  # RU P (where G is)
            0x417: "toggle_pip",  # RU Z (where P is)
            0x414: "locate_video",  # RU D (where L is)
            0x415: "toggle_always_on_top",  # RU E (where T is)
            0x423: "expand_tree",  # RU U (where E is)
            0x426: "collapse_tree",  # RU TS (where W is)
            # Multimedia keys (local behavior)
            Qt.Key.Key_MediaPlay: "toggle_pause",
            Qt.Key.Key_MediaPause: "toggle_pause",
            Qt.Key.Key_MediaTogglePlayPause: "toggle_pause",
            Qt.Key.Key_MediaStop: "pause",
            Qt.Key.Key_MediaNext: "next_video",
            Qt.Key.Key_MediaPrevious: "prev_video",
        }
        # Actions strictly requiring Ctrl modifier
        self.ctrl_mappings = {
            Qt.Key.Key_L: "toggle_library",
        }

        # Actions strictly requiring Shift modifier
        self.shift_mappings = {
            Qt.Key.Key_Left: "prev_video",
            Qt.Key.Key_Right: "next_video",
            Qt.Key.Key_Up: "volume_up",
            Qt.Key.Key_Down: "volume_down",
            Qt.Key.Key_Comma: "audio_delay_down",  # Shift + <
            Qt.Key.Key_Period: "audio_delay_up",  # Shift + >
        }

        # Navigation/Speed (no shift)
        self.plain_arrow_mappings = {
            Qt.Key.Key_Up: "speed_up",
            Qt.Key.Key_Down: "speed_down",
        }

        # Windows-specific layout independent mappings (Virtual Keys)
        self.win_vk_mappings = {
            0x46: "toggle_fullscreen",  # F
            0x1B: "exit_fullscreen_or_pip",  # ESC
            0x4D: "toggle_mute",  # M
            0x53: "take_screenshot",  # S
            0x43: "toggle_subtitles",  # C
            0x52: "reset_zoom",  # R
            0x5A: "zoom_mode",  # Z
            0xBC: "frame_back",  # Comma (<)
            0xBE: "frame_step",  # Period (>)
            0xDB: "zoom_out",  # [
            0xDD: "zoom_in",  # ]
            0x42: "add_marker",  # B
            0x47: "toggle_marker_gallery",  # G
            0x50: "toggle_pip",  # P
            0x50: "toggle_pip",  # P
            0x4C: "locate_video",  # L
            0x54: "toggle_always_on_top",  # T
            0x45: "expand_tree",  # E
            0x57: "collapse_tree",  # W
        }

        # Start global listener thread
        logging.debug("Starting GlobalHotkeyThread")  # DEBUG
        self.global_thread = GlobalHotkeyThread()
        self.global_thread.action_triggered.connect(self.global_action_triggered.emit)
        self.global_thread.action_state_changed.connect(
            self.global_action_state_changed.emit
        )
        self.global_thread.start()
        logging.debug("GlobalHotkeyThread started successfully")  # DEBUG

    def stop(self):
        if hasattr(self, "global_thread"):
            self.global_thread.stop()
            self.global_thread.wait()

    def get_action(self, event: QKeyEvent):
        """
        Returns the action name for the given key event, or None if no mapping exists.
        """
        key = event.key()
        vk = event.nativeVirtualKey()
        modifiers = event.modifiers()

        # Check for Ctrl + key first
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            if key in self.ctrl_mappings:
                return self.ctrl_mappings[key]

        # Check for Shift + Arrow keys first
        if modifiers == Qt.KeyboardModifier.ShiftModifier:
            if key in self.shift_mappings:
                return self.shift_mappings[key]

        # Check for plain Arrow keys (Speed control)
        if modifiers == Qt.KeyboardModifier.NoModifier:
            if key in self.plain_arrow_mappings:
                return self.plain_arrow_mappings[key]

        # Check standard mappings
        action = self.mappings.get(key)
        if action:
            return action

        # If not found by key, check by native virtual key (Windows layout independent)
        if modifiers == Qt.KeyboardModifier.NoModifier:
            if vk in self.win_vk_mappings:
                return self.win_vk_mappings[vk]

        return None
