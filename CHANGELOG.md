# Changelog

All notable changes to this project will be documented in this file.

## [1.0.5]
- **UX**: Added "Open Directory" option to the video context menu to quickly access files in Explorer.
- **UX**: Added "Reset All Progress" option to the folder context menu to mark all videos in a folder as unwatched.
- **UI**: Standardized context menu iconography:
    - Added volume icons to the audio track submenu and its items.
    - Removed emojis from audio track/menu labels for a professional, system-consistent look.

## [1.0.4]
- **UI**: Streamlined the player control panel by removing secondary action buttons:
    - Removed Reset Zoom, Take Screenshot, and Frame Step buttons.
- **Tools Menu**: Introduced a new "Tools" menu in the main window:
    - Relocated "Take Screenshot" and "Frame Step" actions to this menu.
    - Added status bar confirmation with a checkmark (✓) when taking a screenshot.

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
