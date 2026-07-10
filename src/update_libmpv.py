import os
import sys
import urllib.request
import urllib.error
import urllib.parse
import json
import zipfile
import shutil
import time
import threading
import ctypes
import io
import subprocess
import re
from ctypes import wintypes
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from translator import tr
from abc import ABC, abstractmethod

# Fix console encoding for Windows to prevent UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Fallback for older python versions if needed, though 3.7+ has reconfigure
        pass

_TOKEN_FILE = ".github_token"


def _get_github_token() -> str:
    """
    Load a GitHub Personal Access Token for authenticated API requests.
    Priority:
      1. Environment variable GITHUB_TOKEN
      2. File .github_token next to the exe / src directory
    Returns empty string if not found.
    """
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token
    if getattr(sys, 'frozen', False):
        token_path = Path(sys.executable).parent / _TOKEN_FILE
    else:
        token_path = Path(__file__).parent / _TOKEN_FILE
    if token_path.exists():
        try:
            return token_path.read_text("utf-8").strip()
        except Exception:
            pass
    return ""


# Try importing py7zr
try:
    import py7zr
    HAS_PY7ZR = True
except ImportError:
    HAS_PY7ZR = False

def format_size(size_bytes):
    """Formats bytes into human readable MB."""
    return f"{size_bytes / (1024 * 1024):.1f} MB"

def safe_unlink(path, retries=5, delay=0.5):
    """Attempts to delete a file with retries for Windows permission issues."""
    path = Path(path)
    for i in range(retries):
        try:
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            return True
        except PermissionError:
            if i < retries - 1:
                time.sleep(delay)
            else:
                print(f"Warning: Could not delete {path}") # Fallback for tr failures
                return False
        except Exception as e:
            print(f"Error deleting {path}: {e}")
            return False
    return False

def get_dll_version(path):
    """Extracts ProductVersion string from DLL using Windows API."""
    try:
        path = str(path)
        size = ctypes.windll.version.GetFileVersionInfoSizeW(path, None)
        if not size:
            return None
        
        res = ctypes.create_string_buffer(size)
        ctypes.windll.version.GetFileVersionInfoW(path, 0, size, res)
        
        translations = ctypes.POINTER(wintypes.DWORD)()
        trans_len = wintypes.UINT()
        ctypes.windll.version.VerQueryValueW(res, "\\VarFileInfo\\Translation", ctypes.byref(translations), ctypes.byref(trans_len))
        
        codepages = [(0x0409, 0x04b0), (0x0409, 0x04E4), (0x0000, 0x04b0)]
        if trans_len.value >= 4:
            trans = translations[0]
            codepages.insert(0, (trans & 0xFFFF, trans >> 16))

        for lang, cp in codepages:
            for property_name in ["ProductVersion", "FileVersion"]:
                str_info = f"\\StringFileInfo\\{lang:04x}{cp:04x}\\{property_name}"
                ptr = ctypes.c_wchar_p()
                length = wintypes.UINT()
                if ctypes.windll.version.VerQueryValueW(res, str_info, ctypes.byref(ptr), ctypes.byref(length)):
                    if ptr.value:
                        v = ptr.value.strip()
                        if "-" in v:
                            v = v.split("-")[0]
                        if v and not v.startswith('v'):
                            v = 'v' + v
                        return v
    except:
        pass
    return None

class Downloader:
    def __init__(self, url, target_path, num_threads=8):
        self.url = url
        self.target_path = target_path
        self.num_threads = num_threads
        self.total_size = 0
        self.read_so_far = 0
        self.start_time = 0
        self.lock = threading.RLock()
        self.last_update_time = 0
        self.update_interval = 0.1 # Max updates every 100ms
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
        }

    def _resolve_redirects(self, url):
        """Resolves redirects to get the final download URL before using HEAD/Range."""
        try:
            req = urllib.request.Request(url, headers=self.headers, method='HEAD')
            with urllib.request.urlopen(req) as response:
                return response.geturl()
        except:
            # Fallback to GET just in case HEAD is blocked
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req) as response:
                     return response.geturl()
            except:
                return url

    def _download_chunk(self, start, end):
        req = urllib.request.Request(self.url, headers=self.headers)
        if start is not None and end is not None:
             req.add_header('Range', f'bytes={start}-{end}')
        
        try:
            with urllib.request.urlopen(req) as response:
                with open(self.target_path, 'r+b') as f:
                    if start is not None:
                        f.seek(start)
                    chunk_size = 1024 * 256
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        with self.lock:
                            self.read_so_far += len(chunk)
                            self._report_progress()
        except:
            raise

    def _report_progress(self, force=False):
        now = time.time()
        with self.lock:
            if not force and now - self.last_update_time < self.update_interval:
                return
            self.last_update_time = now
            
            elapsed_time = now - self.start_time
            if elapsed_time > 0:
                speed_val = self.read_so_far / elapsed_time
                speed_str = f"{speed_val / (1024 * 1024):.1f} MB/s"
                
                if self.total_size > 0:
                    percent = self.read_so_far * 100 / self.total_size
                    remaining_bytes = self.total_size - self.read_so_far
                    eta_secs = remaining_bytes / speed_val if speed_val > 0 else 0
                    eta_str = f"{int(eta_secs // 60)}m {int(eta_secs % 60)}s"
                    
                    s = tr('ffmpeg_updater.progress', 
                           current=format_size(self.read_so_far), 
                           total=format_size(self.total_size), 
                           percent=percent,
                           speed=speed_str,
                           eta=eta_str)
                else:
                    s = tr('ffmpeg_updater.progress_unknown', 
                           current=format_size(self.read_so_far),
                           speed=speed_str)
                
                # Clear line and print new progress
                if sys.stdout:
                    sys.stdout.write('\r' + s.ljust(80)[:80])
                    sys.stdout.flush()

    def download(self):
        # Resolve any redirects first to get the final direct link if possible
        print(f"Resolving URL: {self.url}")
        self.url = self._resolve_redirects(self.url)
        print(f"Resolved URL: {self.url}")

        req = urllib.request.Request(self.url, headers=self.headers, method='HEAD')
        try:
            with urllib.request.urlopen(req) as response:
                self.total_size = int(response.info().get('Content-Length', 0))
                self.accept_ranges = response.info().get('Accept-Ranges') == 'bytes'
        except Exception as e:
             print(f"HEAD request failed: {e}. Falling back to single-thread download.")
             self.total_size = 0
             self.accept_ranges = False

        with open(self.target_path, 'wb') as f:
            if self.total_size > 0:
                f.truncate(self.total_size)
            else:
                # If size unknown, just create/truncate
                pass

        self.start_time = time.time()
        
        if self.accept_ranges and self.total_size > 0:
            chunk_size = self.total_size // self.num_threads
            futures = []
            with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
                for i in range(self.num_threads):
                    start = i * chunk_size
                    end = self.total_size - 1 if i == self.num_threads - 1 else (i + 1) * chunk_size - 1
                    futures.append(executor.submit(self._download_chunk, start, end))
                for future in futures:
                    future.result()
        else:
            # Single threaded fallback (no Range support or unknown size)
            self._download_chunk(None, None)

        self._report_progress(force=True) # Final update
        return time.time() - self.start_time

class ReleaseSource(ABC):
    @abstractmethod
    def get_latest_release(self):
        pass
    
    @abstractmethod
    def get_name(self):
        pass


class GitHubSource(ReleaseSource):
    def __init__(self, repo, author_name):
        self.repo = repo
        self.author_name = author_name
        self.api_url = f"https://api.github.com/repos/{repo}/releases/latest"

    def get_name(self):
        return f"GitHub ({self.author_name})"

    def get_latest_release(self):
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/vnd.github.v3+json'
        }
        token = _get_github_token()
        if token:
            headers['Authorization'] = f'Bearer {token}'
        req = urllib.request.Request(self.api_url, headers=headers)
        try:
            with urllib.request.urlopen(req) as response:
                data = json.load(response)
                
                assets = data.get('assets', [])
                download_url = None
                
                for asset in assets:
                    name = asset['name'].lower()
                    if 'mpv-dev-x86_64' in name and name.endswith('.7z') and 'v3' not in name:
                         download_url = asset['browser_download_url']
                         break
                
                if not download_url:
                     for asset in assets:
                        name = asset['name'].lower()
                        if 'mpv-x86_64' in name and name.endswith('.7z') and 'v3' not in name:
                            download_url = asset['browser_download_url']
                            break
    
                tag = data['tag_name']
                
                return tag, download_url
        except Exception as e:
            print(f"GitHub error for {self.repo}: {e}")
            return None, None

def get_7z_path(bin_dir=None):
    """Tries to find 7z/7zr executable."""
    common_paths = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]
    # Check PATH
    path = shutil.which("7z") or shutil.which("7zr")
    if path:
        return path
    
    # Check bin directory for 7zr.exe
    if bin_dir:
        local_7zr = Path(bin_dir) / "7zr.exe"
        if local_7zr.exists():
            return str(local_7zr)
        
    for p in common_paths:
        if os.path.exists(p):
            return p
    return None

def download_7zr(target_dir):
    """Downloads standalone 7-Zip console (7zr.exe) from 7-zip.org."""
    url = "https://www.7-zip.org/a/7zr.exe"
    target_path = Path(target_dir) / "7zr.exe"
    print(f"Downloading standalone 7zr.exe from {url}...")
    try:
        # Use headers to be safe
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response, open(target_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print(f"7zr.exe downloaded successfully to {target_path}")
        return str(target_path)
    except Exception as e:
        print(f"Failed to download 7zr.exe: {e}")
        return None

def extract_7z(archive_path, extract_to, bin_dir=None):
    """Extracts .7z archive with robust fallbacks."""
    
    # 1. Try 7-Zip executable (system or local)
    seven_zip_exe = get_7z_path(bin_dir)
    
    # If not found, try to download 7zr.exe to bin_dir
    if not seven_zip_exe and bin_dir:
        print("7-Zip not found. Attempting to download 7zr.exe...")
        seven_zip_exe = download_7zr(bin_dir)
        
    if seven_zip_exe:
        try:
            print(f"Extracting with 7-Zip: {seven_zip_exe}")
            cmd = [seven_zip_exe, 'x', '-y', f'-o{extract_to}', str(archive_path)]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"7-Zip extraction failed: {e.stderr.decode('utf-8', 'ignore') if e.stderr else e}")
            print("Trying next method...")

    # 2. Try py7zr (pure python fallback)
    if HAS_PY7ZR:
        try:
            print("Extracting with py7zr...")
            with py7zr.SevenZipFile(archive_path, mode='r') as z:
                z.extractall(path=extract_to)
            return True
        except Exception as e:
            print(f"py7zr extraction failed: {e}. Trying next method...")
    
    # 3. Try system tar (last resort)
    try:
        print("Extracting with system tar...")
        subprocess.run(['tar', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        cmd = ['tar', '-x', '-f', str(archive_path), '-C', str(extract_to)]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise Exception(f"Tar failed: {result.stderr.strip()}")
        return True
    except Exception as e:
        msg = f"All extraction methods failed. Please install 7-Zip manually. Error: {e}"
        raise Exception(msg)

def find_dll_in_dir(search_dir):
    """Recursively searches for libmpv-2.dll."""
    for root, dirs, files in os.walk(search_dir):
        for name in files:
            if name.lower() in ["libmpv-2.dll", "mpv-2.dll"]:
                return Path(root) / name
    return None

def update_libmpv():
    script_dir = Path(__file__).parent
    bin_dir = script_dir / "resources" / "bin"
    temp_dir = script_dir / "temp_mpv_extract"
    
    if not bin_dir.exists():
        bin_dir.mkdir(parents=True, exist_ok=True)
        
    dll_path = bin_dir / "libmpv-2.dll"
    version_file = bin_dir / "libmpv.version"
    archive_path = script_dir / "libmpv_archive.7z"
    
    print("=" * 60)
    print(f"      {tr('libmpv_updater.title')}      ")
    print("=" * 60)
    
    local_version = None
    if version_file.exists():
        local_version = version_file.read_text().strip()
    
    if not local_version and dll_path.exists():
        local_version = get_dll_version(dll_path)
        if local_version:
            version_file.write_text(local_version)
    
    if not dll_path.exists():
        print(tr('libmpv_updater.not_found'))
        local_version = "missing"
    else:
        print(tr('libmpv_updater.local_version', version=local_version or "unknown"))

    sources = [
        GitHubSource("shinchiro/mpv-winbuild-cmake", "shinchiro"),
        GitHubSource("zhongfly/mpv-winbuild", "zhongfly")
    ]
 
    print(tr('libmpv_updater.checking'))

    updated = False
    
    for source in sources:
        try:
            print(f"Checking {source.get_name()}...")
            ver, url = source.get_latest_release()
            
            if not ver or not url:
                print(f"No release found or error with {source.get_name()}")
                continue
                
            print(f"Found version {ver} at {source.get_name()}")
            
            if local_version == ver and dll_path.exists():
                print(tr('libmpv_updater.up_to_date'))
                return True
                
            print(f"\n{tr('libmpv_updater.updating')}")
            print(f"{tr('libmpv_updater.downloading')}")
        
            try:
                downloader = Downloader(url, archive_path)
                duration = downloader.download()
                print(f"\n{tr('ffmpeg_updater.download_success', time=duration)}")
                
                print(tr('libmpv_updater.extracting'))
                safe_unlink(temp_dir)
                temp_dir.mkdir(exist_ok=True)
                
                extract_7z(archive_path, temp_dir, bin_dir)
                
                new_dll = find_dll_in_dir(temp_dir)
                if not new_dll:
                     raise Exception(tr('libmpv_updater.dll_not_found'))
                
                print(f"Found DLL at: {new_dll}")
                shutil.copy2(new_dll, dll_path)
                
                include_src = new_dll.parent.parent / "include"
                include_dst = bin_dir.parent / "include"
                if include_src.exists() and include_src.is_dir():
                     if include_dst.exists():
                         safe_unlink(include_dst)
                     shutil.copytree(include_src, include_dst)
                     print("Updated headers.")
        
                version_file.write_text(ver)
                print("-" * 40)
                print(tr('libmpv_updater.success', version=ver))
                print("-" * 40)
                updated = True
                break
                
            except Exception as e:
                print(f"Error with {source.get_name()}: {e}")
                print("Trying next source...")
                if archive_path.exists():
                    safe_unlink(archive_path)
                if temp_dir.exists():
                    safe_unlink(temp_dir)
                continue
                
        except Exception as e:
            print(f"Failed to check {source.get_name()}: {e}")
            continue

    if not updated:
        if not dll_path.exists():
             print(f"\nError: All sources failed and local DLL missing.")
             return False
        else:
             print(f"\nAll sources failed. Keeping local version.")
             return False
             
    if archive_path.exists():
        print(tr('ffmpeg_updater.cleanup'))
        safe_unlink(archive_path)
    if temp_dir.exists():
        safe_unlink(temp_dir)
        
    return True

if __name__ == "__main__":
    try:
        if update_libmpv():
            print("\n" + "=" * 60)
            input(tr('ffmpeg_updater.press_enter'))
        else:
            print("\n" + "=" * 60)
            input("Update failed. Press Enter to exit...")
    except Exception as e:
        print(f"\nFatal Error: {e}")
        input("Press Enter to exit...")
