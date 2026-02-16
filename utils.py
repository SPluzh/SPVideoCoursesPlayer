"""
Shared utility functions for the SPVideoCoursesPlayer project.
"""

import re
from translator import tr


def natural_sort_key(name):
    """Natural sort key: '1. Intro' < '2. Basic' < '10. Advanced'"""
    def convert(text):
        return int(text) if text.isdigit() else text.lower()
    return [convert(c) for c in re.split(r'(\d+)', str(name))]


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
