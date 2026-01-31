# Changelog

## [1.0.0] - 2026-01-28

### Added
- **Core functionality**: Modern video player based on libmpv for viewing video courses.
- **Library Management**: Automatic scanning of directories, database tracking of courses, and progress saving.
- **Subtitle Support**: Built-in and external subtitle support with customizable styles (size, colors).
- **Audio Management**: Support for multiple audio tracks with a unified volume/track selection interface.
- **Dependency Management**: Automated downloading and updating of `libmpv` and `FFmpeg` binaries.
- **Modern UI**: Dark-themed interface with custom popups, high-DPI support, and fluid layouts.
- **Localization**: Full support for English and Russian languages.
- **Versioning**: Integrated `version.txt` for centralized version control.

### Changed
- Refactored binary structure: Moved all DLLs and executables to a dedicated `bin/` folder.
- Redesigned "About" dialog: Replaced standard message box with a custom frameless dark-themed window.
- Optimized scan process: Added multi-threaded downloads for FFmpeg and improved console reporting.
- Improved UI responsiveness: Added smart popup positioning to prevent windows from going off-screen.
