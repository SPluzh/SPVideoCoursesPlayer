"""
Модуль для отображения прогресса в кнопке таскбара Windows
Требует: pip install comtypes
"""
import sys

COMTYPES_AVAILABLE = False

if sys.platform == 'win32':
    try:
        import ctypes
        from ctypes import POINTER, HRESULT
        from ctypes.wintypes import HWND
        import comtypes
        from comtypes import IUnknown, GUID, COMMETHOD
        import comtypes.client
        COMTYPES_AVAILABLE = True
    except ImportError:
        print("comtypes is not installed. Install it: pip install comtypes")


if COMTYPES_AVAILABLE:
    # Define ITaskbarList3 interface
    class ITaskbarList(IUnknown):
        _iid_ = GUID('{56FDF342-FD6D-11d0-958A-006097C9A090}')
        _methods_ = [
            COMMETHOD([], HRESULT, 'HrInit'),
            COMMETHOD([], HRESULT, 'AddTab', (['in'], HWND, 'hwnd')),
            COMMETHOD([], HRESULT, 'DeleteTab', (['in'], HWND, 'hwnd')),
            COMMETHOD([], HRESULT, 'ActivateTab', (['in'], HWND, 'hwnd')),
            COMMETHOD([], HRESULT, 'SetActiveAlt', (['in'], HWND, 'hwnd')),
        ]

    class ITaskbarList2(ITaskbarList):
        _iid_ = GUID('{602D4995-B13A-429b-A66E-1935E44F4317}')
        _methods_ = [
            COMMETHOD([], HRESULT, 'MarkFullscreenWindow',
                      (['in'], HWND, 'hwnd'),
                      (['in'], ctypes.c_int, 'fFullscreen')),
        ]

    class ITaskbarList3(ITaskbarList2):
        _iid_ = GUID('{ea1afb91-9e28-4b86-90e9-9e9f8a5eefaf}')
        _methods_ = [
            COMMETHOD([], HRESULT, 'SetProgressValue',
                      (['in'], HWND, 'hwnd'),
                      (['in'], ctypes.c_ulonglong, 'ullCompleted'),
                      (['in'], ctypes.c_ulonglong, 'ullTotal')),
            COMMETHOD([], HRESULT, 'SetProgressState',
                      (['in'], HWND, 'hwnd'),
                      (['in'], ctypes.c_int, 'tbpFlags')),
        ]

    # CLSID TaskbarList
    CLSID_TaskbarList = GUID('{56FDF344-FD6D-11d0-958A-006097C9A090}')


class TaskbarProgress:
    """
    Класс для отображения прогресса в кнопке таскбара Windows.
    
    Состояния:
    - NOPROGRESS: Прогресс скрыт
    - INDETERMINATE: Анимация (неопределённый прогресс)
    - NORMAL: Зелёный прогресс-бар
    - ERROR: Красный прогресс-бар
    - PAUSED: Жёлтый прогресс-бар
    """
    
    # State constants
    TBPF_NOPROGRESS = 0x0
    TBPF_INDETERMINATE = 0x1
    TBPF_NORMAL = 0x2
    TBPF_ERROR = 0x4
    TBPF_PAUSED = 0x8
    
    def __init__(self):
        self.hwnd = None
        self.taskbar = None
        self._initialized = False
        self._current_state = self.TBPF_NOPROGRESS
        
        if sys.platform == 'win32' and COMTYPES_AVAILABLE:
            self._init_taskbar()
    
    def _init_taskbar(self):
        """Initialize ITaskbarList3 COM interface."""
        try:
            # Create COM object and get ITaskbarList3 interface
            taskbar = comtypes.client.CreateObject(
                CLSID_TaskbarList,
                interface=ITaskbarList3
            )
            
            # Initialize
            taskbar.HrInit()
            
            self.taskbar = taskbar
            self._initialized = True
            
        except Exception as e:
            print(f"Failed to initialize TaskbarProgress: {e}")
            self._initialized = False
    
    @property
    def is_available(self) -> bool:
        """Checks if taskbar functionality is available."""
        return self._initialized and self.hwnd is not None
    
    def set_hwnd(self, hwnd: int):
        """
        Sets the window handle.
        Call after showing the window (in showEvent).
        
        Args:
            hwnd: Window handle
        """
        self.hwnd = hwnd
    
    def set_progress(self, current: float, total: float):
        """
        Sets the progress value.
        
        Args:
            current: Current value (e.g., played seconds)
            total: Maximum value (e.g., total duration)
        """
        if not self.is_available:
            return
        
        try:
            # Convert to integers for API
            current_int = max(0, int(current))
            total_int = max(1, int(total))  # Avoid division by zero
            
            self.taskbar.SetProgressValue(self.hwnd, current_int, total_int)
            
        except Exception as e:
            print(f"Error setting taskbar progress: {e}")
    
    def set_progress_percent(self, percent: int):
        """
        Sets progress in percent (0-100).
        
        Args:
            percent: Progress percent
        """
        self.set_progress(percent, 100)
    
    def set_state(self, state: int):
        """
        Sets the progress bar state.
        
        Args:
            state: One of TBPF_* constants
        """
        if not self.is_available:
            return
        
        try:
            self.taskbar.SetProgressState(self.hwnd, state)
            self._current_state = state
        except Exception as e:
            print(f"Error setting taskbar states: {e}")
    
    def set_normal(self):
        """Sets normal state (green progress)."""
        self.set_state(self.TBPF_NORMAL)
    
    def set_paused(self):
        """Sets paused state (yellow progress)."""
        self.set_state(self.TBPF_PAUSED)
    
    def set_error(self):
        """Sets error state (red progress)."""
        self.set_state(self.TBPF_ERROR)
    
    def set_indeterminate(self):
        """Sets indeterminate state (animation)."""
        self.set_state(self.TBPF_INDETERMINATE)
    
    def clear(self):
        """Hides the progress bar in the taskbar."""
        self.set_state(self.TBPF_NOPROGRESS)
    
    def update_for_playback(self, is_playing: bool, current: float, total: float):
        """
        Complex update for the audio player.
        
        Args:
            is_playing: True if playing, False if paused
            current: Current position
            total: Total duration
        """
        if not self.is_available:
            return
        
        # Set state depending on playback
        new_state = self.TBPF_NORMAL if is_playing else self.TBPF_PAUSED
        
        if new_state != self._current_state:
            self.set_state(new_state)
        
        # Update progress
        self.set_progress(current, total)


if __name__ == '__main__':
    print(f"COMTYPES_AVAILABLE: {COMTYPES_AVAILABLE}")
    
    if COMTYPES_AVAILABLE:
        tp = TaskbarProgress()
        print(f"Initialized: {tp._initialized}")