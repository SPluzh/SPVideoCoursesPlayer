import os
import hashlib
from pathlib import Path
from PyQt6.QtCore import QObject, QProcess, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap

class ThumbnailProvider(QObject):
    """Utility to generate and cache video thumbnails."""
    finished = pyqtSignal(str, QPixmap) # marker_id or timestamp, pixmap

    def __init__(self, parent=None, ffmpeg_path=None):
        super().__init__(parent)
        self.ffmpeg_path = ffmpeg_path
        self.cache_dir = Path(__file__).parent / "data" / "marker_thumbs"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.process = QProcess()
        self.process.finished.connect(self._on_finished)
        self.current_request = None
        self.queue = [] # [(video_path, timestamp, cache_path, request_id), ...]

    def get_thumbnail(self, video_path, timestamp, marker_id=None):
        """Get thumbnail from cache or generate it."""
        print(f"DEBUG: ThumbnailProvider.get_thumbnail for ts={timestamp}, id={marker_id}")
        video_path = str(video_path)
        # Unique ID for cache
        video_id = hashlib.md5(video_path.encode()).hexdigest()
        target_dir = self.cache_dir / video_id
        target_dir.mkdir(exist_ok=True)
        
        # We use marker_id if available, else timestamp
        file_id = f"marker_{marker_id}" if marker_id else f"ts_{int(timestamp)}"
        cache_path = target_dir / f"{file_id}.jpg"

        if cache_path.exists():
            print(f"DEBUG: Found cached thumbnail for {file_id}")
            pixmap = QPixmap(str(cache_path))
            # Even if cached, emit signal so UI updates if it was just created/cleared
            self.finished.emit(str(file_id), pixmap)
            return pixmap

        # Generate if not exists
        self._generate(video_path, timestamp, cache_path, file_id)
        return None

    def _generate(self, video_path, timestamp, cache_path, request_id):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            print(f"DEBUG: ThumbnailProvider busy, queueing {request_id}")
            self.queue.append((video_path, timestamp, cache_path, request_id))
            return

        print(f"DEBUG: Generating thumbnail for {request_id} at {timestamp}s")
        self.current_request = (request_id, cache_path)
        
        args = [
            "-ss", str(timestamp),
            "-i", video_path,
            "-vframes", "1",
            "-vf", "scale=240:-1", # Slightly larger for better quality
            "-f", "image2",
            "-vcodec", "mjpeg",
            "-q:v", "4",
            "-y", # Overwrite
            str(cache_path)
        ]
        
        self.process.start(str(self.ffmpeg_path), args)

    def _on_finished(self):
        if self.current_request:
            req_id, path = self.current_request
            if path.exists():
                print(f"DEBUG: Thumbnail generated successfully: {req_id}")
                pixmap = QPixmap(str(path))
                self.finished.emit(str(req_id), pixmap)
            else:
                print(f"DEBUG: Thumbnail generation failed for {req_id} (file not created)")
        self.current_request = None
        
        # Process next in queue
        if self.queue:
            next_req = self.queue.pop(0)
            self._generate(*next_req)
