# Changelog

All notable changes to this project will be documented in this file.

## [1.0.3]
- **Library**: Added a search bar with real-time filtering:
    - Implemented recursive matching logic (shows parent folders for matching videos and all children for matching folders).
    - Blocked tree signals during search to preserve user-defined folder expansion states in the database.

## [1.0.2]
- **Hotkeys**: Implemented a comprehensive, layout-independent hotkey system:
    - Added support for both English and Russian (Cyrillic) keyboard layouts.
    - Added dedicated hotkeys: `Space` (Play/Pause), `F` (Fullscreen), `M` (Mute), `C` (Subtitles), `S` (Screenshot), `R` (Reset Zoom), `Z` (Hold-to-Zoom).
    - Added precision controls: `<` / `>` (Frame step), `[` / `]` (Zoom).
- **Multimedia Keys**: Implemented truly global support for system multimedia keys (Play/Pause, Next/Prev Track, Stop, Volume Control).
- **UX**: Enabled key auto-repeat for all arrow keys, allowing continuous seeking, volume, and speed adjustment when keys are held down.
- **Control**: Multimedia keys and zoom hotkeys work globally, even when the application is not in focus.


## [1.0.1]
- **Navigation**: Added "Next Video" and "Previous Video" buttons to the player controls.
