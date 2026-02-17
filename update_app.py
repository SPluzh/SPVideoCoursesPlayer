"""
Auto-update module for SPVideoCoursesPlayer.

Checks GitHub Releases for new versions, downloads the update zip,
creates a hidden _updater.bat script to replace files and restart.
"""

import os
import sys
import json
import urllib.request
import subprocess
from pathlib import Path

from constants import ROOT_DIR, RESOURCES_DIR


GITHUB_API_URL = "https://api.github.com/repos/SPluzh/SPVideoCoursesPlayer/releases/latest"
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# Files/dirs that must NOT be overwritten during update
PROTECTED_ITEMS = {
    'settings.ini',
    'data',
    'ffmpeg.exe',
    'ffprobe.exe',
    'libmpv-2.dll',
    'libmpv.version',
    '_updater.bat',
    '_update_download.zip',
    '_update_temp',
}


def get_current_version() -> str:
    """Read current app version from resources/version.txt."""
    try:
        version_file = RESOURCES_DIR / "version.txt"
        if version_file.exists():
            return version_file.read_text("utf-8").strip()
    except Exception:
        pass
    return "0.0.0"


def _parse_version(v: str) -> tuple:
    """Parse version string like '1.2.7' or 'v1.2.7' into tuple of ints."""
    v = v.strip().lstrip('v')
    try:
        return tuple(int(x) for x in v.split('.'))
    except (ValueError, TypeError):
        return (0, 0, 0)


def compare_versions(local: str, remote: str) -> bool:
    """Return True if remote version is newer than local."""
    return _parse_version(remote) > _parse_version(local)


def get_latest_release() -> dict | None:
    """
    Fetch latest release info from GitHub API.
    Returns dict with keys: tag, url, changelog, or None on error.
    """
    try:
        req = urllib.request.Request(GITHUB_API_URL, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.load(response)

        tag = data.get('tag_name', '')
        body = data.get('body', '')
        assets = data.get('assets', [])

        download_url = None
        for asset in assets:
            name = asset.get('name', '')
            if name.endswith('.zip'):
                download_url = asset.get('browser_download_url')
                break

        if tag and download_url:
            return {
                'tag': tag,
                'url': download_url,
                'changelog': body,
            }
    except Exception as e:
        print(f"Error checking for updates: {e}")
    return None


def check_for_update() -> dict | None:
    """
    Check if an update is available.
    Returns dict {current, latest, url, changelog} or None.
    """
    current = get_current_version()
    release = get_latest_release()
    if not release:
        return None

    latest = release['tag'].lstrip('v')
    if compare_versions(current, latest):
        return {
            'current': current,
            'latest': latest,
            'url': release['url'],
            'changelog': release['changelog'],
        }
    return None


def download_update(download_url: str) -> Path:
    """
    Download update zip to ROOT_DIR/_update_download.zip.
    Uses Downloader from update_libmpv for multi-threaded download.
    Returns path to downloaded file.
    """
    target = ROOT_DIR / '_update_download.zip'

    try:
        from update_libmpv import Downloader
        downloader = Downloader(download_url, str(target))
        downloader.download()
    except ImportError:
        # Fallback: simple download
        print(f"Downloading update from {download_url}...")
        req = urllib.request.Request(download_url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=300) as response:
            with open(target, 'wb') as f:
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
        print("Download complete.")

    if not target.exists():
        raise RuntimeError("Download failed: file not found")
    return target


def create_updater_script(zip_path: Path, new_version: str) -> Path:
    """
    Generate _updater.bat that waits for app exit, extracts zip,
    copies files (skipping protected ones), restarts app, self-deletes.
    """
    bat_path = ROOT_DIR / '_updater.bat'
    exe_name = _get_exe_name()
    current_pid = os.getpid()

    # Build exclusion filter for findstr
    # Each protected item on its own line for findstr matching
    protected_patterns = '\\n'.join([
        f"\\\\{item}" if not item.endswith(('.exe', '.dll', '.ini', '.version'))
        else f"\\\\{item}"
        for item in PROTECTED_ITEMS
    ])

    script = f"""@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

set "APP_DIR=%~dp0"
set "EXE_NAME={exe_name}"
set "PID={current_pid}"
set "ZIP_PATH={zip_path}"
set "TEMP_DIR=%APP_DIR%_update_temp"
set "VERSION={new_version}"

REM --- Wait for application to exit ---
:wait_loop
tasklist /FI "PID eq %PID%" 2>nul | find "%PID%" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

REM --- Small delay for file handles to release ---
timeout /t 2 /nobreak >nul

REM --- Extract zip to temp directory ---
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%" 2>nul
powershell -Command "Expand-Archive -Path '%ZIP_PATH%' -DestinationPath '%TEMP_DIR%' -Force"

REM --- Find the actual content root (may be nested in a subfolder) ---
set "SOURCE_DIR=%TEMP_DIR%"

REM Check if zip contains a single top-level folder
set "SUBFOLDER_COUNT=0"
set "LAST_SUBFOLDER="
for /d %%D in ("%TEMP_DIR%\\*") do (
    set /a SUBFOLDER_COUNT+=1
    set "LAST_SUBFOLDER=%%D"
)

REM If exactly one subfolder and no files at root, use it as source
set "FILE_COUNT=0"
for %%F in ("%TEMP_DIR%\\*.*") do set /a FILE_COUNT+=1

if %SUBFOLDER_COUNT% equ 1 if %FILE_COUNT% equ 0 (
    set "SOURCE_DIR=!LAST_SUBFOLDER!"
)

REM --- Copy files, skipping protected items ---
xcopy "!SOURCE_DIR!\\*" "%APP_DIR%" /e /y /i /exclude:%~f0.exc >nul 2>&1

REM If xcopy exclude doesn't work well, use robocopy as fallback
robocopy "!SOURCE_DIR!" "%APP_DIR%" /e /xf settings.ini ffmpeg.exe ffprobe.exe libmpv-2.dll libmpv.version _updater.bat /xd data _update_temp >nul 2>&1

REM --- Update version file ---
echo %VERSION%> "%APP_DIR%resources\\version.txt"

REM --- Cleanup ---
rmdir /s /q "%TEMP_DIR%" 2>nul
del /f /q "%ZIP_PATH%" 2>nul

REM --- Restart application ---
start "" "%APP_DIR%%EXE_NAME%"

REM --- Bring window to foreground ---
timeout /t 2 /nobreak >nul
powershell -Command "(New-Object -ComObject WScript.Shell).AppActivate('%EXE_NAME%')" >nul 2>&1

REM --- Self-delete ---
del "%~f0.exc" 2>nul
(goto) 2>nul & del "%~f0"
"""

    # Write exclusion file for xcopy (one pattern per line)
    exc_path = Path(str(bat_path) + '.exc')
    exc_lines = [
        'settings.ini',
        'ffmpeg.exe',
        'ffprobe.exe',
        'libmpv-2.dll',
        'libmpv.version',
        '_updater.bat',
        '\\data\\',
        '\\_update_temp\\',
    ]
    exc_path.write_text('\n'.join(exc_lines), encoding='utf-8')

    bat_path.write_text(script, encoding='utf-8')
    return bat_path


def launch_updater_and_exit(bat_path: Path):
    """Launch the updater bat script hidden and quit the application."""
    subprocess.Popen(
        ['cmd', '/c', str(bat_path)],
        creationflags=subprocess.CREATE_NO_WINDOW,
        close_fds=True,
        cwd=str(ROOT_DIR),
    )


def cleanup_update_artifacts():
    """Remove leftover update files from previous runs."""
    artifacts = [
        ROOT_DIR / '_update_temp',
        ROOT_DIR / '_update_download.zip',
        ROOT_DIR / '_updater.bat',
        ROOT_DIR / '_updater.bat.exc',
    ]
    for path in artifacts:
        try:
            if path.is_dir():
                import shutil
                shutil.rmtree(path, ignore_errors=True)
            elif path.is_file():
                path.unlink(missing_ok=True)
        except Exception:
            pass


def _get_exe_name() -> str:
    """Get the name of the running executable."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).name
    # Dev mode: return python script name
    return 'SP Video Courses Player.exe'
