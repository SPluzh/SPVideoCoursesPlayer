"""
Configuration manager for the SPVideoCoursesPlayer project.

Centralizes all settings.ini read/write operations. The VideoCourseBrowser
delegates config I/O to this class, keeping its own code focused on UI logic.
"""

import os
import configparser
from pathlib import Path


class ConfigManager:
    """Manages reading and writing of application settings from settings.ini."""

    # Default values for all sections
    DEFAULTS = {
        "General": {
            "language": "en",
            "show_preview_popup": "True",
            "check_updates_on_start": "True",
            "skip_version": "",
            "autoplay_on_next": "True",
            "autoplay_on_prev": "True",
            "show_osd": "True",
        },
        "Paths": {
            "paths": "",
            "thumbnails_dir": "data/video_thumbnails",
            "ffmpeg_path": "resources/bin/ffmpeg.exe",
            "ffprobe_path": "resources/bin/ffprobe.exe",
            "libmpv_path": "resources/bin/libmpv-2.dll",
        },
        "Display": {
            "window_width": "1400",
            "window_height": "800",
            "video_row_height": "110",
            "folder_row_height": "70",
        },
        "Thumbnails": {
            "render_width": "320",
            "render_height": "180",
            "display_width": "160",
            "display_height": "90",
            "count": "12",
            "quality": "2",
            "regenerate": "False",
            "max_workers": "8",
            "animation_interval": "400",
        },
        "Video": {
            "extensions": ".mp4,.mkv,.avi,.mov,.wmv,.flv,.webm,.m4v,.mpg,.mpeg,.3gp,.ts",
            "folder_image_extensions": ".jpg,.jpeg,.png,.webp,.bmp",
        },
        "Subtitles": {
            "text_color": "#FFFFFF",
            "outline_color": "#000000",
            "font_scale": "1.0",
            "extensions": ".srt,.ass,.ssa,.sub,.idx,.vtt,.sup,.stl,.smi,.txt",
        },
        "Audio": {
            "extensions": ".mp3,.aac,.ac3,.dts,.flac,.wav,.ogg,.m4a,.wma,.eac3,.opus,.mka",
        },
        "Performance": {
            "max_workers": "8",
            "thumbnail_workers": "4",
            "ffmpeg_timeout": "15",
        },
        "Folder_Style": {
            "icon_size": "24",
            "row_height": "35",
            "font_bold": "True",
            "font_size": "10",
            "text_color": "0,100,180",
            "bg_color": "230,240,255",
        },
    }

    def __init__(self, config_file: Path, root_dir: Path, data_dir: Path):
        self.config_file = config_file
        self.root_dir = root_dir
        self.data_dir = data_dir

    def _read_config(self) -> configparser.ConfigParser:
        """Read and return the current config. Creates defaults if file doesn't exist."""
        if not self.config_file.exists():
            self._create_default_settings()

        config = configparser.ConfigParser()
        config.read(self.config_file, encoding="utf-8")
        return config

    def _write_config(self, config: configparser.ConfigParser):
        """Write config to the INI file."""
        with open(self.config_file, "w", encoding="utf-8") as f:
            config.write(f)

    def _create_default_settings(self):
        """Create the settings.ini file with default values."""
        config = configparser.ConfigParser()
        for section, values in self.DEFAULTS.items():
            config[section] = values
        self._write_config(config)

    # --- General settings ---

    def get_language(self) -> str:
        config = self._read_config()
        return config.get("General", "language", fallback="ru")

    def set_language(self, lang_code: str):
        config = self._read_config()
        if "General" not in config:
            config["General"] = {}
        config["General"]["language"] = lang_code
        self._write_config(config)

    def get_show_preview_popup(self) -> bool:
        config = self._read_config()
        return config.getboolean("General", "show_preview_popup", fallback=True)

    def get_autoplay_on_next(self) -> bool:
        config = self._read_config()
        return config.getboolean("General", "autoplay_on_next", fallback=True)

    def get_autoplay_on_prev(self) -> bool:
        config = self._read_config()
        return config.getboolean("General", "autoplay_on_prev", fallback=True)

    def get_show_osd(self) -> bool:
        config = self._read_config()
        return config.getboolean("General", "show_osd", fallback=True)

    def set_show_osd(self, value: bool):
        config = self._read_config()
        if "General" not in config:
            config["General"] = {}
        config["General"]["show_osd"] = str(value)
        self._write_config(config)

    def get_fav_filter_active(self) -> bool:
        config = self._read_config()
        return config.getboolean("General", "fav_filter_active", fallback=False)

    def get_tag_filter_active(self) -> bool:
        config = self._read_config()
        return config.getboolean("General", "tag_filter_active", fallback=False)

    def get_selected_tag_ids(self) -> set:
        config = self._read_config()
        tag_ids_str = config.get("General", "selected_tag_ids", fallback="")
        if tag_ids_str:
            try:
                return set(map(int, tag_ids_str.split(",")))
            except (ValueError, TypeError):
                return set()
        return set()

    # --- Update settings ---

    def get_check_updates_on_start(self) -> bool:
        config = self._read_config()
        return config.getboolean("General", "check_updates_on_start", fallback=True)

    def set_check_updates_on_start(self, value: bool):
        config = self._read_config()
        if "General" not in config:
            config["General"] = {}
        config["General"]["check_updates_on_start"] = str(value)
        self._write_config(config)

    def set_autoplay_on_next(self, value: bool):
        config = self._read_config()
        if "General" not in config:
            config["General"] = {}
        config["General"]["autoplay_on_next"] = str(value)
        self._write_config(config)

    def set_autoplay_on_prev(self, value: bool):
        config = self._read_config()
        if "General" not in config:
            config["General"] = {}
        config["General"]["autoplay_on_prev"] = str(value)
        self._write_config(config)

    def get_skip_version(self) -> str:
        config = self._read_config()
        return config.get("General", "skip_version", fallback="")

    def set_skip_version(self, version: str):
        config = self._read_config()
        if "General" not in config:
            config["General"] = {}
        config["General"]["skip_version"] = version
        self._write_config(config)

    # --- Path settings ---

    def get_library_paths(self) -> str:
        config = self._read_config()
        return config.get("Paths", "paths", fallback="")

    def get_excluded_library_paths(self) -> set:
        config = self._read_config()
        excluded_str = config.get("Paths", "excluded_paths", fallback="")
        return {
            os.path.normpath(p.strip()) for p in excluded_str.split(";") if p.strip()
        }

    def get_thumbnails_dir(self) -> Path:
        config = self._read_config()
        default = str(self.data_dir / "video_thumbnails")
        thumbnails_dir = self.data_dir / "video_thumbnails"
        if config.has_section("Paths"):
            thumbnails_dir = Path(
                config.get("Paths", "thumbnails_dir", fallback=default)
            )
            if not thumbnails_dir.is_absolute():
                thumbnails_dir = self.root_dir / thumbnails_dir
        return thumbnails_dir

    # --- Display settings ---

    def get_window_width(self) -> int:
        config = self._read_config()
        return config.getint("Display", "window_width", fallback=1400)

    def get_window_height(self) -> int:
        config = self._read_config()
        return config.getint("Display", "window_height", fallback=800)

    def get_video_row_height(self) -> int:
        config = self._read_config()
        return config.getint("Display", "video_row_height", fallback=110)

    def get_folder_row_height(self) -> int:
        config = self._read_config()
        return config.getint("Display", "folder_row_height", fallback=70)

    # --- Folder Style settings ---

    def get_folder_icon_size(self) -> int:
        config = self._read_config()
        return config.getint("Folder_Style", "icon_size", fallback=24)

    def get_folder_style_row_height(self) -> int:
        config = self._read_config()
        return config.getint("Folder_Style", "row_height", fallback=35)

    # --- Thumbnail settings ---

    def get_display_width(self) -> int:
        config = self._read_config()
        return config.getint("Thumbnails", "display_width", fallback=160)

    def get_display_height(self) -> int:
        config = self._read_config()
        return config.getint("Thumbnails", "display_height", fallback=90)

    def get_animation_interval(self) -> int:
        config = self._read_config()
        return config.getint("Thumbnails", "animation_interval", fallback=400)

    def get_render_width(self) -> int:
        config = self._read_config()
        return config.getint("Thumbnails", "render_width", fallback=320)

    def get_render_height(self) -> int:
        config = self._read_config()
        return config.getint("Thumbnails", "render_height", fallback=180)

    def get_thumbnail_count(self) -> int:
        config = self._read_config()
        return config.getint("Thumbnails", "count", fallback=12)

    def get_thumbnail_quality(self) -> int:
        config = self._read_config()
        return config.getint("Thumbnails", "quality", fallback=2)

    def get_regenerate_thumbnails(self) -> bool:
        config = self._read_config()
        return config.getboolean("Thumbnails", "regenerate", fallback=False)

    # --- Performance settings ---

    def get_max_workers(self) -> int:
        config = self._read_config()
        return config.getint("Performance", "max_workers", fallback=8)

    def get_thumbnail_workers(self) -> int:
        config = self._read_config()
        return config.getint("Performance", "thumbnail_workers", fallback=4)

    def get_ffmpeg_timeout(self) -> int:
        config = self._read_config()
        return config.getint("Performance", "ffmpeg_timeout", fallback=5)

    # --- Video settings ---

    def get_folder_image_extensions(self) -> set:
        config = self._read_config()
        folder_exts = config.get(
            "Video", "folder_image_extensions", fallback=".jpg,.jpeg,.png,.webp,.bmp"
        )
        return {e.strip().lower() for e in folder_exts.split(",")}

    def get_video_extensions(self) -> set:
        config = self._read_config()
        exts = config.get(
            "Video", "extensions", fallback=self.DEFAULTS["Video"]["extensions"]
        )
        return {e.strip().lower() for e in exts.split(",")}

    def get_audio_extensions(self) -> set:
        config = self._read_config()
        exts = config.get(
            "Audio", "extensions", fallback=self.DEFAULTS["Audio"]["extensions"]
        )
        return {e.strip().lower() for e in exts.split(",")}

    def get_subtitle_extensions(self) -> set:
        config = self._read_config()
        exts = config.get(
            "Subtitles", "extensions", fallback=self.DEFAULTS["Subtitles"]["extensions"]
        )
        return {e.strip().lower() for e in exts.split(",")}

    # --- Subtitle settings ---

    def get_subtitle_settings(self) -> tuple:
        """Returns (text_color, outline_color, font_scale)."""
        config = self._read_config()
        text_color = config.get("Subtitles", "text_color", fallback="#FFFFFF")
        outline_color = config.get("Subtitles", "outline_color", fallback="#000000")
        font_scale = config.getfloat("Subtitles", "font_scale", fallback=1.0)
        return text_color, outline_color, font_scale

    def save_subtitle_setting(self, property_name: str, value):
        """Save a single subtitle style setting to ini file."""
        config = self._read_config()
        if "Subtitles" not in config:
            config["Subtitles"] = {}

        if property_name == "sub-color":
            config["Subtitles"]["text_color"] = value
        elif property_name == "sub-border-color":
            config["Subtitles"]["outline_color"] = value
        elif property_name == "sub-scale":
            config["Subtitles"]["font_scale"] = f"{value:.2f}"

        self._write_config(config)

    # --- Window state ---

    def get_window_state(self) -> dict:
        """Read all window state data from config. Returns a dict with optional keys."""
        config = self._read_config()
        state = {}

        if config.has_option("Window", "geometry"):
            state["geometry"] = config.get("Window", "geometry")
        if config.has_option("Window", "is_maximized"):
            try:
                state["is_maximized"] = config.getboolean("Window", "is_maximized")
            except (ValueError, TypeError):
                pass
        if config.has_option("Window", "splitter_state"):
            state["splitter_state"] = config.get("Window", "splitter_state")
        if config.has_option("Window", "playback_speed"):
            state["playback_speed"] = config.get("Window", "playback_speed")
        if config.has_option("Window", "pip_geometry"):
            state["pip_geometry"] = config.get("Window", "pip_geometry")
        if config.has_option("Window", "last_video"):
            state["last_video"] = config.get("Window", "last_video")
        if config.has_option("Window", "show_markers"):
            try:
                state["show_markers"] = config.getboolean("Window", "show_markers")
            except (ValueError, TypeError):
                pass
        if config.has_option("Window", "show_library"):
            try:
                state["show_library"] = config.getboolean("Window", "show_library")
            except (ValueError, TypeError):
                pass
        if config.has_option("Window", "show_tree_lines"):
            try:
                state["show_tree_lines"] = config.getboolean(
                    "Window", "show_tree_lines"
                )
            except (ValueError, TypeError):
                pass

        return state

    def save_window_state(self, state: dict):
        """Save window state data to config. state is a dict with string values."""
        config = self._read_config()
        if "Window" not in config:
            config["Window"] = {}

        for key, value in state.items():
            config["Window"][key] = str(value)

        self._write_config(config)

    def save_filter_state(
        self, fav_active: bool, tag_active: bool, selected_tag_ids: set
    ):
        """Save filter state (favorites, tags) to General section."""
        config = self._read_config()
        if "General" not in config:
            config["General"] = {}
        config["General"]["fav_filter_active"] = str(fav_active)
        config["General"]["tag_filter_active"] = str(tag_active)
        config["General"]["selected_tag_ids"] = ",".join(map(str, selected_tag_ids))
        self._write_config(config)

    def set_library_paths(self, paths: list[str]):
        config = self._read_config()
        if "Paths" not in config:
            config["Paths"] = {}
        config["Paths"]["paths"] = ";".join(paths)
        self._write_config(config)

    def set_excluded_library_paths(self, paths: list[str]):
        config = self._read_config()
        if "Paths" not in config:
            config["Paths"] = {}
        config["Paths"]["excluded_paths"] = ";".join(paths)
        self._write_config(config)

    def get_ffmpeg_path(self) -> Path:
        config = self._read_config()
        # Logic similar to resolve_binary_path but using self.root_dir
        path_str = config.get(
            "Paths", "ffmpeg_path", fallback="resources/bin/ffmpeg.exe"
        )
        path = Path(path_str)
        if not path.is_absolute():
            path = self.root_dir / path
        return path

    def get_ffprobe_path(self) -> Path:
        config = self._read_config()
        path_str = config.get(
            "Paths", "ffprobe_path", fallback="resources/bin/ffprobe.exe"
        )
        path = Path(path_str)
        if not path.is_absolute():
            path = self.root_dir / path
        return path

    def get_libmpv_path(self) -> Path:
        config = self._read_config()
        path_str = config.get(
            "Paths", "libmpv_path", fallback="resources/bin/libmpv-2.dll"
        )
        path = Path(path_str)
        if not path.is_absolute():
            path = self.root_dir / path
        return path

    def get_show_tree_lines(self) -> bool:
        config = self._read_config()
        return config.getboolean("Window", "show_tree_lines", fallback=True)

    def set_show_tree_lines(self, value: bool):
        config = self._read_config()
        if "Window" not in config:
            config["Window"] = {}
        config["Window"]["show_tree_lines"] = str(value)
        self._write_config(config)

    def get_raw_config(self) -> configparser.ConfigParser:
        """Get the raw ConfigParser for binary path resolution or other direct access."""
        return self._read_config()
