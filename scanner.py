import subprocess
import json
import sys
import os
import re
import time
import threading
import sqlite3
import configparser
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from translator import tr
from database import DatabaseManager

# Fix for 'charmap' codec errors on Windows when printing Cyrillic
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

def natural_sort_key(path):
    """
    Natural sort key.
    "1. Intro" < "2. Basic" < "10. Advanced"
    """
    def convert(text):
        return int(text) if text.isdigit() else text.lower()
    
    name = path.name if isinstance(path, Path) else str(path)
    return [convert(c) for c in re.split(r'(\d+)', name)]


class VideoScanner:
    def __init__(self, config_file='video_course_browser.ini'):
        print("\n" + "=" * 70)
        print(tr('scanner.init_title'))
        print("=" * 70)

        self.script_dir = Path(__file__).parent
        self.data_dir = self.script_dir / 'data'
        self.data_dir.mkdir(exist_ok=True)
        
        self.config_file = self.script_dir / config_file
        self.db_file = self.data_dir / 'video_courses.db'
        self.thumbnails_dir = self.data_dir / 'video_thumbnails'
        
        self._load_settings()
        
        # Paths to ffprobe and ffmpeg are already set in _load_settings, but ensure defaults if not loaded
        if not hasattr(self, 'ffprobe_path'):
            self.ffprobe_path = self.script_dir / 'resources/bin/ffprobe.exe'
        self.has_ffprobe = self.ffprobe_path.exists()
        
        if not hasattr(self, 'ffmpeg_path'):
            self.ffmpeg_path = self.script_dir / 'resources/bin/ffmpeg.exe'
        self.has_ffmpeg = self.ffmpeg_path.exists()

        print(f"\n{tr('scanner.paths_title')}")
        print(tr('scanner.path_script', path=self.script_dir))
        print(tr('scanner.path_db', path=self.db_file))
        print(tr('scanner.path_thumbs', path=self.thumbnails_dir))
        
        if self.has_ffprobe:
            print(tr('scanner.ffprobe_found'))
        else:
            print(tr('scanner.ffprobe_not_found'))
            
        if self.has_ffmpeg:
            print(tr('scanner.ffmpeg_found'))
        else:
            print(tr('scanner.ffmpeg_not_found'))

        self.thumbnails_dir.mkdir(exist_ok=True)
        
        # Initialize Database Manager
        self.db = DatabaseManager(self.db_file)
        
        self._print_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'thumbnails_generated': 0,
            'thumbnails_cached': 0,
            'thumbnails_failed': 0,
            'time_thumbnails': 0,
            'time_ffprobe': 0,
            'time_total': 0
        }

    def _load_settings(self):
        """Load settings from configuration file."""
        config = configparser.ConfigParser()
        config.read(self.config_file, encoding='utf-8')

        # Path to thumbnails folder
        if config.has_section('Paths'):
            custom_thumbs = config.get('Paths', 'thumbnails_dir', fallback=None)
            if custom_thumbs:
                self.thumbnails_dir = Path(custom_thumbs)
                if not self.thumbnails_dir.is_absolute():
                    self.thumbnails_dir = self.script_dir / self.thumbnails_dir

            # Paths to binary files
            ffmpeg_custom = config.get('Paths', 'ffmpeg_path', fallback=None)
            if ffmpeg_custom:
                self.ffmpeg_path = Path(ffmpeg_custom)
                if not self.ffmpeg_path.is_absolute():
                    self.ffmpeg_path = self.script_dir / self.ffmpeg_path

            ffprobe_custom = config.get('Paths', 'ffprobe_path', fallback=None)
            if ffprobe_custom:
                self.ffprobe_path = Path(ffprobe_custom)
                if not self.ffprobe_path.is_absolute():
                    self.ffprobe_path = self.script_dir / self.ffprobe_path

        # Video file extensions
        extensions = config.get(
            'Video', 'extensions',
            fallback='.mp4,.mkv,.avi,.mov,.wmv,.flv,.webm,.m4v,.mpg,.mpeg,.3gp,.ts'
        )
        self.video_extensions = {e.strip().lower() for e in extensions.split(',')}

        # Audio file extensions
        audio_extensions = config.get(
            'Audio', 'extensions',
            fallback='.mp3,.aac,.ac3,.dts,.flac,.wav,.ogg,.m4a,.wma,.eac3,.opus,.mka'
        )
        self.audio_extensions = {e.strip().lower() for e in audio_extensions.split(',')}

        # Subtitle file extensions
        subtitle_extensions = config.get(
            'Subtitles', 'extensions',
            fallback='.srt,.ass,.ssa,.sub,.idx,.vtt,.sup,.stl,.smi,.txt'
        )
        self.subtitle_extensions = {e.strip().lower() for e in subtitle_extensions.split(',')}

        # Thumbnail settings
        self.render_width = config.getint('Thumbnails', 'render_width', fallback=320)
        self.render_height = config.getint('Thumbnails', 'render_height', fallback=180)
        self.thumbnail_count = config.getint('Thumbnails', 'count', fallback=10)
        self.thumbnail_quality = config.getint('Thumbnails', 'quality', fallback=5)  # 2-31, lower is better
        self.regenerate_thumbnails = config.getboolean('Thumbnails', 'regenerate', fallback=False)
        
        # Performance settings
        self.max_workers = config.getint('Performance', 'max_workers', fallback=8)
        self.thumbnail_workers = config.getint('Performance', 'thumbnail_workers', fallback=4)
        self.ffmpeg_timeout = config.getint('Performance', 'ffmpeg_timeout', fallback=5)

        print(f"\n{'─' * 40}")
        print(tr('scanner.settings_title'))
        print(f"{'─' * 40}")
        print(tr('scanner.thumbs_title'))
        print(tr('scanner.thumbs_size', width=self.render_width, height=self.render_height))
        print(tr('scanner.thumbs_quality', quality=self.thumbnail_quality))
        print(tr('scanner.thumbs_count', count=self.thumbnail_count))
        regen_status = tr('scanner.yes') if self.regenerate_thumbnails else tr('scanner.no')
        print(tr('scanner.thumbs_regen', status=regen_status))
        print(f"\n{tr('scanner.perf_title')}")
        print(tr('scanner.perf_video_workers', count=self.max_workers))
        print(tr('scanner.perf_thumb_workers', count=self.thumbnail_workers))
        print(tr('scanner.perf_timeout', seconds=self.ffmpeg_timeout))
        print(f"\n{tr('scanner.formats_title')}")
        print(tr('scanner.formats_video', count=len(self.video_extensions)))
        print(tr('scanner.formats_audio', count=len(self.audio_extensions)))
        print(tr('scanner.formats_subtitle', count=len(self.subtitle_extensions)))

    def _get_existing_video_data(self, file_path):
        """Get existing video data from DB for caching."""
        return self.db.get_existing_video_data(file_path)

    def _get_existing_audio_selection(self, video_id):
        """Get information about previously selected audio track."""
        try:
            with self.db.get_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT track_type, stream_index, audio_file_path 
                    FROM audio_tracks WHERE id = (
                        SELECT selected_audio_id FROM video_files WHERE id = ?
                    )
                """, (video_id,))
                row = c.fetchone()
                if row:
                    return {
                        'track_type': row[0],
                        'stream_index': row[1],
                        'audio_file_path': row[2]
                    }
        except:
            pass
        return None

    def _get_subprocess_startupinfo(self):
        """Get startupinfo to hide console windows on Windows."""
        startupinfo = None
        if hasattr(subprocess, 'STARTUPINFO'):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        return startupinfo

    def _create_thumbnails_batch(self, video_path, duration, video_hash):
        """
        FAST thumbnail generation using a single ffmpeg call with the select filter.
        Extracts all frames in a single pass through the file.
        """
        if not duration or duration < 1:
            duration = 60
        
        # Calculate time points (5% - 95% of duration)
        start_time = duration * 0.05
        end_time = duration * 0.95
        interval = (end_time - start_time) / (self.thumbnail_count - 1) if self.thumbnail_count > 1 else 0
        
        timestamps = [start_time + interval * i for i in range(self.thumbnail_count)]
        
        # Form select expression for ffmpeg
        # select='eq(n,frame1)+eq(n,frame2)+...' - but this requires knowing frame numbers
        # Better to use multiple -ss with -frames:v 1
        
        thumbnail_paths = []
        startupinfo = self._get_subprocess_startupinfo()
        
        for idx, time_sec in enumerate(timestamps):
            thumb_path = self.thumbnails_dir / f"{video_hash}_{idx}.jpg"
            
            # Skip if already exists
            if thumb_path.exists() and not self.regenerate_thumbnails:
                thumbnail_paths.append(str(thumb_path))
                self.stats['thumbnails_cached'] += 1
                continue
            
            try:
                # OPTIMIZED ffmpeg command:
                # -ss BEFORE -i = fast seek without decoding
                # -skip_frame noref = skip non-key frames (faster)
                # -an = no audio
                # -frames:v 1 = only 1 frame
                # -q:v = JPEG quality (2-31)
                cmd = [
                    str(self.ffmpeg_path),
                    '-ss', f'{time_sec:.2f}',           # Seek BEFORE input (fast!)
                    '-i', str(video_path),
                    '-vf', f'scale={self.render_width}:{self.render_height}:force_original_aspect_ratio=decrease,'
                           f'pad={self.render_width}:{self.render_height}:(ow-iw)/2:(oh-ih)/2:color=black',
                    '-frames:v', '1',                    # Only 1 frame
                    '-q:v', str(self.thumbnail_quality), # JPEG quality
                    '-an',                               # No audio
                    '-y',                                # Overwrite
                    str(thumb_path)
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=self.ffmpeg_timeout,
                    startupinfo=startupinfo
                )
                
                if thumb_path.exists():
                    thumbnail_paths.append(str(thumb_path))
                    self.stats['thumbnails_generated'] += 1
                else:
                    self.stats['thumbnails_failed'] += 1
                    
            except subprocess.TimeoutExpired:
                self.stats['thumbnails_failed'] += 1
            except Exception:
                self.stats['thumbnails_failed'] += 1
        
        return thumbnail_paths

    def _create_thumbnails_parallel(self, video_path, duration, video_hash):
        """
        Parallel thumbnail generation - each frame in a separate thread.
        Maximum speed on multi-core systems.
        """
        if not duration or duration < 1:
            duration = 60
        
        start_time = duration * 0.05
        end_time = duration * 0.95
        interval = (end_time - start_time) / (self.thumbnail_count - 1) if self.thumbnail_count > 1 else 0
        
        def extract_single_frame(args):
            idx, time_sec = args
            thumb_path = self.thumbnails_dir / f"{video_hash}_{idx}.jpg"
            
            if thumb_path.exists() and not self.regenerate_thumbnails:
                return (idx, str(thumb_path), 'cached')
            
            try:
                startupinfo = self._get_subprocess_startupinfo()
                
                cmd = [
                    str(self.ffmpeg_path),
                    '-ss', f'{time_sec:.2f}',
                    '-i', str(video_path),
                    '-vf', f'scale={self.render_width}:{self.render_height}:force_original_aspect_ratio=decrease,'
                           f'pad={self.render_width}:{self.render_height}:(ow-iw)/2:(oh-ih)/2:color=black',
                    '-frames:v', '1',
                    '-q:v', str(self.thumbnail_quality),
                    '-an',
                    '-y',
                    str(thumb_path)
                ]
                
                subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=self.ffmpeg_timeout,
                    startupinfo=startupinfo
                )
                
                if thumb_path.exists():
                    return (idx, str(thumb_path), 'generated')
                return (idx, None, 'failed')
                
            except:
                return (idx, None, 'failed')
        
        # Create tasks
        tasks = [(i, start_time + interval * i) for i in range(self.thumbnail_count)]
        
        # Parallel execution
        results = [None] * self.thumbnail_count
        
        with ThreadPoolExecutor(max_workers=self.thumbnail_workers) as executor:
            futures = {executor.submit(extract_single_frame, task): task[0] for task in tasks}
            
            for future in as_completed(futures):
                idx, path, status = future.result()
                results[idx] = path
                
                if status == 'cached':
                    self.stats['thumbnails_cached'] += 1
                elif status == 'generated':
                    self.stats['thumbnails_generated'] += 1
                else:
                    self.stats['thumbnails_failed'] += 1
        
        # Filter None
        return [p for p in results if p]

    def _create_thumbnails_fast(self, video_path, duration, existing_data=None):
        """
        Main method for creating thumbnails with caching.
        
        Logic:
        1. Check cache in DB
        2. Check files on disk
        3. Generate missing ones in parallel
        """
        if not self.has_ffmpeg:
            return None, []
        
        video_hash = self._get_video_hash(video_path)
        
        # STEP 1: Check cache in database
        if existing_data and not self.regenerate_thumbnails:
            if existing_data.get('thumbnails_json'):
                try:
                    cached_list = json.loads(existing_data['thumbnails_json'])
                    if cached_list and len(cached_list) == self.thumbnail_count:
                        # Check existence of all files
                        all_exist = all(Path(p).exists() for p in cached_list)
                        if all_exist:
                            self.stats['thumbnails_cached'] += len(cached_list)
                            return cached_list[0], cached_list
                except:
                    pass
        
        # STEP 2: Check files on disk
        if not self.regenerate_thumbnails:
            existing_files = []
            for i in range(self.thumbnail_count):
                p = self.thumbnails_dir / f"{video_hash}_{i}.jpg"
                if p.exists():
                    existing_files.append(str(p))
            
            if len(existing_files) == self.thumbnail_count:
                self.stats['thumbnails_cached'] += len(existing_files)
                return existing_files[0], existing_files
        
        # STEP 3: Generate thumbnails in parallel
        start_time = time.time()
        
        # Remove ALL old files for this hash to avoid index conflicts
        for old_file in self.thumbnails_dir.glob(f"{video_hash}_*.jpg"):
            try:
                old_file.unlink()
            except:
                pass
        
        thumbnail_paths = self._create_thumbnails_parallel(video_path, duration, video_hash)
        
        elapsed = time.time() - start_time
        self.stats['time_thumbnails'] += elapsed
        
        return thumbnail_paths[0] if thumbnail_paths else None, thumbnail_paths

    def _has_video_files(self, directory):
        """Fast check for video files in directory."""
        try:
            return any(f.is_file() and f.suffix.lower() in self.video_extensions for f in directory.iterdir())
        except (PermissionError, OSError):
            return False

    def _get_video_hash(self, video_path):
        """Generate unique hash for video file based on path and size."""
        path_str = str(video_path)
        try:
            size = video_path.stat().st_size
            mtime = video_path.stat().st_mtime
            key = f"{path_str}_{size}_{mtime}"
        except:
            key = path_str
            
        return hashlib.md5(key.encode('utf-8')).hexdigest()

    def _get_video_info_with_audio_subs(self, path):
        """
        Get full information about video file via ffprobe.
        
        Returns:
        - duration: duration in seconds
        - resolution: resolution (e.g. "1920x1080")
        - codec: video codec
        - file_size: file size
        - embedded_audio_tracks: list of embedded audio tracks
        - embedded_subtitle_tracks: list of embedded subtitle tracks
        """
        start_time = time.time()
        
        duration = 0
        resolution = None
        codec = None
        embedded_audio_tracks = []
        embedded_subtitle_tracks = []
        
        try:
            file_size = path.stat().st_size
        except:
            file_size = 0
        
        if self.has_ffprobe:
            try:
                startupinfo = self._get_subprocess_startupinfo()
                
                result = subprocess.run(
                    [
                        str(self.ffprobe_path),
                        '-v', 'quiet',
                        '-print_format', 'json',
                        '-show_format',
                        '-show_streams',
                        str(path)
                    ],
                    capture_output=True,
                    encoding='utf-8',
                    errors='ignore',
                    timeout=10,
                    startupinfo=startupinfo
                )
                
                if result.returncode == 0 and result.stdout:
                    data = json.loads(result.stdout)
                    
                    # Duration from format
                    if 'format' in data and 'duration' in data['format']:
                        try:
                            duration = float(data['format']['duration'])
                        except:
                            duration = 0
                    
                    # If not in format, get from video stream
                    if duration == 0 and 'streams' in data:
                        for s in data['streams']:
                            if s.get('codec_type') == 'video' and 'duration' in s:
                                try:
                                    duration = float(s['duration'])
                                    break
                                except:
                                    continue
                    
                    if 'streams' in data:
                        for stream in data['streams']:
                            codec_type = stream.get('codec_type', '')
                            
                            # Video stream
                            if codec_type == 'video' and not resolution:
                                width = stream.get('width', 0)
                                height = stream.get('height', 0)
                                if width and height:
                                    resolution = f"{width}x{height}"
                                codec = stream.get('codec_name', '')
                            
                            # Audio stream
                            elif codec_type == 'audio':
                                tags = stream.get('tags', {})
                                
                                language = (
                                    tags.get('language') or 
                                    tags.get('LANGUAGE') or
                                    tags.get('lang')
                                )
                                
                                title = (
                                    tags.get('title') or 
                                    tags.get('TITLE') or
                                    tags.get('handler_name')
                                )
                                
                                bitrate = None
                                if 'bit_rate' in stream:
                                    try:
                                        bitrate = int(stream['bit_rate'])
                                    except:
                                        pass
                                
                                sample_rate = None
                                if 'sample_rate' in stream:
                                    try:
                                        sample_rate = int(stream['sample_rate'])
                                    except:
                                        pass
                                
                                audio_duration = duration
                                if 'duration' in stream:
                                    try:
                                        audio_duration = float(stream['duration'])
                                    except:
                                        pass
                                
                                audio_track = {
                                    'track_type': 'embedded',
                                    'stream_index': stream.get('index', 0),
                                    'audio_file_path': None,
                                    'audio_file_name': None,
                                    'language': language,
                                    'title': title,
                                    'codec': stream.get('codec_name'),
                                    'bitrate': bitrate,
                                    'sample_rate': sample_rate,
                                    'channels': stream.get('channels'),
                                    'channel_layout': stream.get('channel_layout'),
                                    'duration': audio_duration,
                                    'file_size': 0,
                                    'is_default': 1 if stream.get('disposition', {}).get('default', 0) else 0,
                                    'match_score': 100
                                }
                                
                                embedded_audio_tracks.append(audio_track)
                            
                            # Subtitles
                            elif codec_type == 'subtitle':
                                tags = stream.get('tags', {})
                                disposition = stream.get('disposition', {})
                                
                                language = (
                                    tags.get('language') or 
                                    tags.get('LANGUAGE') or
                                    tags.get('lang')
                                )
                                
                                title = (
                                    tags.get('title') or 
                                    tags.get('TITLE') or
                                    tags.get('handler_name')
                                )
                                
                                subtitle_track = {
                                    'track_type': 'embedded',
                                    'stream_index': stream.get('index', 0),
                                    'subtitle_file_path': None,
                                    'subtitle_file_name': None,
                                    'language': language,
                                    'title': title,
                                    'codec': stream.get('codec_name'),
                                    'format': stream.get('codec_long_name'),
                                    'is_default': 1 if disposition.get('default', 0) else 0,
                                    'is_forced': 1 if disposition.get('forced', 0) else 0,
                                    'match_score': 100
                                }
                                
                                embedded_subtitle_tracks.append(subtitle_track)
                        
            except Exception as e:
                pass
        
        elapsed = time.time() - start_time
        self.stats['time_ffprobe'] += elapsed
        
        return duration, resolution, codec, file_size, embedded_audio_tracks, embedded_subtitle_tracks

    def _get_external_audio_info(self, audio_path):
        """Get information about external audio file."""
        info = {
            'duration': 0,
            'codec': None,
            'bitrate': None,
            'sample_rate': None,
            'channels': None,
            'channel_layout': None,
            'language': None,
            'title': None,
            'file_size': 0
        }
        
        try:
            info['file_size'] = audio_path.stat().st_size
        except:
            pass
        
        if self.has_ffprobe:
            try:
                startupinfo = self._get_subprocess_startupinfo()
                
                result = subprocess.run(
                    [
                        str(self.ffprobe_path),
                        '-v', 'quiet',
                        '-print_format', 'json',
                        '-show_format',
                        '-show_streams',
                        '-select_streams', 'a:0',
                        str(audio_path)
                    ],
                    capture_output=True,
                    encoding='utf-8',
                    errors='ignore',
                    timeout=5,
                    startupinfo=startupinfo
                )
                
                if result.returncode == 0 and result.stdout:
                    data = json.loads(result.stdout)
                    
                    if 'format' in data:
                        fmt = data['format']
                        if 'duration' in fmt:
                            info['duration'] = float(fmt['duration'])
                        if 'bit_rate' in fmt:
                            try:
                                info['bitrate'] = int(fmt['bit_rate'])
                            except:
                                pass
                        
                        tags = fmt.get('tags', {})
                        info['language'] = tags.get('language') or tags.get('LANGUAGE')
                        info['title'] = tags.get('title') or tags.get('TITLE')
                    
                    if 'streams' in data and data['streams']:
                        stream = data['streams'][0]
                        info['codec'] = stream.get('codec_name')
                        if 'sample_rate' in stream:
                            try:
                                info['sample_rate'] = int(stream['sample_rate'])
                            except:
                                pass
                        info['channels'] = stream.get('channels')
                        info['channel_layout'] = stream.get('channel_layout')
                        
                        stream_tags = stream.get('tags', {})
                        if not info['language']:
                            info['language'] = stream_tags.get('language') or stream_tags.get('LANGUAGE')
                        if not info['title']:
                            info['title'] = stream_tags.get('title') or stream_tags.get('TITLE')
                        
            except:
                pass
        
        return info

    def _normalize_name(self, name):
        """Normalize filename for comparison."""
        name = Path(name).stem
        name = name.lower()
        name = re.sub(r'[_\-\.\[\]\(\)\{\}]', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def _extract_episode_number(self, name):
        """Extract episode/lesson number from filename."""
        name = Path(name).stem
        
        patterns = [
            r'(?:episode|ep|e|урок|lesson|part|часть|глава|chapter|ch)[\s\.\-_]*(\d+)',
            r'^(\d+)[\s\.\-_]',
            r'[\s\.\-_](\d+)[\s\.\-_]',
            r'[\s\.\-_](\d+)$',
            r's\d+e(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None

    def _calculate_match_score(self, video_name, audio_name):
        """Calculate match score of external audio to video."""
        score = 0
        
        video_norm = self._normalize_name(video_name)
        audio_norm = self._normalize_name(audio_name)
        
        # Exact name match
        if video_norm == audio_norm:
            score += 100
        else:
            # One name contains the other
            if video_norm in audio_norm or audio_norm in video_norm:
                score += 50
            
            # Common prefix
            min_len = min(len(video_norm), len(audio_norm))
            if min_len > 0:
                common_prefix = 0
                for i in range(min_len):
                    if video_norm[i] == audio_norm[i]:
                        common_prefix += 1
                    else:
                        break
                score += int(common_prefix / min_len * 30)
        
        # Episode number match
        video_ep = self._extract_episode_number(video_name)
        audio_ep = self._extract_episode_number(audio_name)
        if video_ep is not None and audio_ep is not None:
            if video_ep == audio_ep:
                score += 40
        
        # Language tags
        lang_patterns = [
            r'[\[\(]?(rus|russian|ru|рус|русский)[\]\)]?',
            r'[\[\(]?(eng|english|en|англ|английский)[\]\)]?',
            r'[\[\(]?(ukr|ukrainian|ua|укр|украинский)[\]\)]?',
        ]
        
        for pattern in lang_patterns:
            if re.search(pattern, audio_name, re.IGNORECASE):
                score += 5
                break
        
        return score

    def _find_external_audio(self, video_file, folder):
        """Find external audio tracks matching video file."""
        external_audio = []
        
        try:
            audio_files = [
                f for f in folder.iterdir()
                if f.is_file() and f.suffix.lower() in self.audio_extensions
            ]
            
            if not audio_files:
                return []
            
            video_name = video_file.name
            
            for audio_file in audio_files:
                audio_name = audio_file.name
                audio_stem = audio_file.stem.lower()
                
                audio_info = self._get_external_audio_info(audio_file)
                match_score = self._calculate_match_score(video_name, audio_name)
                
                # Minimum match threshold
                if match_score >= 30:
                    language = audio_info['language']
                    if not language:
                        lang_patterns = [
                            (r'[\[\(]?(rus|russian|ru|рус)[\]\)]?', 'ru'),
                            (r'[\[\(]?(eng|english|en|англ)[\]\)]?', 'en'),
                            (r'[\[\(]?(ukr|ukrainian|ua|укр)[\]\)]?', 'uk'),
                        ]
                        for pattern, lang in lang_patterns:
                            if re.search(pattern, audio_name, re.IGNORECASE):
                                language = lang
                                break
                    
                    external_audio.append({
                        'track_type': 'external',
                        'stream_index': None,
                        'audio_file_path': str(audio_file),
                        'audio_file_name': audio_name,
                        'language': language,
                        'title': audio_info['title'] or audio_stem,
                        'codec': audio_info['codec'],
                        'bitrate': audio_info['bitrate'],
                        'sample_rate': audio_info['sample_rate'],
                        'channels': audio_info['channels'],
                        'channel_layout': audio_info['channel_layout'],
                        'duration': audio_info['duration'],
                        'file_size': audio_info['file_size'],
                        'is_default': 0,
                        'match_score': match_score
                    })
            
            # Sort by relevance
            external_audio.sort(key=lambda x: x['match_score'], reverse=True)
            
        except Exception as e:
            pass
        
        return external_audio

    def _find_external_subtitles(self, video_file, folder):
        """Find external subtitle files matching video file."""
        external_subtitles = []
        
        try:
            subtitle_files = [
                f for f in folder.iterdir()
                if f.is_file() and f.suffix.lower() in self.subtitle_extensions
            ]
            
            if not subtitle_files:
                return []
            
            video_name = video_file.name
            video_stem = video_file.stem.lower()
            
            for sub_file in subtitle_files:
                sub_name = sub_file.name
                sub_stem = sub_file.stem.lower()
                
                match_score = self._calculate_match_score(video_name, sub_name)
                
                # Also check exact name match (video.ru.srt -> video.mp4)
                if sub_stem.startswith(video_stem):
                    match_score = max(match_score, 80)
                
                # Minimum match threshold
                if match_score >= 30:
                    # Determine language from filename
                    language = None
                    lang_patterns = [
                        (r'(?:^|[\[\(._\-])(rus|russian|ru|рус)(?:$|[\]\)._\-])', 'ru'),
                        (r'(?:^|[\[\(._\-])(eng|english|en|англ)(?:$|[\]\)._\-])', 'en'),
                        (r'(?:^|[\[\(._\-])(ukr|ukrainian|ua|укр)(?:$|[\]\)._\-])', 'uk'),
                        (r'(?:^|[\[\(._\-])(jpn|japanese|ja|jp|яп)(?:$|[\]\)._\-])', 'ja'),
                        (r'(?:^|[\[\(._\-])(ger|german|de|deu|нем)(?:$|[\]\)._\-])', 'de'),
                        (r'(?:^|[\[\(._\-])(fra|french|fr|фр)(?:$|[\]\)._\-])', 'fr'),
                        (r'(?:^|[\[\(._\-])(spa|spanish|es|исп)(?:$|[\]\)._\-])', 'es'),
                        (r'(?:^|[\[\(._\-])(chi|chinese|zh|кит)(?:$|[\]\)._\-])', 'zh'),
                    ]
                    for pattern, lang in lang_patterns:
                        if re.search(pattern, sub_name, re.IGNORECASE):
                            language = lang
                            print(f"DEBUG: Found subtitle language {lang} for {sub_name}")
                            break
                    
                    # Determine if subtitles are forced
                    is_forced = 0
                    if re.search(r'(?:^|[\[\(._\-])forced(?:$|[\]\)._\-])', sub_name, re.IGNORECASE):
                        is_forced = 1
                    
                    # Codec by extension
                    ext_to_codec = {
                        '.srt': 'subrip',
                        '.ass': 'ass',
                        '.ssa': 'ass',
                        '.sub': 'subviewer',
                        '.vtt': 'webvtt',
                        '.sup': 'hdmv_pgs_subtitle',
                        '.stl': 'stl',
                        '.smi': 'sami',
                    }
                    codec = ext_to_codec.get(sub_file.suffix.lower(), sub_file.suffix[1:])
                    
                    external_subtitles.append({
                        'track_type': 'external',
                        'stream_index': None,
                        'subtitle_file_path': str(sub_file),
                        'subtitle_file_name': sub_name,
                        'language': language,
                        'title': sub_stem,
                        'codec': codec,
                        'format': sub_file.suffix[1:].upper(),
                        'is_default': 0,
                        'is_forced': is_forced,
                        'match_score': match_score
                    })
            
            # Sort by relevance
            external_subtitles.sort(key=lambda x: x['match_score'], reverse=True)
            
        except Exception as e:
            pass
        
        return external_subtitles

    def _process_video_file(self, video_file, folder, rel_path, track_number):
        """
        Process a single video file.
        
        Stages:
        1. Check cache in DB
        2. Get metadata via ffprobe
        3. Generate thumbnails
        4. Find external audio tracks
        """
        try:
            file_path_str = str(video_file)
            
            # Get existing data from DB
            existing_data = self._get_existing_video_data(file_path_str)
            saved_audio_selection = None
            
            if existing_data:
                saved_audio_selection = self._get_existing_audio_selection(existing_data['id'])
            
            # Check if file has changed
            try:
                current_file_size = video_file.stat().st_size
            except:
                current_file_size = 0
            
            file_changed = True
            if existing_data and existing_data.get('file_size') == current_file_size:
                file_changed = False
            
            # CACHING: if file has not changed
            if not file_changed and existing_data:
                duration = existing_data.get('duration', 0)
                
                # Check thumbnails
                thumbnail_path_str = existing_data.get('thumbnail_path')
                thumbnails_json = existing_data.get('thumbnails_json')
                thumb_list = []
                
                if thumbnails_json:
                    try:
                        thumb_list = json.loads(thumbnails_json)
                        if not all(Path(p).exists() for p in thumb_list) or len(thumb_list) != self.thumbnail_count:
                            # Thumbnails damaged or count mismatch - regenerate
                            # Pass None instead of existing_data to force regenerate all thumbnails
                            thumbnail_path_str, thumb_list = self._create_thumbnails_fast(
                                video_file, duration, None
                            )
                            thumbnails_json = json.dumps(thumb_list) if thumb_list else None
                        else:
                            self.stats['thumbnails_cached'] += len(thumb_list)
                    except:
                        thumbnail_path_str, thumb_list = self._create_thumbnails_fast(
                            video_file, duration, None
                        )
                        thumbnails_json = json.dumps(thumb_list) if thumb_list else None
                
                # Scan audio tracks and subtitles anyway (external ones might have changed)
                _, resolution, codec, file_size, embedded_audio, embedded_subs = self._get_video_info_with_audio_subs(video_file)
                external_audio = self._find_external_audio(video_file, folder)
                external_subs = self._find_external_subtitles(video_file, folder)
                all_audio_tracks = embedded_audio + external_audio
                all_subtitle_tracks = embedded_subs + external_subs
                
                return {
                    'folder_path': str(rel_path),
                    'file_path': file_path_str,
                    'file_name': video_file.name,
                    'track_number': track_number,
                    'duration': duration,
                    'resolution': resolution,
                    'file_size': file_size,
                    'codec': codec,
                    'thumbnail_path': thumbnail_path_str,
                    'thumbnails_json': thumbnails_json,
                    'watched_percent': existing_data.get('watched_percent', 0),
                    'last_position': existing_data.get('last_position', 0),
                    'thumb_count': len(thumb_list),
                    'audio_tracks': all_audio_tracks,
                    'audio_track_count': len(all_audio_tracks),
                    'embedded_audio_count': len(embedded_audio),
                    'external_audio_count': len(external_audio),
                    'subtitle_tracks': all_subtitle_tracks,
                    'subtitle_track_count': len(all_subtitle_tracks),
                    'embedded_subtitle_count': len(embedded_subs),
                    'external_subtitle_count': len(external_subs),
                    'saved_audio_selection': saved_audio_selection,
                    'from_cache': True
                }
            
            # FULL SCAN
            duration, resolution, codec, file_size, embedded_audio, embedded_subs = self._get_video_info_with_audio_subs(video_file)
            
            thumbnail_path_str = None
            thumbnails_json = None
            thumb_list = []
            
            if self.has_ffmpeg:
                main_thumb, thumb_list = self._create_thumbnails_fast(video_file, duration, existing_data)
                if main_thumb:
                    thumbnail_path_str = main_thumb
                if thumb_list:
                    thumbnails_json = json.dumps(thumb_list)
            
            external_audio = self._find_external_audio(video_file, folder)
            external_subs = self._find_external_subtitles(video_file, folder)
            all_audio_tracks = embedded_audio + external_audio
            all_subtitle_tracks = embedded_subs + external_subs
            
            watched_percent = existing_data.get('watched_percent', 0) if existing_data else 0
            last_position = existing_data.get('last_position', 0) if existing_data else 0
            
            return {
                'folder_path': str(rel_path),
                'file_path': file_path_str,
                'file_name': video_file.name,
                'track_number': track_number,
                'duration': duration,
                'resolution': resolution,
                'file_size': file_size,
                'codec': codec,
                'thumbnail_path': thumbnail_path_str,
                'thumbnails_json': thumbnails_json,
                'watched_percent': watched_percent,
                'last_position': last_position,
                'thumb_count': len(thumb_list),
                'audio_tracks': all_audio_tracks,
                'audio_track_count': len(all_audio_tracks),
                'embedded_audio_count': len(embedded_audio),
                'external_audio_count': len(external_audio),
                'subtitle_tracks': all_subtitle_tracks,
                'subtitle_track_count': len(all_subtitle_tracks),
                'embedded_subtitle_count': len(embedded_subs),
                'external_subtitle_count': len(external_subs),
                'saved_audio_selection': saved_audio_selection,
                'from_cache': False
            }
        except Exception as e:
            return None

    def scan_directory(self, root_path):
        """
        Main directory scanning method.
        
        Features:
        - Incremental addition (does not remove existing data)
        - Parallel video file processing
        - Thumbnail and metadata caching
        - Save user data (progress, audio selection)
        """
        total_start_time = time.time()
        
        print("\n" + "=" * 70)
        print(tr('scanner.scan_title'))
        print("=" * 70)

        root = Path(root_path)
        root_str = str(root)
        print(f"\n{tr('scanner.scan_path', path=root)}")

        if not root.exists():
            print(f"\n{tr('scanner.scan_error_not_exists')}")
            return 0, 0

        with self.db.get_connection() as conn:
            c = conn.cursor()
            
            # Statistics of existing data
            c.execute("SELECT COUNT(*) FROM folders WHERE root_path = ?", (root_str,))
            existing_folders = c.fetchone()[0]
            
            c.execute("""
                SELECT COUNT(*) FROM video_files 
                WHERE folder_path IN (SELECT path FROM folders WHERE root_path = ?)
            """, (root_str,))
            existing_videos = c.fetchone()[0]
            
            if existing_folders > 0:
                print(f"\n{tr('scanner.scan_existing_data')}")
                print(tr('scanner.scan_existing_folders', count=existing_folders))
                print(tr('scanner.scan_existing_videos', count=existing_videos))

            total_video_count = 0
            total_folder_count = 0
            new_videos = 0
            cached_videos = 0
            total_embedded_audio = 0
            total_external_audio = 0
            restored_audio_selections = 0
            total_embedded_subs = 0
            total_external_subs = 0

            # Search for folders with video
            print(f"\n{tr('scanner.scan_searching')}")
            scan_start = time.time()
            
            video_folders = []
            for item in root.rglob('*'):
                if item.is_dir():
                    # Check if there are videos in the folder itself
                    try:
                        if any(f.suffix.lower() in self.video_extensions for f in item.iterdir() if f.is_file()):
                            video_folders.append(item)
                    except:
                        continue
            
            # Also check root
            try:
                if any(f.suffix.lower() in self.video_extensions for f in root.iterdir() if f.is_file()):
                    if root not in video_folders:
                        video_folders.append(root)
            except:
                pass
            
            video_folders.sort(key=natural_sort_key)
            
            for folder in video_folders:
                try:
                    rel_path = folder.relative_to(root)
                    parent = rel_path.parent if str(rel_path.parent) != '.' else ''
                    
                    print(f"\n📁 {rel_path if str(rel_path) != '.' else folder.name}")
                    
                    # List of video files
                    video_files = sorted(
                        [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in self.video_extensions],
                        key=natural_sort_key
                    )
                    
                    video_count = len(video_files)
                    
                    # Insert/update folder
                    c.execute("""
                        INSERT INTO folders (path, parent_path, name, video_count, root_path, total_duration, total_size)
                        VALUES (?, ?, ?, ?, ?, 0, 0)
                        ON CONFLICT(path) DO UPDATE SET
                            parent_path = excluded.parent_path,
                            name = excluded.name,
                            video_count = excluded.video_count,
                            root_path = excluded.root_path,
                            last_updated = CURRENT_TIMESTAMP
                    """, (str(rel_path), str(parent), folder.name, video_count, root_str))

                    # Process video files
                    folder_start = time.time()
                    folder_duration = 0
                    folder_size = 0
                    folder_thumbs = 0
                    folder_embedded_audio = 0
                    folder_external_audio = 0
                    folder_embedded_subs = 0
                    folder_external_subs = 0
                    folder_cached = 0
                    folder_new = 0
                    
                    tasks = [(video_files[i], folder, rel_path, i + 1) 
                             for i in range(len(video_files))]
                    
                    results = []
                    
                    # Parallel processing for large folders
                    if len(video_files) > 2:
                        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                            futures = [executor.submit(self._process_video_file, *task) for task in tasks]
                            for future in as_completed(futures):
                                result = future.result()
                                if result:
                                    results.append(result)
                    else:
                        for task in tasks:
                            result = self._process_video_file(*task)
                            if result:
                                results.append(result)
                    
                    # Save results to DB
                    for result in results:
                        folder_duration += result['duration'] or 0
                        folder_size += result['file_size'] or 0
                        folder_thumbs += result['thumb_count']
                        folder_embedded_audio += result['embedded_audio_count']
                        folder_external_audio += result['external_audio_count']
                        folder_embedded_subs += result.get('embedded_subtitle_count', 0)
                        folder_external_subs += result.get('external_subtitle_count', 0)
                        
                        if result.get('from_cache'):
                            folder_cached += 1
                        else:
                            folder_new += 1
                        
                        # Upsert video
                        c.execute("""
                            INSERT INTO video_files
                            (folder_path, file_path, file_name, track_number,
                             duration, resolution, file_size, codec,
                             thumbnail_path, thumbnails_json, watched_percent, last_position,
                             audio_track_count, selected_audio_id, subtitle_track_count, selected_subtitle_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, NULL)
                            ON CONFLICT(file_path) DO UPDATE SET
                                folder_path = excluded.folder_path,
                                file_name = excluded.file_name,
                                track_number = excluded.track_number,
                                duration = excluded.duration,
                                resolution = excluded.resolution,
                                file_size = excluded.file_size,
                                codec = excluded.codec,
                                thumbnail_path = excluded.thumbnail_path,
                                thumbnails_json = excluded.thumbnails_json,
                                audio_track_count = excluded.audio_track_count,
                                subtitle_track_count = excluded.subtitle_track_count
                        """, (
                            result['folder_path'], result['file_path'], result['file_name'],
                            result['track_number'], result['duration'], result['resolution'],
                            result['file_size'], result['codec'], result['thumbnail_path'],
                            result['thumbnails_json'], result['watched_percent'], result['last_position'],
                            result['audio_track_count'], result['subtitle_track_count']
                        ))
                        
                        # Video ID
                        c.execute("SELECT id FROM video_files WHERE file_path = ?", (result['file_path'],))
                        video_id = c.fetchone()[0]
                        
                        # Update audio tracks
                        c.execute("DELETE FROM audio_tracks WHERE video_id = ?", (video_id,))
                        
                        selected_audio_id = None
                        saved_selection = result.get('saved_audio_selection')
                        
                        for audio in result['audio_tracks']:
                            c.execute("""
                                INSERT INTO audio_tracks
                                (video_id, video_file_path, track_type, stream_index,
                                 audio_file_path, audio_file_name, language, title,
                                 codec, bitrate, sample_rate, channels, channel_layout,
                                 duration, file_size, is_default, match_score)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                video_id, result['file_path'], audio['track_type'],
                                audio['stream_index'], audio['audio_file_path'],
                                audio['audio_file_name'], audio['language'], audio['title'],
                                audio['codec'], audio['bitrate'], audio['sample_rate'],
                                audio['channels'], audio['channel_layout'], audio['duration'],
                                audio['file_size'], audio['is_default'], audio['match_score']
                            ))
                            
                            audio_track_id = c.lastrowid
                            
                            # Restore selection
                            if saved_selection:
                                if audio['track_type'] == saved_selection['track_type']:
                                    if audio['track_type'] == 'embedded':
                                        if audio['stream_index'] == saved_selection['stream_index']:
                                            selected_audio_id = audio_track_id
                                    else:
                                        if audio['audio_file_path'] == saved_selection['audio_file_path']:
                                            selected_audio_id = audio_track_id
                        
                        if selected_audio_id:
                            c.execute("UPDATE video_files SET selected_audio_id = ? WHERE id = ?",
                                      (selected_audio_id, video_id))
                            restored_audio_selections += 1
                        
                        # Add subtitles
                        c.execute("DELETE FROM subtitle_tracks WHERE video_id = ?", (video_id,))
                        
                        for subtitle in result.get('subtitle_tracks', []):
                            c.execute("""
                                INSERT INTO subtitle_tracks
                                (video_id, video_file_path, track_type, stream_index,
                                 subtitle_file_path, subtitle_file_name, language, title,
                                 codec, format, is_default, is_forced, match_score)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                video_id, result['file_path'], subtitle['track_type'],
                                subtitle['stream_index'], subtitle['subtitle_file_path'],
                                subtitle['subtitle_file_name'], subtitle['language'], subtitle['title'],
                                subtitle['codec'], subtitle['format'], subtitle['is_default'],
                                subtitle['is_forced'], subtitle['match_score']
                            ))
                        
                        total_video_count += 1
                    
                    total_embedded_audio += folder_embedded_audio
                    total_external_audio += folder_external_audio
                    cached_videos += folder_cached
                    new_videos += folder_new

                    # Update folder statistics
                    c.execute("""
                        UPDATE folders SET total_duration = ?, total_size = ? WHERE path = ?
                    """, (folder_duration, folder_size, str(rel_path)))

                    # Output folder info
                    folder_time = time.time() - folder_start
                    hours = int(folder_duration // 3600)
                    minutes = int((folder_duration % 3600) // 60)
                    size_gb = folder_size / (1024**3)
                    
                    info_parts = [
                        tr('scanner.scanner_units.videos', count=video_count),
                        f"⏱ {tr('scanner.scanner_units.hours_short', hours=hours)}{tr('scanner.scanner_units.minutes_short', minutes=minutes)}",
                        f"💾 {size_gb:.1f}GB"
                    ]
                    
                    if folder_cached:
                        info_parts.append(tr('scanner.process_cached', count=folder_cached))
                    
                    if folder_embedded_audio + folder_external_audio > 0:
                        info_parts.append(tr('scanner.process_audio', embedded=folder_embedded_audio, external=folder_external_audio))
                    
                    if folder_embedded_subs + folder_external_subs > 0:
                        info_parts.append(tr('scanner.process_subs', embedded=folder_embedded_subs, external=folder_external_subs))
                    
                    # Add thumbnail info only if generated
                    thumbs_generated = self.stats['thumbnails_generated'] - (getattr(self, '_last_thumbs_count', 0))
                    self._last_thumbs_count = self.stats['thumbnails_generated']
                    if thumbs_generated > 0:
                        info_parts.append(f"🖼 {thumbs_generated}")
                    
                    info_parts.append(tr('scanner.process_time', time=f"{folder_time:.1f}"))
                    
                    print(tr('scanner.process_info', info=' | '.join(info_parts)))

                except Exception as e:
                    print(tr('scanner.process_error', error=f"{type(e).__name__}: {e}"))
                    continue

            # Create folder hierarchy
            print(f"\n{tr('scanner.hierarchy_building')}")
            
            c.execute("SELECT DISTINCT parent_path FROM folders WHERE parent_path != '' AND root_path = ?", (root_str,))
            parent_paths = [row[0] for row in c.fetchall()]
            
            added = set()
            for parent_path in parent_paths:
                current = ''
                for part in Path(parent_path).parts:
                    current = str(Path(current) / part) if current else part
                    if current not in added:
                        parent = str(Path(current).parent) if str(Path(current).parent) != '.' else ''
                        c.execute("""
                            INSERT INTO folders (path, parent_path, name, is_folder, video_count, root_path)
                            VALUES (?, ?, ?, 1, 0, ?)
                            ON CONFLICT(path) DO NOTHING
                        """, (current, parent, Path(current).name, root_str))
                        added.add(current)

            conn.commit()

        # Final statistics
        total_time = time.time() - total_start_time
        self.stats['time_total'] = total_time
        
        print("\n" + "=" * 70)
        print(tr('scanner.scan_complete_title'))
        print("=" * 70)
        
        print(f"\n{tr('scanner.stats_title')}")
        print(f"   {'─' * 40}")
        print(tr('scanner.stats_courses', count=len(video_folders)))
        print(tr('scanner.stats_videos', count=total_video_count))
        print(tr('scanner.stats_cached', count=cached_videos))
        print(tr('scanner.stats_new', count=new_videos))
        print(f"   {'─' * 40}")
        print(tr('scanner.stats_thumbs_title'))
        print(tr('scanner.stats_thumbs_generated', count=self.stats['thumbnails_generated']))
        print(tr('scanner.stats_thumbs_cached', count=self.stats['thumbnails_cached']))
        print(tr('scanner.stats_thumbs_failed', count=self.stats['thumbnails_failed']))
        print(f"   {'─' * 40}")
        print(tr('scanner.stats_audio_title'))
        print(tr('scanner.stats_audio_embedded', count=total_embedded_audio))
        print(tr('scanner.stats_audio_external', count=total_external_audio))
        print(tr('scanner.stats_audio_restored', count=restored_audio_selections))
        print(f"   {'─' * 40}")
        print(tr('scanner.stats_time_title'))
        print(tr('scanner.stats_time_ffprobe', time=f"{self.stats['time_ffprobe']:.1f}"))
        print(tr('scanner.stats_time_thumbs', time=f"{self.stats['time_thumbnails']:.1f}"))
        print(tr('scanner.stats_time_total', time=f"{total_time:.1f}"))
        
        if self.stats['thumbnails_generated'] > 0:
            avg_thumb_time = self.stats['time_thumbnails'] / self.stats['thumbnails_generated'] * 1000
            print(tr('scanner.stats_time_avg', time=f"{avg_thumb_time:.0f}"))
        
        print()

        return total_video_count, len(video_folders)


def main():
    scanner = VideoScanner()

    config = configparser.ConfigParser()
    config.read(scanner.config_file, encoding='utf-8')

    default_path = config.get('Paths', 'default_path', fallback=r'D:\Courses')

    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else default_path

    video_count, folder_count = scanner.scan_directory(path)
    
    print(tr('scanner.scanner_units.done', folder_count=folder_count, video_count=video_count))


if __name__ == '__main__':
    main()