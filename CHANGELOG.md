# Changelog

All notable changes to this project will be documented in this file.

## [1.1.3]
- **Tags**: Improved tag management in the context menu:
    - Added "Tags" submenu to quickly add or remove tags from videos.
    - Context menu items now display the tag's color.
- **Favorites**: Enhanced favorite management:
    - Added valid icons for "Add to Favorites" and "Remove from Favorites".

## [1.1.2]
- **Favorites**: Added "Add to Favorites" functionality:
    - Toggle favorite status via context menu.
    - Added Heart icon (♥) to the top-left of video thumbnails.
- **Tags**: Implemented a comprehensive tagging system:
    - New **Tags Dialog** to create, assign, and delete custom tags with colors.
    - Tags are displayed as colored badges on video items.
    - Updated Search to support filtering by tag names.

## [1.1.1]
- **Library**: Added marker counts to the video course list:
    - Displays the number of markers next to video resolution and file size with a 🔖 icon.

## [1.1.0]
- **Markers**: Introduced a full-featured video marker system:
    - **Visual Navigation**: Added a floating Marker Gallery (`G`) with screenshots and high-legibility time badges.
    - **Customization**: Added support for 12 distinct marker colors.
    - **Management**: Full control with the new Marker Dialog: edit labels, adjust time with precision (+/- buttons), and manual time entry.
    - **Quick Actions**: Right-click markers in the slider or gallery to Edit or Delete instantly.


## [1.0.9]
- **UI**: Enhanced the **Settings Dialog** with comprehensive icon support:
    - Added custom icons for **Add**, **Edit**, **Remove**, **Scan**, **Save**, and **Clear Data** buttons.
    - Implemented status icons (**Check**, **Fail**, **Upload**, **Download**) for library path validation and dependency checks (FFmpeg/Libmpv).

## [1.0.8]
- **UI**: Fixed window splitter behavior so the library panel is collapsible while the player panel behaves correctly.

## [1.0.7]
- **Feature**: Added Seek Slider Hover Preview:
    - Moves mouse over the timeline to see a timestamp and video thumbnail from that moment.
    - Uses optimized FFmpeg background processing for fast updates.
    - Styled with a "plaque" (rounded dark background) for the timestamp for better readability.
    - Popup stays vertically anchored to the slider to prevent jitter.

## [1.0.6]
- **UI**: Refined status bar flexibility and styling

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
