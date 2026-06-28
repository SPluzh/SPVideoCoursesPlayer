"""
Shared utility functions for the SPVideoCoursesPlayer project.
"""

import re
from pathlib import Path
from translator import tr


# Language code to display name mapping
LANGUAGE_NAMES = {
    'ru': 'Русский',
    'rus': 'Русский',
    'russian': 'Русский',
    'en': 'English',
    'eng': 'English',
    'english': 'English',
    'uk': 'Українська',
    'ukr': 'Українська',
    'ukrainian': 'Українська',
    'de': 'Deutsch',
    'ger': 'Deutsch',
    'german': 'Deutsch',
    'fr': 'Français',
    'fra': 'Français',
    'french': 'Français',
    'es': 'Español',
    'spa': 'Español',
    'spanish': 'Español',
    'it': 'Italiano',
    'ita': 'Italiano',
    'italian': 'Italiano',
    'ja': '日本語',
    'jpn': '日本語',
    'japanese': '日本語',
    'zh': '中文',
    'chi': '中文',
    'chinese': '中文',
    'pt': 'Português',
    'por': 'Português',
    'portuguese': 'Português',
}


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


def format_audio_track_name(track):
    """
    Format audio track name for user display.
    
    Args:
        track (dict): Audio track info with keys: track_type, language, 
                      audio_file_name, title, stream_index
    
    Returns:
        str: Formatted track name
        
    Examples:
        Embedded track with language: "Встроенная: Русский"
        External track: "Внешняя: audio_ru.mp3"
        Embedded without language: "Встроенная: Дорожка #1"
    """
    track_type = track.get('track_type', 'unknown')
    language = track.get('language', '') or ''
    language = language.lower() if language else ''
    audio_file_name = track.get('audio_file_name', '')
    title = track.get('title', '')
    stream_index = track.get('stream_index')
    
    # Determine track type prefix
    if track_type == 'embedded':
        prefix = tr('audio.embedded')
    elif track_type == 'external':
        prefix = tr('audio.external')
    else:
        prefix = tr('audio.unknown')
    
    # Determine track description
    if track_type == 'external':
        # For external tracks, show filename
        description = audio_file_name if audio_file_name else tr('audio.external_file')
    else:
        # For embedded tracks, try to show language
        if language and language in LANGUAGE_NAMES:
            description = LANGUAGE_NAMES[language]
        elif title:
            description = title
        elif stream_index is not None:
            description = tr('audio.track_number', number=stream_index)
        else:
            description = tr('audio.unknown_track')
    
    return f"{prefix}: {description}"
