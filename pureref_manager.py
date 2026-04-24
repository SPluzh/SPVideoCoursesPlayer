"""PureRef integration — create, open, and focus .pur files."""

import ctypes
import ctypes.wintypes
import logging
import subprocess
from pathlib import Path

from config_manager import ConfigManager


class PureRefManager:
    """Manages PureRef file creation, launching, and window focusing.

    Tracks one PureRef process per folder so that opening PureRef from
    different folders launches separate instances, while re-opening
    from the same folder focuses the existing window.
    """

    def __init__(self, config: ConfigManager):
        self.config = config
        # {resolved_folder_path: subprocess.Popen}
        self._processes: dict[Path, subprocess.Popen] = {}

    def has_pur_file(self, folder: Path) -> bool:
        """Check if a .pur file exists in the folder."""
        filename = self.config.get_pureref_filename()
        return (folder / filename).exists()

    def get_file_size(self, folder: Path) -> int:
        """Get the size of the .pur file in bytes.
        
        Returns:
            File size in bytes, or 0 if file doesn't exist.
        """
        filename = self.config.get_pureref_filename()
        pur_file = folder / filename
        if pur_file.exists():
            try:
                return pur_file.stat().st_size
            except Exception as e:
                logging.error(f"Error getting PureRef file size: {e}")
                return 0
        return 0

    def delete(self, folder: Path) -> tuple[bool, str]:
        """Delete the .pur file for the given folder.
        
        Returns:
            (success, error_message) — success=True if ok,
            otherwise error_message contains the reason.
        """
        filename = self.config.get_pureref_filename()
        pur_file = folder / filename

        if not pur_file.exists():
            return False, "file_not_found"

        # Clean up running process if any
        key = folder.resolve()
        proc = self._processes.pop(key, None)
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception as e:
                logging.warning(f"Error terminating PureRef process: {e}")

        # Delete the file
        try:
            pur_file.unlink()
            logging.info(f"Deleted PureRef file: {pur_file}")
            return True, ""
        except Exception as e:
            logging.error(f"Error deleting PureRef file: {e}")
            return False, f"delete_error:{e}"

    def is_running(self, folder: Path) -> bool:
        """Check if PureRef is currently running for this folder."""
        key = folder.resolve()
        proc = self._processes.get(key)
        return proc is not None and proc.poll() is None

    def open(self, folder: Path) -> tuple[bool, str]:
        """Open or create a PureRef file for the given folder.

        Returns:
            (success, error_message) — success=True if ok,
            otherwise error_message contains the reason.
        """
        pureref_exe = Path(self.config.get_pureref_path())
        pureref_filename = self.config.get_pureref_filename()
        pur_file = folder / pureref_filename

        if not pureref_exe.exists():
            return False, f"pureref_not_found:{pureref_exe}"

        # Create file if it doesn't exist
        if not pur_file.exists():
            try:
                pur_file.touch()
            except Exception as e:
                logging.error(f"Error creating PureRef file: {e}")
                return False, f"create_error:{e}"

        key = folder.resolve()

        # Check if we already have a running process for THIS folder
        proc = self._processes.get(key)
        if proc is not None and proc.poll() is None:
            # Process is still alive — try to focus its window
            logging.debug(
                f"PureRef process already running for {folder}, attempting to focus window (PID: {proc.pid})"
            )
            if self._focus_window_by_pid(proc.pid):
                logging.debug(f"Successfully focused existing PureRef window")
                return True, ""
            # Window not found (maybe minimized to tray) — still running,
            # don't launch duplicate
            logging.debug(
                f"Could not find window for PID {proc.pid}, but process is still alive - not launching duplicate"
            )
            return True, ""

        # Clean up dead process entry if any
        self._processes.pop(key, None)

        # Launch PureRef
        try:
            logging.debug(f"Launching new PureRef instance for {folder}")
            proc = subprocess.Popen([str(pureref_exe), str(pur_file)])
            self._processes[key] = proc
            logging.debug(f"PureRef launched successfully (PID: {proc.pid})")
            return True, ""
        except Exception as e:
            logging.error(f"Error launching PureRef: {e}")
            return False, f"launch_error:{e}"

    def _focus_window_by_pid(self, pid: int) -> bool:
        """Find and focus a PureRef window belonging to the given process ID.

        Uses WinAPI EnumWindows + GetWindowThreadProcessId to locate the
        window owned by the specific PureRef process, then brings it
        to the foreground.
        """
        try:
            found_hwnd = [None]
            target_pid = ctypes.wintypes.DWORD(pid)

            @ctypes.WINFUNCTYPE(
                ctypes.wintypes.BOOL,
                ctypes.wintypes.HWND,
                ctypes.wintypes.LPARAM,
            )
            def enum_callback(hwnd, _lParam):
                # Check if this window belongs to our target process
                window_pid = ctypes.wintypes.DWORD()
                ctypes.windll.user32.GetWindowThreadProcessId(
                    hwnd, ctypes.byref(window_pid)
                )
                if window_pid.value == target_pid.value:
                    # Verify it's a visible top-level window
                    if ctypes.windll.user32.IsWindowVisible(hwnd):
                        found_hwnd[0] = hwnd
                        return False  # Stop enumeration
                return True

            ctypes.windll.user32.EnumWindows(enum_callback, 0)

            if found_hwnd[0]:
                SW_RESTORE = 9
                ctypes.windll.user32.ShowWindow(found_hwnd[0], SW_RESTORE)
                ctypes.windll.user32.SetForegroundWindow(found_hwnd[0])
                return True
        except Exception as e:
            logging.error(f"Error focusing PureRef window: {e}")

        return False
