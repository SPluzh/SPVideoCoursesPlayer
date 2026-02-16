"""
Shared utility functions for the SPVideoCoursesPlayer project.
"""

import re
from pathlib import Path
from translator import tr


def natural_sort_key(name):
    """Natural sort key: '1. Intro' < '2. Basic' < '10. Advanced'"""
    def convert(text):
        return int(text) if text.isdigit() else text.lower()
    name = name.name if isinstance(name, Path) else str(name)
    return [convert(c) for c in re.split(r'(\d+)', name)]


def format_time(seconds):
    """Format seconds into HH:MM:SS or MM:SS string."""
    if not seconds:
        return "00:00"

    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def format_duration(seconds):
    """Alias for format_time, used for displaying durations."""
    return format_time(seconds)


def format_size(bytes_size):
    """Format file size into a human-readable string (KB/MB/GB)."""
    if bytes_size < 1024 * 1024:
        return tr('video_info.size_kb', size=f'{bytes_size/1024:.1f}')
    elif bytes_size < 1024 * 1024 * 1024:
        return tr('video_info.size_mb', size=f'{bytes_size/(1024*1024):.1f}')
    else:
        return tr('video_info.size_gb', size=f'{bytes_size/(1024*1024*1024):.2f}')


def resolve_binary_path(config, key, default_relative):
    """
    Resolve path to binary (ffmpeg, mpv, etc) using config or default.
    Handles relative paths from ROOT_DIR.
    """
    from constants import ROOT_DIR, RESOURCES_DIR
    
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


def setup_encoding():
    """Fix Windows console encoding to utf-8."""
    import sys
    if sys.platform.startswith('win'):
        for stream in (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__):
            if hasattr(stream, 'reconfigure'):
                try:
                    stream.reconfigure(encoding='utf-8')
                except Exception:
                    pass
