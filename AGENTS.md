# Agent Guidelines for SPVideoCoursesPlayer

High-signal instructions for coding agents working on this PyQt6-based Windows video player.

**Tech Stack:** Python 3.10+, PyQt6, libmpv, SQLite, FFmpeg

## Commands

**Run:**
```bash
python main.py
```

**Test translations (must pass before commit):**
```bash
python tests/check_translations.py
```

**Build (use existing spec file):**
```bash
pyinstaller _build_/SPVideoCoursesPlayer.spec
```

**Install:**
```bash
pip install -r requirements.txt
```

## Architecture

**Entry point:** `main.py` (3146 lines) - MainWindow, PiP overlay, all UI wiring  
**Core modules:** `player.py` (2318 lines), `scanner.py` (1515 lines), `library.py` (1416 lines), `database.py` (993 lines)

**Key files:**
- `constants.py` - ROOT_DIR, RESOURCES_DIR, DATA_DIR (import these, never hardcode paths)
- `translator.py` - Global `tr()` function for i18n (en.json, ru.json)
- `config_manager.py` - All settings.ini operations (never read INI directly)
- `database.py` - DatabaseManager with context managers (WAL mode, foreign keys enabled)
- `hotkeys.py` - HotkeyManager using physical scan codes (layout-independent)
- `mpv_handler.py` - MPV DLL setup (must run before importing python-mpv)
- `utils.py` - format_time, natural_sort_key, resolve_binary_path, setup_encoding

**Dialogs:** about, folder_stats, marker, progress, settings, tags, update  
**Popups:** preview, subtitle, tag_filter, volume

**Resources:**
- `resources/bin/` - ffmpeg.exe, ffprobe.exe, libmpv-2.dll (gitignored, auto-downloaded)
- `resources/translations/` - en.json, ru.json (nested JSON, dot notation keys)
- `resources/icons/` - 44 PNG icons
- `data/` - video_courses.db (SQLite), thumbnails (gitignored)

## Critical Setup Requirements

**Startup sequence matters:**
1. `setup_encoding()` - Must run first (fixes Windows UTF-8)
2. Import constants
3. `setup_mpv_dll()` - Must run before importing python-mpv
4. `locale.setlocale(locale.LC_NUMERIC, "C")` - Required for MPV compatibility

**Path handling:**
- ALWAYS use `pathlib.Path` objects, never strings
- Import: `from constants import ROOT_DIR, RESOURCES_DIR, DATA_DIR`
- Join with `/`: `RESOURCES_DIR / 'icons' / 'play.png'`

**MPV safety:**
- Wrap ALL MPV calls in try-except blocks (MPV throws exceptions during playback)

**Translation system:**
- Use `tr('key.subkey')` for all user-facing strings
- Keys use dot notation: `'player.play'`, `'settings.title'`
- Placeholders: `tr('video_info.size_kb', size='123.4')`
- Run `python tests/check_translations.py` before committing

**Database:**
- Always use `DatabaseManager` class
- Context managers: `with self.db.get_connection() as conn:`
- Parameterized queries only (SQL injection prevention)
- WAL mode enabled, foreign keys with CASCADE deletes

**Configuration:**
- All settings via `ConfigManager` class
- Never read settings.ini directly
- Defaults in `ConfigManager.DEFAULTS`

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
4. **CRITICAL**: If adding tooltips or any UI text that should update on language change:
   - Set the text/tooltip in `setup_ui()` using `tr()`
   - ALSO add the same line to the `update_texts()` method in the same class
   - Example: `self.speed_slider.setToolTip(tr("player.tooltip_speed"))` must appear in BOTH places
   - The `update_texts()` method is called by `MainWindow.update_all_texts()` when language changes
   - Without this, the text will only show in the initial language and won't update on language switch

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
- **Main entry**: `main.py` (3146 lines, contains MainWindow, PiPOverlay)
- **Config**: `settings.ini` (gitignored, managed by ConfigManager)
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
