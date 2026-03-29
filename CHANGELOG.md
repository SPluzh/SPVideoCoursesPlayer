# Changelog

All notable changes to this project will be documented in this file.

## [1.4.5]
- **Always On Top**: Added a toggle to keep the player window above all other windows:
    - **Hotkey**: Press `T` to toggle "Always on Top" mode.
- **UI Refinement**: Improved menu organization and information:
    - Moved **Picture-in-Picture (PiP)** toggle from the "Tools" to the "View" menu for better grouping.

## [1.4.4]
- **Library**: Added "Locate Active Video" feature:
    - **Hotkey**: Press `L` to instantly scroll the library to the currently playing video.
    - **Navigation**: Automatically expands parent folders and reveals hidden video items.

## [1.4.3]
- **Library**: Added a toggle for the library panel visibility:
    - **Hotkey**: Implemented `Ctrl + L` to show or hide the library panel instantly.
    - **Menu**: Added a checkable "Show Library" item in the 

## [1.4.2]
- **Zoom OSD**: Added on-screen display notification for zoom level changes:
    - **Visual Feedback**: Shows current zoom percentage (e.g., "Zoom: 150%" / "Масштаб: 150%") in the top-left corner of the video.

## [1.4.1]
    - **Smoothing**: Enabled antialiasing for perfectly round and smooth dots.
    - **Stability**: Implemented float-based positioning (QRectF) to eliminate vertical jitter and "jumping" when switching frames during hover.

## [1.4.0]
- **Display**: Implemented comprehensive **High DPI support** for sharp rendering on all displays (4K, laptops with scaling):
    - **High DPI Scaling**: Enabled native Qt scaling with `PassThrough` policy for perfect rendering on fractional scales (e.g. 125%, 150%).
    - **Layout Precision**: Refined image centering and sizing logic to ensure sharp, pixel-perfect alignment in the library view.

## [1.3.9]
- **Performance**: Extensive memory optimization to reduce footprint
    - **LRU Cache**: Implemented LRU caching for video thumbnails (200 items) and hover previews (50 items), preventing unbounded RAM growth.
    - **Pre-scaling**: Thumbnails are now scaled to display size upon loading, significantly reducing memory usage per image.
    - **Lazy MPV**: The preview player instance is now initialized only on first hover and automatically destroyed after 10 seconds of inactivity to free resources.
    - **Resource Limit**: Reduced the MPV demuxer buffer for preview player to minimize memory consumption.

## [1.3.8]
- **Library UI**: Overhauled folder nesting visualization:
    - **Nesting Lines**: Added vertical colored indicator lines to clearly show folder depth.
    - **Path-based Coloring**: Folders are now assigned stable, unique colors based on their file paths, making it easy to track a single folder's hierarchy visually.
    - **Folder Endings**: The indicator lines now form a visual corner (L-bracket) when reaching the last item in a folder.

## [1.3.7]
- **UI Enhancements**:
    - **Dynamic Progress Labels**: Added color-coding for time labels on video thumbnails (Green for watched, Yellow for in-progress, Black for new).
    - **Cleaned Layout**: Removed redundant progress text lines under video titles to streamline the library view.

## [1.3.6]
- **Autoplay Settings**: Added options to automatically start playback when switching to the next or previous video.

## [1.3.5]
- **Folder Images**: Fixed cropping of folder cover images to correctly preserve aspect ratio (16:9).
- **Progress Auto-Update**: Progress bars for videos and folders now update automatically every 30 seconds during playback.
- **Video Titles**: Increased the text wrapping limit for video titles to 3 lines.

## [1.3.4]
- **Taskbar Integration**: Implemented Windows taskbar thumbnail buttons for playback control:
    - Added 5 interactive buttons: Previous Video, Rewind 10s, Play/Pause, Forward 10s, and Next Video.
    - Added real-time synchronization of the Play/Pause button icon with the player state.
    - Implemented a native event filter to handle button clicks directly from the taskbar preview.

## [1.3.3]
- **Search**: Implemented a robust fuzzy search system:
    - **Fuzzy Matching**: Matches queries even with typos using SequenceMatcher.
    - **Transliteration**: Automatically converts queries between English and Russian layouts (e.g. "ghbdtn" -> "привет").
    - **Word-level Matching**: Matches queries independently of word order.
    - **Integration**: Works seamlessly across library items, tags, and markers.

## [1.3.2]
- **Library**:
    - Markers are now displayed as a list under each video.
    - Added a button to toggle marker visibility.
    - Added search by markers.

## [1.3.1]
- **UI**: Added a **hotkey hint list** to the "About" dialog.

## [1.3.0]
- **Auto-Update**: Implemented a comprehensive auto-update system using GitHub Releases

## [1.2.7]
- **Availability Tracking**: Implemented smart file availability tracking:
    - **Scanner**: Updated scan logic to mark missing videos/folders as unavailable instead of removing them.
    - **Library**: Filtered view to show only available items, preserving play history and tags for temporarily missing files.

## [1.2.6]
- **Audio Enhancements**: Integrated professional audio processing tools:
    - **Denoise**: Added Noise Reduction with Standard and AI (`arnndn`) modes.
    - **Compressor**: Added Dynamic Range Compressor to normalize volume levels.
    - **De-esser**: Added specialized filter for reducing harsh sibilance.
    - **Mono Mode**: Added channel mixing to mono for single-speaker content.
    - **Audio Delay**: Implemented precision sync adjustment (+/- 50ms) with auto-repeat.
- **UI/OSD**: Improved visual feedback:
    - Added localized OSD notifications for audio tools and delay changes.

## [1.2.5]
- **Library Filter**: Introduced dedicated filter buttons for **Favorites** and **Tags** in the search area.
- **Tags Filter**: Added a versatile multi-tag filtering system (OR logic) with persistent state and selection popup.

## [1.2.4]
- **Settings**: Implemented **Inactive Source** support:
    - **Control**: Added checkboxes to library paths to easily toggle them as active or inactive.
    - **Behavior**: Inactive sources are hidden from the library view and excluded from scans, but their data is preserved.

## [1.2.3]
- **Folder UI**: Major visual overhaul for course folders:
    - **Statistics**: Displays video count, total duration, watched duration, and percentage (e.g., "5 videos • 00:10:00 / 01:00:00 (16%)").
    - **Progress Bar**: Added a green progress bar below folder icons to visualize course completion.

## [1.2.2]
- **Feature**: Added **Course Statistics** window:
    - **Info**: Displays detailed course information (video counts, time statistics).

## [1.2.1]
- **Performance**: Completely rewrote preview thumbnails using `libmpv` (replaced FFmpeg QProcess):
    - **Instant Previews**: Reduced thumbnail generation latency from ~150ms to ~30ms.
    - **Optimization**: Implemented background MPV instance with keyframe seeking for immediate response.
    - **Responsiveness**: Significantly reduced debounce timer (25ms → 15ms) and post-seek delay.

## [1.2.0]
- **Picture-in-Picture (PiP)**: Implemented a robust floating video window mode:
    - **Toggle**: Switch to PiP via hotkey `P` (works in English and Russian layouts). Button removed from main player controls.
    - **Window Control**: 
        - Resizable with aspect ratio enforcement (16:9).
        - Draggable by right-click anywhere on the window.
        - Close button appears on hover.
    
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
