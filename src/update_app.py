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


def _get_app_dir() -> Path:
    """
    Get the top-level application directory.
    In frozen PyInstaller onedir builds, ROOT_DIR points to _internal/,
    but the .exe lives one level up. This returns the correct dir.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return ROOT_DIR


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
    Returns dict with keys: tag, url, changelog, or None if tag/download_url is missing.
    Raises Exception on network/API errors.
    """
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
    Download update zip to app_dir/_update_download.zip.
    Uses Downloader from update_libmpv for multi-threaded download.
    Returns path to downloaded file.
    """
    import time as _time

    app_dir = _get_app_dir()
    target = app_dir / '_update_download.zip'

    print("=" * 50)
    print("  Downloading application update...")
    print("=" * 50)
    print(f"URL: {download_url}")
    print(f"Target: {target}")
    print("")

    try:
        from update_libmpv import Downloader, format_size
        downloader = Downloader(download_url, str(target))

        # Get file size before download
        req = urllib.request.Request(download_url, headers={'User-Agent': USER_AGENT}, method='HEAD')
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                total = int(resp.info().get('Content-Length', 0))
                if total > 0:
                    print(f"File size: {format_size(total)}")
        except Exception:
            pass

        print(f"Threads: {downloader.num_threads}")
        print("Downloading...")
        print("")

        duration = downloader.download()

        print("")
        print(f"Download completed in {duration:.1f}s")
    except ImportError:
        # Fallback: simple download
        print("Using single-thread fallback...")
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

    size_mb = target.stat().st_size / (1024 * 1024)
    print(f"Saved: {target.name} ({size_mb:.1f} MB)")
    print("")
    print("Creating updater script...")
    return target


def create_updater_script(zip_path: Path, new_version: str) -> Path:
    """
    Generate _updater.bat that waits for app exit, extracts zip,
    copies files (skipping protected ones), restarts app, self-deletes.
    """
    app_dir = _get_app_dir()
    bat_path = app_dir / '_updater.bat'
    exe_name = _get_exe_name()
    exe_path = _get_exe_path()
    current_pid = os.getpid()

    script = f"""@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

set "APP_DIR=%~dp0"
set "EXE_PATH={exe_path}"
set "PID={current_pid}"
set "ZIP_PATH={zip_path}"
set "TEMP_DIR=%APP_DIR%_update_temp"
set "VERSION={new_version}"
set "LOG=%APP_DIR%_update_log.txt"

echo [%date% %time%] Update started > "%LOG%"
echo APP_DIR=%APP_DIR% >> "%LOG%"
echo EXE_PATH=%EXE_PATH% >> "%LOG%"
echo ZIP_PATH=%ZIP_PATH% >> "%LOG%"

REM --- Wait for application to exit ---
echo Waiting for PID %PID% to exit... >> "%LOG%"
:wait_loop
tasklist /FI "PID eq %PID%" 2>nul | find "%PID%" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)
echo Process exited. >> "%LOG%"

REM --- Small delay for file handles to release ---
timeout /t 3 /nobreak >nul

REM --- Extract zip to temp directory ---
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%" 2>nul
echo Extracting zip... >> "%LOG%"
powershell -Command "Expand-Archive -Path '%ZIP_PATH%' -DestinationPath '%TEMP_DIR%' -Force"
echo Extraction done. >> "%LOG%"

REM --- Find the actual content root (may be nested in a subfolder) ---
set "SOURCE_DIR=%TEMP_DIR%"

REM Check if zip contains a single top-level folder
set "SUBFOLDER_COUNT=0"
set "LAST_SUBFOLDER="
for /d %%D in ("%TEMP_DIR%\\*") do (
    set /a SUBFOLDER_COUNT+=1
    set "LAST_SUBFOLDER=%%D"
    echo Found subfolder: %%D >> "%LOG%"
)

REM Count files at root level
set "FILE_COUNT=0"
for %%F in ("%TEMP_DIR%\\*.*") do (
    set /a FILE_COUNT+=1
    echo Found root file: %%F >> "%LOG%"
)

if !SUBFOLDER_COUNT! equ 1 if !FILE_COUNT! equ 0 (
    set "SOURCE_DIR=!LAST_SUBFOLDER!"
    echo Using subfolder as source: !SOURCE_DIR! >> "%LOG%"
)

echo SOURCE_DIR=!SOURCE_DIR! >> "%LOG%"

REM --- List source contents for debugging ---
echo Source directory contents: >> "%LOG%"
dir /b "!SOURCE_DIR!" >> "%LOG%" 2>&1

REM --- Copy all files using robocopy, excluding protected items ---
echo Starting robocopy... >> "%LOG%"
robocopy "!SOURCE_DIR!" "%APP_DIR%." /e /np /njh /njs /r:3 /w:2 /xf settings.ini ffmpeg.exe ffprobe.exe libmpv-2.dll libmpv.version _updater.bat _updater.bat.exc _update_log.txt /xd data _update_temp >> "%LOG%" 2>&1
echo Robocopy exit code: !errorlevel! >> "%LOG%"

REM --- Update version file ---
if exist "%APP_DIR%_internal\\resources\\version.txt" (
    echo %VERSION%> "%APP_DIR%_internal\\resources\\version.txt"
    echo Updated version in _internal\\resources\\version.txt >> "%LOG%"
) else if exist "%APP_DIR%resources\\version.txt" (
    echo %VERSION%> "%APP_DIR%resources\\version.txt"
    echo Updated version in resources\\version.txt >> "%LOG%"
)

REM --- Cleanup ---
echo Cleaning up... >> "%LOG%"
rmdir /s /q "%TEMP_DIR%" 2>nul
del /f /q "%ZIP_PATH%" 2>nul

REM --- Restart application ---
echo Starting: %EXE_PATH% >> "%LOG%"
start "" "%EXE_PATH%"

REM --- Bring window to foreground ---
timeout /t 2 /nobreak >nul
powershell -Command "(New-Object -ComObject WScript.Shell).AppActivate('{exe_name}')" >nul 2>&1

REM --- Self-delete ---
echo Update complete. >> "%LOG%"
del "%~f0.exc" 2>nul
(goto) 2>nul & del "%~f0"
"""

    bat_path.write_text(script, encoding='utf-8')
    return bat_path


def launch_updater_and_exit(bat_path: Path):
    """Launch the updater bat script hidden and quit the application."""
    app_dir = _get_app_dir()
    subprocess.Popen(
        ['cmd', '/c', str(bat_path)],
        creationflags=subprocess.CREATE_NO_WINDOW,
        close_fds=True,
        cwd=str(app_dir),
    )


def cleanup_update_artifacts():
    """Remove leftover update files from previous runs."""
    app_dir = _get_app_dir()
    artifacts = [
        app_dir / '_update_temp',
        app_dir / '_update_download.zip',
        app_dir / '_updater.bat',
        app_dir / '_updater.bat.exc',
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
    """Get the name of the running executable (just filename)."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).name
    return 'SP Video Courses Player.exe'


def _get_exe_path() -> str:
    """Get the full path to the running executable."""
    if getattr(sys, 'frozen', False):
        return str(Path(sys.executable))
    return str(ROOT_DIR / 'SP Video Courses Player.exe')
