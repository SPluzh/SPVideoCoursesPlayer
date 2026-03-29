# Agent Guidelines for SPVideoCoursesPlayer

This document provides coding agents with essential information about the SPVideoCoursesPlayer codebase.

## Project Overview

SPVideoCoursesPlayer is a PyQt6-based desktop video player for Windows, designed for managing and watching downloaded video courses with progress tracking, markers, and advanced audio features.

**Tech Stack:** Python 3.10+, PyQt6, libmpv, SQLite, FFmpeg

## Build & Test Commands

### Running the Application
```bash
python main.py
```

### Running Tests
```bash
# Check translation completeness (verifies all keys exist in en.json and ru.json)
python tests/check_translations.py

# Test taskbar buttons functionality
python tests/test_taskbar_buttons.py

# Run a single test file
python tests/<test_name>.py
```

### Building Executable
```bash
# Build standalone Windows executable with PyInstaller
pyinstaller --name "SP Video Courses Player" --windowed --icon=resources/icons/app.ico main.py

# Output will be in dist/ folder
```

### Installing Dependencies
```bash
pip install -r requirements.txt

# Required: PyQt6, python-mpv, comtypes, mutagen, pyinstaller
```

### Debugging & Utilities
```bash
# Debug scanner functionality
python debug_scanner.py

# Verify refactoring integrity
python verify_refactoring.py

# Check Python version (requires 3.10+, tested with 3.14.2)
python --version
```

## Project Structure

```
SPVideoCoursesPlayer/
├── main.py                 # Application entry point, main window, PiP overlay
├── player.py               # Video player widget with MPV integration
├── library.py              # Video library tree widget and delegates
├── database.py             # DatabaseManager for SQLite operations
├── config_manager.py       # Settings.ini read/write operations
├── scanner.py              # Video scanning and thumbnail generation
├── mpv_handler.py          # MPV DLL setup and video widget
├── translator.py           # i18n translation system (Translator class, tr())
├── constants.py            # Project-wide path constants (ROOT_DIR, RESOURCES_DIR, DATA_DIR)
├── utils.py                # Shared utility functions (format_time, natural_sort_key, etc.)
├── hotkeys.py              # Keyboard shortcut management
├── styles.py               # Qt stylesheet definitions (StyleManager, DARK_STYLE)
├── icon_manager.py         # Icon loading and caching
├── video_item_data.py      # VideoItemData class for library items
├── thumbnail_provider.py   # Thumbnail generation and caching
├── search_utils.py         # Smart search functionality
├── taskbar_progress.py     # Windows taskbar integration
├── *_dialog.py             # Various dialog windows (settings, tags, markers, etc.)
├── *_popup.py              # Popup widgets (subtitles, volume, preview, etc.)
├── update_*.py             # Update utilities (app, ffmpeg, libmpv)
├── resources/              # Icons, translations, binaries, styles
│   ├── translations/       # en.json, ru.json
│   ├── styles/             # dark.qss
│   └── bin/                # ffmpeg.exe, ffprobe.exe, libmpv-2.dll
├── data/                   # SQLite DB, thumbnails (gitignored)
└── tests/                  # Test scripts
```

## Code Style Guidelines

### Imports
- Standard library imports first
- Third-party imports second (PyQt6, etc.)
- Local imports last
- Group related imports together
- Use `from constants import ROOT_DIR, RESOURCES_DIR, DATA_DIR` for paths

Example:
```python
import sys
import os
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal

from constants import ROOT_DIR, RESOURCES_DIR
from utils import format_time, natural_sort_key
from translator import tr
```

### Formatting
- **Indentation:** 4 spaces (no tabs)
- **Line length:** Aim for 100-120 characters, but not strict
- **Quotes:** Single quotes `'` preferred, double quotes `"` for strings with single quotes
- **Docstrings:** Use triple double-quotes `"""` for module/class/function docs

### Naming Conventions
- **Classes:** PascalCase (e.g., `VideoPlayerWidget`, `DatabaseManager`)
- **Functions/Methods:** snake_case (e.g., `format_time`, `get_video_info`)
- **Constants:** UPPER_SNAKE_CASE (e.g., `ROOT_DIR`, `DATA_DIR`)
- **Private methods:** Prefix with underscore (e.g., `_read_config`, `_print_lock`)
- **PyQt signals:** snake_case (e.g., `video_finished`, `position_changed`)

### Type Hints
- Not consistently used throughout the codebase
- Add type hints for new functions when clarity is needed
- Use `Path` from pathlib for file paths

### Error Handling
- Use try-except blocks for file I/O, database operations, and external processes
- Log errors with `logging.error()` including traceback: `logging.error(f"Error: {e}", exc_info=True)`
- Use descriptive error messages with emoji prefixes: `❌ ERROR`, `⚠️ WARNING`, `✅ SUCCESS`, `ℹ️ INFO`
- Fail gracefully in UI code - don't crash the application
- Always wrap MPV operations in try-except blocks (MPV can throw exceptions during playback)

Example:
```python
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except Exception as e:
    logging.error(f"❌ Failed to load {file_path}: {e}", exc_info=True)
    return None
```

### Logging
- Use Python's `logging` module (configured in main.py)
- Levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- Format: `logging.debug(f"Message with {variable}")`
- Comment out verbose debug logs in production code

### Database Operations
- Always use `DatabaseManager` class (database.py)
- Use context managers: `with self.db.get_connection() as conn:`
- Use parameterized queries to prevent SQL injection
- Foreign keys are enabled with CASCADE deletes

### Translation System
- Use `tr('key.subkey')` for all user-facing strings
- Translation keys use dot notation: `'player.play'`, `'settings.title'`
- Support placeholders: `tr('video_info.size_kb', size='123.4')`
- Translation files: `resources/translations/en.json`, `ru.json`

### PyQt6 Patterns
- Inherit from appropriate Qt base classes
- Use signals for inter-widget communication
- Connect signals in `__init__` or dedicated setup methods
- Use `pyqtSignal` for custom signals
- Prefer `QTimer.singleShot()` for delayed execution
- Use `Qt.ConnectionType.QueuedConnection` for thread-safe signals

### Path Handling
- Always use `pathlib.Path` objects, not strings
- Import constants: `from constants import ROOT_DIR, RESOURCES_DIR, DATA_DIR`
- Use `/` operator for path joining: `RESOURCES_DIR / 'icons' / 'play.png'`
- Check existence with `.exists()`, create dirs with `.mkdir(exist_ok=True)`

### Configuration
- All settings managed through `ConfigManager` class
- Settings stored in `resources/settings.ini` (gitignored)
- Use `config.get_*()` methods, never read INI directly
- Defaults defined in `ConfigManager.DEFAULTS`

### Threading
- Use `ThreadPoolExecutor` for concurrent operations (scanner.py)
- Use `threading.Lock()` for shared resource protection
- Use `QThread` for long-running Qt operations
- Emit signals from worker threads to update UI

## Common Patterns

### Adding a New Dialog
1. Create `*_dialog.py` file
2. Inherit from `QDialog`
3. Use `tr()` for all text
4. Apply dark theme: `self.setStyleSheet(DARK_STYLE)`
5. Import and instantiate in main.py

### Adding a New Database Table
1. Add CREATE TABLE in `database.py` → `init_database()`
2. Add indices if needed
3. Create getter/setter methods in `DatabaseManager`
4. Update scanner.py if table needs population during scan

### Adding a Translation Key
1. Add to `resources/translations/en.json` and `ru.json`
2. Use nested structure: `{"player": {"play": "Play"}}`
3. Run `python tests/check_translations.py` to verify

## Important Notes

- **Python Version:** Requires Python 3.10+ (tested with 3.14.2)
- **Windows-only:** Uses comtypes for taskbar integration
- **MPV required:** libmpv-2.dll must be in resources/bin/
- **FFmpeg required:** For thumbnail generation and video analysis
- **Encoding:** UTF-8 everywhere, `setup_encoding()` called at startup
- **Locale:** `locale.setlocale(locale.LC_NUMERIC, 'C')` for MPV compatibility
- **No linting:** Project doesn't use flake8/pylint/black - follow existing style
- **No unit tests:** Only utility test scripts in tests/
- **High DPI:** Application supports High DPI displays with Qt's PassThrough scaling policy

## Debugging Tips

- Enable debug logging: Already set to `logging.DEBUG` in main.py
- Check `data/video_courses.db` with SQLite browser
- Verify binary paths in settings.ini
- Test translations with `tests/check_translations.py`
- Use `logging.debug()` liberally, comment out before commit

## External Dependencies

- **PyQt6:** GUI framework
- **python-mpv:** MPV player bindings
- **comtypes:** Windows COM for taskbar features
- **mutagen:** Audio metadata reading
- **pyinstaller:** Building standalone executable

## Development Agreements & Best Practices

1. **Path Handling**: ALWAYS use `pathlib.Path` objects, never strings
2. **Hotkey Centralization**: Route all keyboard events through `HotkeyManager` (uses physical scan codes for layout independence)
3. **Focus Suppression**: Standardize `setFocusPolicy(Qt.FocusPolicy.NoFocus)` on buttons/sliders
4. **MPV Safety**: Wrap all MPV calls in try/except blocks
5. **Config & Settings**: Add new user-facing toggles to `settings.ini` with defaults in `ConfigManager.DEFAULTS`
6. **Signal Management**: Use `blockSignals(True)` during filtering/batch operations to prevent accidental DB writes
7. **Icon Loading**: In dialogs, call `load_icons()` BEFORE `setup_ui()` to avoid crashes
8. **Window State**: When restoring QSplitter state, explicitly call `setCollapsible()` AFTER `restoreState()` to enforce desired behavior

## When Making Changes

1. Maintain existing code style and patterns
2. Use `tr()` for any user-visible text
3. Add error handling with logging
4. Test with both English and Russian translations
5. Verify database migrations if schema changes
6. Update CHANGELOG.md for significant changes
7. Don't commit data/, settings.ini, or binaries

## Known Pitfalls

- **MPV Threading**: Background threads must not touch the UI - use signals for thread-safe communication
- **CSS Overrides**: Global styles (DARK_STYLE) can interfere with small UI elements - test thoroughly
- **Menu Initialization**: Define `QAction` objects before usage to avoid crashes
- **Preview Performance**: FFmpeg frame extraction via `QProcess` has unavoidable delay but is stable
- **Splitter State**: `restoreState()` overwrites code-level settings - always re-apply `setCollapsible()` after restore

## Quick Reference

### File Locations
- **Main entry**: `main.py` (3000+ lines, contains MainWindow, PiPOverlay)
- **Config**: `resources/settings.ini` (gitignored, managed by ConfigManager)
- **Database**: `data/video_courses.db` (SQLite, WAL mode enabled)
- **Translations**: `resources/translations/en.json`, `ru.json`
- **Binaries**: `resources/bin/` (ffmpeg.exe, ffprobe.exe, libmpv-2.dll)

### Key Classes
- `MainWindow` (main.py): Main application window
- `VideoPlayerWidget` (player.py): MPV-based video player
- `HoverTreeWidget` (library.py): Video library tree view
- `DatabaseManager` (database.py): All DB operations
- `ConfigManager` (config_manager.py): Settings.ini management
- `VideoScanner` (scanner.py): Video scanning and thumbnail generation
- `HotkeyManager` (hotkeys.py): Centralized keyboard handling

### Common Operations
- **Get config value**: `config.get_language()`, `config.get_video_extensions()`
- **Set config value**: `config.set_language('en')`, `config.save()`
- **DB query**: `with self.db.get_connection() as conn: cursor = conn.cursor(); ...`
- **Translate text**: `tr('player.play')`, `tr('video_info.size_kb', size='123.4')`
- **Load icon**: `QIcon(str(RESOURCES_DIR / 'icons' / 'play.png'))`
