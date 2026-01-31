import os
import sys
import urllib.request
import json
import zipfile
import shutil
import time
import threading
import ctypes
import io
from ctypes import wintypes
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from translator import tr

def format_size(size_bytes):
    """Formats bytes into human readable MB."""
    return f"{size_bytes / (1024 * 1024):.1f} MB"

def safe_unlink(path, retries=5, delay=0.5):
    """Attempts to delete a file with retries for Windows permission issues."""
    for i in range(retries):
        try:
            if path.exists():
                path.unlink()
            return True
        except PermissionError:
            if i < retries - 1:
                time.sleep(delay)
            else:
                print(tr('libmpv_updater.warning_delete', path=path))
                return False
        except Exception as e:
            print(tr('libmpv_updater.error_delete', path=path, error=e))
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def _download_chunk(self, start, end):
        req = urllib.request.Request(self.url, headers=self.headers)
        req.add_header('Range', f'bytes={start}-{end}')
        
        try:
            with urllib.request.urlopen(req) as response:
                with open(self.target_path, 'r+b') as f:
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
                sys.stdout.write('\r' + s.ljust(80)[:80])
                sys.stdout.flush()

    def download(self):
        req = urllib.request.Request(self.url, headers=self.headers, method='HEAD')
        with urllib.request.urlopen(req) as response:
            self.total_size = int(response.info().get('Content-Length', 0))
            accept_ranges = response.info().get('Accept-Ranges') == 'bytes'

        with open(self.target_path, 'wb') as f:
            f.truncate(self.total_size)

        self.start_time = time.time()
        
        if accept_ranges and self.total_size > 0:
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
            self._download_chunk(0, self.total_size - 1 if self.total_size > 0 else '')

        self._report_progress(force=True) # Final update
        return time.time() - self.start_time

def get_latest_release():
    api_url = "https://api.github.com/repos/mpvnet-player/mpv.net/releases/latest"
    req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        data = json.load(response)
        tag = data['tag_name']
        assets = data['assets']
        
        # Look for portable-x64.zip
        download_url = None
        for asset in assets:
            if "portable-x64.zip" in asset['name'].lower():
                download_url = asset['browser_download_url']
                break
        
        return tag, download_url

def find_and_extract_dll(zip_obj, target_path):
    """Recursively searches for the DLL in zip and nested zips."""
    all_files = zip_obj.namelist()
    
    # Check current zip level
    dll_names = ["libmpv-2.dll", "mpv.dll", "mpv-2.dll", "libmpv.dll"]
    for name in all_files:
        basename = os.path.basename(name).lower()
        if basename in dll_names:
            print(tr('libmpv_updater.extracting_file', name=name))
            with zip_obj.open(name) as source, open(target_path, 'wb') as target:
                shutil.copyfileobj(source, target)
            return True
            
    # If not found, look for nested zips
    for name in all_files:
        if name.lower().endswith('.zip'):
            print(tr('libmpv_updater.searching_nested', name=name))
            with zip_obj.open(name) as nested_zip_data:
                nested_zip_bytes = io.BytesIO(nested_zip_data.read())
                with zipfile.ZipFile(nested_zip_bytes) as nested_zip_obj:
                    if find_and_extract_dll(nested_zip_obj, target_path):
                        return True
    return False

def update_libmpv():
    script_dir = Path(__file__).parent
    bin_dir = script_dir / "resources" / "bin"
    if not bin_dir.exists():
        bin_dir.mkdir(parents=True, exist_ok=True)
        
    dll_path = bin_dir / "libmpv-2.dll"
    version_file = bin_dir / "libmpv.version"
    zip_path = script_dir / "libmpv.zip"
    
    print("=" * 60)
    print(f"      {tr('libmpv_updater.title')}      ")
    print("=" * 60)
    
    try:
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

        print(tr('libmpv_updater.checking'))
        latest_version, download_url = get_latest_release()
        print(tr('libmpv_updater.latest_version', version=latest_version))
        
        if local_version == latest_version and dll_path.exists():
            print(tr('libmpv_updater.up_to_date'))
            return True

        if not download_url:
            raise Exception(tr('libmpv_updater.no_download_url'))

        print(f"\n{tr('libmpv_updater.updating')}")
        print(f"{tr('libmpv_updater.downloading')}")
        
        downloader = Downloader(download_url, zip_path)
        duration = downloader.download()
        print(f"\n{tr('ffmpeg_updater.download_success', time=duration)}")
        
        print(tr('libmpv_updater.extracting'))
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            if not find_and_extract_dll(zip_ref, dll_path):
                print(tr('libmpv_updater.archive_contents'))
                for name in zip_ref.namelist()[:10]:
                    print(f"  - {name}")
                raise Exception(tr('libmpv_updater.dll_not_found'))
        
        version_file.write_text(latest_version)
        print("-" * 40)
        print(tr('libmpv_updater.success', version=latest_version))
        print("-" * 40)
        
    except Exception as e:
        print(f"\n{tr('libmpv_updater.error', error=e)}")
        return False
    finally:
        if zip_path.exists():
            print(tr('ffmpeg_updater.cleanup'))
            safe_unlink(zip_path)

if __name__ == "__main__":
    update_libmpv()
    print("\n" + "=" * 60)
    input(tr('ffmpeg_updater.press_enter'))
