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
            "pureref_path": "C:/Program Files/PureRef/PureRef.exe",
            "pureref_filename": "reference.pur",
            "show_pureref_badges": "True",
            "show_pureref_badges_when_missing": "False",
            "enable_debug_file": "False",
            "show_mass_selection": "False",
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
            "interactive": "False",
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
        "TreeLines": {
            "colors": " #ed2a2a, #ed732a, #edbd2a, #d5ed2a, #8ced2a, #43ed2a, #2aed5b, #2aeda4, #2aeded, #2aa4ed, #d52aed, #ed2abd, #ed2a73, #e46767, #e49667, #e4c467, #d4e467, #a5e467, #76e467, #67e486, #67e4b5, #67e4e4, #67b5e4, #6786e4, #7667e4, #a567e4, #d467e4, #e467c4, #e46796, #da580b, #daa60b, #c0da0b, #72da0b, #25da0b, #0bda3f, #0bda8c, #0bdada, #0b8cda, #c00bda, #da0ba6, #da0b58, #e08484, #e0a784, #e0c984, #d4e084, #b2e084, #90e084, #84e09b, #84e0bd, #84e0e0, #84bde0, #849be0, #9084e0, #b284e0, #d484e0, #e084c9, #e084a7,",
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

    def get_pureref_path(self) -> str:
        config = self._read_config()
        return config.get(
            "Paths", "pureref_path", fallback=self.DEFAULTS["General"]["pureref_path"]
        )

    def get_pureref_filename(self) -> str:
        config = self._read_config()
        return config.get(
            "Paths",
            "pureref_filename",
            fallback=self.DEFAULTS["General"]["pureref_filename"],
        )

    def set_pureref_path(self, path: str):
        config = self._read_config()
        if "Paths" not in config:
            config["Paths"] = {}
        config["Paths"]["pureref_path"] = path
        self._write_config(config)

    def set_pureref_filename(self, filename: str):
        config = self._read_config()
        if "Paths" not in config:
            config["Paths"] = {}
        config["Paths"]["pureref_filename"] = filename
        self._write_config(config)

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

    def get_interactive_subtitles(self) -> bool:
        """Returns True if interactive subtitle overlay should be used."""
        config = self._read_config()
        return config.getboolean("Subtitles", "interactive", fallback=False)

    def set_interactive_subtitles(self, enabled: bool):
        """Sets whether interactive subtitle overlay should be used."""
        config = self._read_config()
        if "Subtitles" not in config:
            config["Subtitles"] = {}
        config["Subtitles"]["interactive"] = str(enabled)
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
        if config.has_option("Window", "show_status_bar"):
            try:
                state["show_status_bar"] = config.getboolean("Window", "show_status_bar")
            except (ValueError, TypeError):
                pass
        if config.has_option("Window", "show_tree_lines"):
            try:
                state["show_tree_lines"] = config.getboolean(
                    "Window", "show_tree_lines"
                )
            except (ValueError, TypeError):
                pass
        if config.has_option("General", "show_pureref_badges"):
            try:
                state["show_pureref_badges"] = config.getboolean(
                    "General", "show_pureref_badges"
                )
            except (ValueError, TypeError):
                pass
        if config.has_option("General", "show_pureref_badges_when_missing"):
            try:
                state["show_pureref_badges_when_missing"] = config.getboolean(
                    "General", "show_pureref_badges_when_missing"
                )
            except (ValueError, TypeError):
                pass
        if config.has_option("General", "show_mass_selection"):
            try:
                state["show_mass_selection"] = config.getboolean(
                    "General", "show_mass_selection"
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

    def get_show_status_bar(self) -> bool:
        config = self._read_config()
        return config.getboolean("Window", "show_status_bar", fallback=False)

    def set_show_status_bar(self, value: bool):
        config = self._read_config()
        if "Window" not in config:
            config["Window"] = {}
        config["Window"]["show_status_bar"] = str(value)
        self._write_config(config)

    def get_show_pureref_badges(self) -> bool:
        config = self._read_config()
        return config.getboolean("General", "show_pureref_badges", fallback=True)

    def set_show_pureref_badges(self, value: bool):
        config = self._read_config()
        if "General" not in config:
            config["General"] = {}
        config["General"]["show_pureref_badges"] = str(value)
        self._write_config(config)

    def get_show_pureref_badges_when_missing(self) -> bool:
        config = self._read_config()
        return config.getboolean(
            "General", "show_pureref_badges_when_missing", fallback=False
        )

    def set_show_pureref_badges_when_missing(self, value: bool):
        config = self._read_config()
        if "General" not in config:
            config["General"] = {}
        config["General"]["show_pureref_badges_when_missing"] = str(value)
        self._write_config(config)

    def get_show_mass_selection(self) -> bool:
        config = self._read_config()
        return config.getboolean("General", "show_mass_selection", fallback=False)

    def set_show_mass_selection(self, value: bool):
        config = self._read_config()
        if "General" not in config:
            config["General"] = {}
        config["General"]["show_mass_selection"] = str(value)
        self._write_config(config)

    def get_tree_line_colors(self) -> list:
        """Returns list of hex color strings for tree nesting lines."""
        config = self._read_config()
        colors_str = config.get(
            "TreeLines", "colors", fallback=self.DEFAULTS["TreeLines"]["colors"]
        )
        return [c.strip() for c in colors_str.split(",") if c.strip()]

    def set_tree_line_colors(self, colors: list):
        """Save tree line colors to config."""
        config = self._read_config()
        if "TreeLines" not in config:
            config["TreeLines"] = {}
        config["TreeLines"]["colors"] = ",".join(colors)
        self._write_config(config)

    def get_raw_config(self) -> configparser.ConfigParser:
        """Get the raw ConfigParser for binary path resolution or other direct access."""
        return self._read_config()

    def get_enable_debug_file(self) -> bool:
        """Returns whether debug logging to file is enabled."""
        config = self._read_config()
        return config.getboolean("General", "enable_debug_file", fallback=False)

    def set_enable_debug_file(self, value: bool):
        """Set whether debug logging to file is enabled."""
        config = self._read_config()
        if "General" not in config:
            config["General"] = {}
        config["General"]["enable_debug_file"] = str(value)
        self._write_config(config)
