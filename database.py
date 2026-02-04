import sqlite3
import json
import time
from pathlib import Path
from translator import tr

class DatabaseManager:
    """
    Manages all database operations for the Video Courses Player.
    Centralizes logic from main.py and scanner.py.
    """
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.init_database()

    def get_connection(self, timeout=10):
        """Returns a connection to the SQLite database."""
        return sqlite3.connect(self.db_path, timeout=timeout)

    def init_database(self):
        """Initializes the database structure, tables, and indices."""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Folders table
            c.execute("""
                CREATE TABLE IF NOT EXISTS folders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    parent_path TEXT,
                    name TEXT NOT NULL,
                    root_path TEXT,
                    is_folder INTEGER DEFAULT 1,
                    is_expanded INTEGER DEFAULT 0,
                    video_count INTEGER DEFAULT 0,
                    total_duration REAL DEFAULT 0,
                    total_size INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Video files table
            c.execute("""
                CREATE TABLE IF NOT EXISTS video_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    folder_path TEXT NOT NULL,
                    file_path TEXT UNIQUE NOT NULL,
                    file_name TEXT,
                    track_number INTEGER,
                    duration REAL DEFAULT 0,
                    resolution TEXT,
                    file_size INTEGER DEFAULT 0,
                    codec TEXT,
                    thumbnail_path TEXT,
                    thumbnails_json TEXT,
                    watched_percent INTEGER DEFAULT 0,
                    last_position REAL DEFAULT 0,
                    audio_track_count INTEGER DEFAULT 0,
                    selected_audio_id INTEGER DEFAULT NULL,
                    subtitle_track_count INTEGER DEFAULT 0,
                    selected_subtitle_id INTEGER DEFAULT NULL,
                    volume INTEGER DEFAULT 100,
                    subtitles_enabled INTEGER DEFAULT 0,
                    FOREIGN KEY(folder_path) REFERENCES folders(path) ON DELETE CASCADE,
                    FOREIGN KEY(selected_audio_id) REFERENCES audio_tracks(id) ON DELETE SET NULL,
                    FOREIGN KEY(selected_subtitle_id) REFERENCES subtitle_tracks(id) ON DELETE SET NULL
                )
            """)

            # Audio tracks table
            c.execute("""
                CREATE TABLE IF NOT EXISTS audio_tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER NOT NULL,
                    video_file_path TEXT NOT NULL,
                    track_type TEXT DEFAULT 'embedded',
                    stream_index INTEGER,
                    audio_file_path TEXT,
                    audio_file_name TEXT,
                    language TEXT,
                    title TEXT,
                    codec TEXT,
                    bitrate INTEGER,
                    sample_rate INTEGER,
                    channels INTEGER,
                    channel_layout TEXT,
                    duration REAL DEFAULT 0,
                    file_size INTEGER DEFAULT 0,
                    is_default INTEGER DEFAULT 0,
                    match_score INTEGER DEFAULT 0,
                    FOREIGN KEY(video_id) REFERENCES video_files(id) ON DELETE CASCADE,
                    UNIQUE(video_file_path, track_type, stream_index, audio_file_path)
                )
            """)

            # Subtitle tracks table
            c.execute("""
                CREATE TABLE IF NOT EXISTS subtitle_tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER NOT NULL,
                    video_file_path TEXT NOT NULL,
                    track_type TEXT DEFAULT 'embedded',
                    stream_index INTEGER,
                    subtitle_file_path TEXT,
                    subtitle_file_name TEXT,
                    language TEXT,
                    title TEXT,
                    codec TEXT,
                    format TEXT,
                    is_default INTEGER DEFAULT 0,
                    is_forced INTEGER DEFAULT 0,
                    match_score INTEGER DEFAULT 0,
                    FOREIGN KEY(video_id) REFERENCES video_files(id) ON DELETE CASCADE,
                    UNIQUE(video_file_path, track_type, stream_index, subtitle_file_path)
                )
            """)

            # Video markers table
            c.execute("""
                CREATE TABLE IF NOT EXISTS video_markers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER NOT NULL,
                    position_seconds REAL NOT NULL,
                    label TEXT,
                    color TEXT DEFAULT '#FFD700',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(video_id) REFERENCES video_files(id) ON DELETE CASCADE
                )
            """)

            # Indices
            c.execute("CREATE INDEX IF NOT EXISTS idx_parent_path ON folders(parent_path)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_folder_path ON video_files(folder_path)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_audio_video_id ON audio_tracks(video_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_audio_video_path ON audio_tracks(video_file_path)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_subtitle_video_id ON subtitle_tracks(video_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_subtitle_video_path ON subtitle_tracks(video_file_path)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_markers_video_id ON video_markers(video_id)")
            
            # Migrations (ensure columns exist)
            c.execute("PRAGMA table_info(video_files)")
            columns = [col[1] for col in c.fetchall()]
            if 'volume' not in columns:
                c.execute("ALTER TABLE video_files ADD COLUMN volume INTEGER DEFAULT 100")
            if 'subtitles_enabled' not in columns:
                c.execute("ALTER TABLE video_files ADD COLUMN subtitles_enabled INTEGER DEFAULT 0")
            if 'thumbnails_json' not in columns:
                c.execute("ALTER TABLE video_files ADD COLUMN thumbnails_json TEXT")
            if 'audio_track_count' not in columns:
                c.execute("ALTER TABLE video_files ADD COLUMN audio_track_count INTEGER DEFAULT 0")
            if 'selected_audio_id' not in columns:
                c.execute("ALTER TABLE video_files ADD COLUMN selected_audio_id INTEGER DEFAULT NULL")
            if 'subtitle_track_count' not in columns:
                c.execute("ALTER TABLE video_files ADD COLUMN subtitle_track_count INTEGER DEFAULT 0")
            if 'selected_subtitle_id' not in columns:
                c.execute("ALTER TABLE video_files ADD COLUMN selected_subtitle_id INTEGER DEFAULT NULL")

            # Migration for video_markers
            c.execute("PRAGMA table_info(video_markers)")
            columns = [col[1] for col in c.fetchall()]
            if 'color' not in columns:
                c.execute("ALTER TABLE video_markers ADD COLUMN color TEXT DEFAULT '#FFD700'")

            conn.commit()

    def get_existing_video_data(self, file_path):
        """Retrieves existing video metadata for scanning or loading."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("""
                    SELECT * FROM video_files WHERE file_path = ?
                """, (str(file_path),))
                row = c.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error getting video data: {e}")
            return None

    def save_progress(self, file_path, position_sec, duration_sec, watched_percent=None, volume=100):
        """Updates video playback progress."""
        if duration_sec <= 0:
            return
        
        if watched_percent is None:
            watched_percent = min(100, int((position_sec / duration_sec) * 100))
            
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    UPDATE video_files 
                    SET last_position = ?, watched_percent = ?, volume = ?
                    WHERE file_path = ?
                """, (position_sec, watched_percent, volume, str(file_path)))
                conn.commit()
        except Exception as e:
            print(f"Error saving progress: {e}")

    def update_folder_expanded_state(self, path, expanded):
        """Saves folder expanded/collapsed state."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute('UPDATE folders SET is_expanded = ? WHERE path = ?', 
                          (1 if expanded else 0, str(path)))
                conn.commit()
        except Exception as e:
            print(f"Error saving folder state: {e}")

    def load_audio_tracks(self, file_path):
        """Loads all audio tracks for a given video file."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                
                # Get video_id and current selection
                c.execute("SELECT id, selected_audio_id FROM video_files WHERE file_path = ?", (str(file_path),))
                video = c.fetchone()
                if not video:
                    return [], None
                
                video_id = video['id']
                selected_id = video['selected_audio_id']
                
                c.execute("""
                    SELECT * FROM audio_tracks 
                    WHERE video_id = ? 
                    ORDER BY is_default DESC, stream_index ASC
                """, (video_id,))
                
                tracks = [dict(row) for row in c.fetchall()]
                return tracks, selected_id
        except Exception as e:
            print(f"Error loading audio tracks: {e}")
            return [], None

    def load_subtitle_tracks(self, file_path):
        """Loads all subtitle tracks for a given video file."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                
                c.execute("SELECT id, selected_subtitle_id, subtitles_enabled FROM video_files WHERE file_path = ?", (str(file_path),))
                video = c.fetchone()
                if not video:
                    return [], None, 0
                
                video_id = video['id']
                selected_id = video['selected_subtitle_id']
                enabled = video['subtitles_enabled']
                
                c.execute("""
                    SELECT * FROM subtitle_tracks 
                    WHERE video_id = ? 
                    ORDER BY is_default DESC, stream_index ASC
                """, (video_id,))
                
                tracks = [dict(row) for row in c.fetchall()]
                return tracks, selected_id, enabled
        except Exception as e:
            print(f"Error loading subtitles: {e}")
            return [], None, 0

    def get_track_info(self, table_name, track_id):
        """Retrieves details for a specific audio or subtitle track."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute(f"SELECT * FROM {table_name} WHERE id = ?", (track_id,))
                row = c.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error getting track info from {table_name}: {e}")
            return None

    def save_selected_audio(self, file_path, track_id):
        """Saves the selected audio track for a video."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE video_files SET selected_audio_id = ? WHERE file_path = ?", 
                          (track_id, str(file_path)))
                conn.commit()
        except Exception as e:
            print(f"Error saving audio selection: {e}")

    def save_selected_subtitle(self, file_path, track_id, enabled=None):
        """Saves the selected subtitle track and enabled state."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                if enabled is not None:
                    c.execute("UPDATE video_files SET selected_subtitle_id = ?, subtitles_enabled = ? WHERE file_path = ?", 
                              (track_id, 1 if enabled else 0, str(file_path)))
                else:
                    c.execute("UPDATE video_files SET selected_subtitle_id = ? WHERE file_path = ?", 
                              (track_id, str(file_path)))
                conn.commit()
        except Exception as e:
            print(f"Error saving subtitle selection: {e}")

    def update_subtitle_enabled(self, file_path, enabled):
        """Only updates the subtitle enabled/disabled state."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE video_files SET subtitles_enabled = ? WHERE file_path = ?", 
                          (1 if enabled else 0, str(file_path)))
                conn.commit()
        except Exception as e:
            print(f"Error updating subtitle state: {e}")

    def get_courses(self):
        """Loads all data for the library view."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                
                # Get all folders
                c.execute("SELECT * FROM folders ORDER BY path")
                folders = [dict(row) for row in c.fetchall()]
                
                # Get all videos
                c.execute("SELECT * FROM video_files ORDER BY folder_path, track_number, file_name")
                videos = [dict(row) for row in c.fetchall()]
                
                return folders, videos
        except Exception as e:
            print(f"Error loading courses: {e}")
            return [], []

    def clear_all_metadata(self):
        """Truncates all tables except for configuration if any."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM subtitle_tracks")
                c.execute("DELETE FROM audio_tracks")
                c.execute("DELETE FROM video_files")
                c.execute("DELETE FROM folders")
                conn.commit()
                return True
        except Exception as e:
            print(f"Error clearing metadata: {e}")
            return False

    def mark_video_as_watched(self, file_path):
        """Marks a video as fully watched."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute('UPDATE video_files SET watched_percent = 100, last_position = 0 WHERE file_path = ?', 
                          (str(file_path),))
                conn.commit()
        except Exception as e:
            print(f"Error marking as watched: {e}")

    def mark_folder_as_watched(self, folder_path):
        """Marks all videos in a folder as fully watched."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute('UPDATE video_files SET watched_percent = 100, last_position = 0 WHERE folder_path = ?', 
                          (str(folder_path),))
                conn.commit()
        except Exception as e:
            print(f"Error marking folder as watched: {e}")

    def reset_folder_progress(self, folder_path):
        """Resets playback progress for all videos in a folder."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute('UPDATE video_files SET watched_percent = 0, last_position = 0 WHERE folder_path = ?', 
                          (str(folder_path),))
                conn.commit()
        except Exception as e:
            print(f"Error resetting folder progress: {e}")

    def reset_video_progress(self, file_path):
        """Resets playback progress for a video."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute('UPDATE video_files SET watched_percent = 0, last_position = 0 WHERE file_path = ?', 
                          (str(file_path),))
                conn.commit()
        except Exception as e:
            print(f"Error resetting progress: {e}")

    def get_video_progress(self, file_path):
        """Retrieves last position and volume for a video."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute('SELECT last_position, volume FROM video_files WHERE file_path = ?', (str(file_path),))
                row = c.fetchone()
                if row:
                    return {'last_position': row['last_position'], 'volume': row['volume'] or 100}
        except Exception as e:
            print(f"Error getting video progress: {e}")
        return None

    def get_video_info(self, file_path):
        """Retrieves basic info for a video file."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute('SELECT id, file_path, folder_path FROM video_files WHERE file_path = ?', (str(file_path),))
                row = c.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error getting video info: {e}")
        return None

    # ===================== MARKERS =====================
    def add_marker(self, file_path, position_seconds, label, color="#FFD700"):
        """Adds a new marker for the video."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                # Get video_id first
                c.execute("SELECT id FROM video_files WHERE file_path = ?", (str(file_path),))
                row = c.fetchone()
                if not row:
                    return None
                
                video_id = row[0]
                c.execute("""
                    INSERT INTO video_markers (video_id, position_seconds, label, color)
                    VALUES (?, ?, ?, ?)
                """, (video_id, position_seconds, label, color))
                conn.commit()
                return c.lastrowid
        except Exception as e:
            print(f"Error adding marker: {e}")
            return None

    def get_markers(self, file_path):
        """Retrieves all markers for a video."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("""
                    SELECT m.* FROM video_markers m
                    JOIN video_files v ON m.video_id = v.id
                    WHERE v.file_path = ?
                    ORDER BY m.position_seconds ASC
                """, (str(file_path),))
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error getting markers: {e}")
            return []

    def delete_marker(self, marker_id):
        """Deletes a specific marker."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM video_markers WHERE id = ?", (marker_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error deleting marker: {e}")
            return False

    def update_marker(self, marker_id, label, color):
        """Updates a marker's label and color."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE video_markers SET label = ?, color = ? WHERE id = ?", (label, color, marker_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error updating marker: {e}")
            return False

    def close(self):
        """Placeholder for closing resources if needed (sqlite3 handles this via context managers)."""
        pass

    def vacuum(self):
        """Optimizes the database file."""
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
        except:
            pass
