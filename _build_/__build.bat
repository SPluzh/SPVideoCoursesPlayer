@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0"
set "PATH=%~dp0bin;%PATH%"

echo ==================================================
echo  SPVideoCoursesPlayer - BUILD
echo ==================================================

REM --- check python ---
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    pause
    exit /b 1
)

REM --- check pyinstaller ---
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller not installed
    echo Install: pip install pyinstaller
    pause
    exit /b 1
)


REM --- clean previous builds ---
if exist build (
    echo Cleaning build/
    rmdir /s /q build
    if exist build (
        echo [ERROR] Failed to delete 'build' directory. Close open files and try again.
        pause
        exit /b 1
    )
)

if exist dist (
    echo Cleaning dist/
    rmdir /s /q dist
    if exist dist (
        echo [ERROR] Failed to delete 'dist' directory.
        pause
        exit /b 1
    )
)

REM --- build ---
echo.
echo Building...
echo.

python -m PyInstaller SPVideoCoursesPlayer.spec
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed
    pause
    exit /b 1
)

REM --- Cleaning up build folder after build ---
if exist build (
    rmdir /s /q build
)

echo.
echo ==========================================
echo  BUILD SUCCESSFUL
echo ==========================================
echo.

REM --- Open output folder ---
if not exist "dist\SP Video Courses Player" (
    echo [ERROR] Output directory missing.
    pause
    exit /b 1
)
explorer "dist\SP Video Courses Player"

echo Output:
echo   dist\SP Video Courses Player\SP Video Courses Player.exe
echo.

