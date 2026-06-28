import sqlite3
import json
import time
import logging
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

    def get_connection(self, timeout=30):
        """Returns a connection to the SQLite database."""
        return sqlite3.connect(self.db_path, timeout=timeout)

    def init_database(self):
        """Initializes the database structure, tables, and indices."""
        with self.get_connection() as conn:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL;")
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
                    is_available INTEGER DEFAULT 1,
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
                    is_available INTEGER DEFAULT 1,
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

            # Tags table
            c.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    color TEXT DEFAULT '#3498db'
                )
            """)

            # Video Tags Junction table
            c.execute("""
                CREATE TABLE IF NOT EXISTS video_tags (
                    video_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    FOREIGN KEY(video_id) REFERENCES video_files(id) ON DELETE CASCADE,
                    FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE,
                    PRIMARY KEY(video_id, tag_id)
                )
            """)

            # Subtitle translation cache table
            c.execute("""
                CREATE TABLE IF NOT EXISTS translations_cache (
                    original_text TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    translation TEXT NOT NULL,
                    parts_of_speech_json TEXT,
                    synonyms_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (original_text, target_lang)
                )
            """)

            # Dictionary table
            c.execute("""
                CREATE TABLE IF NOT EXISTS dictionary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT UNIQUE NOT NULL,
                    translation TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Indices
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_parent_path ON folders(parent_path)"
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_folder_path ON video_files(folder_path)"
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_audio_video_id ON audio_tracks(video_id)"
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_audio_video_path ON audio_tracks(video_file_path)"
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_subtitle_video_id ON subtitle_tracks(video_id)"
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_subtitle_video_path ON subtitle_tracks(video_file_path)"
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_markers_video_id ON video_markers(video_id)"
            )

            # Migrations (ensure columns exist)
            c.execute("PRAGMA table_info(video_files)")
            columns = [col[1] for col in c.fetchall()]
            if "volume" not in columns:
                c.execute(
                    "ALTER TABLE video_files ADD COLUMN volume INTEGER DEFAULT 100"
                )
            if "subtitles_enabled" not in columns:
                c.execute(
                    "ALTER TABLE video_files ADD COLUMN subtitles_enabled INTEGER DEFAULT 0"
                )
            if "thumbnails_json" not in columns:
                c.execute("ALTER TABLE video_files ADD COLUMN thumbnails_json TEXT")
            if "audio_track_count" not in columns:
                c.execute(
                    "ALTER TABLE video_files ADD COLUMN audio_track_count INTEGER DEFAULT 0"
                )
            if "selected_audio_id" not in columns:
                c.execute(
                    "ALTER TABLE video_files ADD COLUMN selected_audio_id INTEGER DEFAULT NULL"
                )
            if "subtitle_track_count" not in columns:
                c.execute(
                    "ALTER TABLE video_files ADD COLUMN subtitle_track_count INTEGER DEFAULT 0"
                )
            if "is_favorite" not in columns:
                c.execute(
                    "ALTER TABLE video_files ADD COLUMN is_favorite INTEGER DEFAULT 0"
                )
            if "selected_subtitle_id" not in columns:
                c.execute(
                    "ALTER TABLE video_files ADD COLUMN selected_subtitle_id INTEGER DEFAULT NULL"
                )
            if "is_available" not in columns:
                c.execute(
                    "ALTER TABLE video_files ADD COLUMN is_available INTEGER DEFAULT 1"
                )
            if "secondary_audio_id" not in columns:
                c.execute(
                    "ALTER TABLE video_files ADD COLUMN secondary_audio_id INTEGER DEFAULT NULL"
                )
            if "secondary_audio_volume" not in columns:
                c.execute(
                    "ALTER TABLE video_files ADD COLUMN secondary_audio_volume INTEGER DEFAULT 10"
                )
            if "secondary_audio_enabled" not in columns:
                c.execute(
                    "ALTER TABLE video_files ADD COLUMN secondary_audio_enabled INTEGER DEFAULT 0"
                )
            if "secondary_subtitle_id" not in columns:
                c.execute(
                    "ALTER TABLE video_files ADD COLUMN secondary_subtitle_id INTEGER DEFAULT NULL"
                )
            if "secondary_subtitle_enabled" not in columns:
                c.execute(
                    "ALTER TABLE video_files ADD COLUMN secondary_subtitle_enabled INTEGER DEFAULT 0"
                )

            # Migration for video_markers
            c.execute("PRAGMA table_info(video_markers)")
            columns = [col[1] for col in c.fetchall()]
            if "color" not in columns:
                c.execute(
                    "ALTER TABLE video_markers ADD COLUMN color TEXT DEFAULT '#FFD700'"
                )

            # Check folders table for is_available
            c.execute("PRAGMA table_info(folders)")
            folder_columns = [col[1] for col in c.fetchall()]
            if "is_available" not in folder_columns:
                c.execute(
                    "ALTER TABLE folders ADD COLUMN is_available INTEGER DEFAULT 1"
                )

            # Migration for tags table
            c.execute("PRAGMA table_info(tags)")
            tags_columns = [col[1] for col in c.fetchall()]
            if "color" not in tags_columns:
                c.execute("ALTER TABLE tags ADD COLUMN color TEXT DEFAULT '#3498db'")

            conn.commit()

    def get_existing_video_data(self, file_path):
        """Retrieves existing video metadata for scanning or loading."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute(
                    """
                    SELECT * FROM video_files WHERE file_path = ?
                """,
                    (str(file_path),),
                )
                row = c.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logging.error(f"Error getting video data: {e}", exc_info=True)
            return None

    def save_progress(
        self, file_path, position_sec, duration_sec, watched_percent=None, volume=100
    ):
        """Updates video playback progress."""
        if duration_sec <= 0:
            return

        if watched_percent is None:
            watched_percent = min(100, int((position_sec / duration_sec) * 100))

        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    UPDATE video_files 
                    SET last_position = ?, watched_percent = ?, volume = ?
                    WHERE file_path = ?
                """,
                    (position_sec, watched_percent, volume, str(file_path)),
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Error saving progress: {e}", exc_info=True)

    def update_folder_expanded_state(self, path, expanded):
        """Saves folder expanded/collapsed state."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE folders SET is_expanded = ? WHERE path = ?",
                    (1 if expanded else 0, str(path)),
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Error saving folder state: {e}", exc_info=True)

    def load_audio_tracks(self, file_path):
        """Loads all audio tracks for a given video file."""
        logging.info(f"💾 DB: Loading audio tracks for: {file_path}")
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()

                # Get video_id and current selection
                c.execute(
                    "SELECT id, selected_audio_id FROM video_files WHERE file_path = ?",
                    (str(file_path),),
                )
                video = c.fetchone()
                if not video:
                    logging.warning(
                        f"💾 DB: ⚠️ Video not found in database: {file_path}"
                    )
                    return [], None

                video_id = video["id"]
                selected_id = video["selected_audio_id"]

                logging.info(
                    f"💾 DB: Found video_id={video_id}, selected_audio_id={selected_id}"
                )

                c.execute(
                    """
                    SELECT * FROM audio_tracks 
                    WHERE video_id = ? 
                    ORDER BY is_default DESC, stream_index ASC
                """,
                    (video_id,),
                )

                tracks = [dict(row) for row in c.fetchall()]
                logging.info(f"💾 DB: Returning {len(tracks)} audio track(s)")
                return tracks, selected_id
        except Exception as e:
            logging.error(f"💾 DB: ❌ Error loading audio tracks: {e}", exc_info=True)
            return [], None

    def load_subtitle_tracks(self, file_path):
        """Loads all subtitle tracks for a given video file."""
        logging.info(f"💾 DB: Loading subtitle tracks for: {file_path}")
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()

                c.execute(
                    "SELECT id, selected_subtitle_id, subtitles_enabled FROM video_files WHERE file_path = ?",
                    (str(file_path),),
                )
                video = c.fetchone()
                if not video:
                    logging.warning(
                        f"💾 DB: ⚠️ Video not found in database: {file_path}"
                    )
                    return [], None, 0

                video_id = video["id"]
                selected_id = video["selected_subtitle_id"]
                enabled = video["subtitles_enabled"]

                logging.info(
                    f"💾 DB: Found video_id={video_id}, selected_subtitle_id={selected_id}, enabled={enabled}"
                )

                c.execute(
                    """
                    SELECT * FROM subtitle_tracks 
                    WHERE video_id = ? 
                    ORDER BY is_default DESC, stream_index ASC
                """,
                    (video_id,),
                )

                tracks = [dict(row) for row in c.fetchall()]
                logging.info(f"💾 DB: Returning {len(tracks)} subtitle track(s)")
                return tracks, selected_id, enabled
        except Exception as e:
            logging.error(f"💾 DB: ❌ Error loading subtitles: {e}", exc_info=True)
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
            logging.error(
                f"Error getting track info from {table_name}: {e}", exc_info=True
            )
            return None

    def save_selected_audio(self, file_path, track_id):
        """Saves the selected audio track for a video."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE video_files SET selected_audio_id = ? WHERE file_path = ?",
                    (track_id, str(file_path)),
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Error saving audio selection: {e}", exc_info=True)

    def save_secondary_audio(self, file_path, track_id, volume, enabled):
        """Saves secondary audio settings for a video."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    UPDATE video_files 
                    SET secondary_audio_id = ?, 
                        secondary_audio_volume = ?, 
                        secondary_audio_enabled = ?
                    WHERE file_path = ?
                """,
                    (track_id, volume, 1 if enabled else 0, str(file_path)),
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Error saving secondary audio: {e}", exc_info=True)

    def load_secondary_audio(self, file_path):
        """Loads secondary audio settings. Returns (track_id, volume, enabled)."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute(
                    """
                    SELECT secondary_audio_id, secondary_audio_volume, secondary_audio_enabled 
                    FROM video_files 
                    WHERE file_path = ?
                """,
                    (str(file_path),),
                )
                row = c.fetchone()
                if row:
                    return (
                        row["secondary_audio_id"],
                        row["secondary_audio_volume"] or 10,
                        bool(row["secondary_audio_enabled"]),
                    )
        except Exception as e:
            logging.error(f"Error loading secondary audio: {e}", exc_info=True)
        return (None, 10, False)

    def save_selected_subtitle(self, file_path, track_id, enabled=None):
        """Saves the selected subtitle track and enabled state."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                if enabled is not None:
                    c.execute(
                        "UPDATE video_files SET selected_subtitle_id = ?, subtitles_enabled = ? WHERE file_path = ?",
                        (track_id, 1 if enabled else 0, str(file_path)),
                    )
                else:
                    c.execute(
                        "UPDATE video_files SET selected_subtitle_id = ? WHERE file_path = ?",
                        (track_id, str(file_path)),
                    )
                conn.commit()
        except Exception as e:
            logging.error(f"Error saving subtitle selection: {e}", exc_info=True)

    def update_subtitle_enabled(self, file_path, enabled):
        """Only updates the subtitle enabled/disabled state."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE video_files SET subtitles_enabled = ? WHERE file_path = ?",
                    (1 if enabled else 0, str(file_path)),
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Error updating subtitle state: {e}", exc_info=True)

    def save_secondary_subtitle(self, file_path, track_id, enabled):
        """Saves secondary subtitle settings for a video."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    UPDATE video_files 
                    SET secondary_subtitle_id = ?, 
                        secondary_subtitle_enabled = ?
                    WHERE file_path = ?
                """,
                    (track_id, 1 if enabled else 0, str(file_path)),
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Error saving secondary subtitle: {e}", exc_info=True)

    def load_secondary_subtitle(self, file_path):
        """Loads secondary subtitle settings. Returns (track_id, enabled)."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute(
                    """
                    SELECT secondary_subtitle_id, secondary_subtitle_enabled 
                    FROM video_files 
                    WHERE file_path = ?
                """,
                    (str(file_path),),
                )
                row = c.fetchone()
                if row:
                    return (
                        row["secondary_subtitle_id"],
                        bool(row["secondary_subtitle_enabled"]),
                    )
        except Exception as e:
            logging.error(f"Error loading secondary subtitle: {e}", exc_info=True)
        return (None, False)

    def get_courses(self):
        """Loads all data for the library view."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()

                # Get all folders
                c.execute("SELECT * FROM folders WHERE is_available = 1 ORDER BY path")
                folders = [dict(row) for row in c.fetchall()]

                # Get all videos
                c.execute("""
                    SELECT v.*, 
                    (SELECT COUNT(*) FROM video_markers WHERE video_id = v.id) as marker_count
                    FROM video_files v 
                    WHERE v.is_available = 1
                    ORDER BY v.folder_path, v.track_number, v.file_name
                """)
                videos = [dict(row) for row in c.fetchall()]

                # Get all tags for all videos to minimize queries
                c.execute("""
                    SELECT vt.video_id, t.id, t.name, t.color 
                    FROM video_tags vt 
                    JOIN tags t ON vt.tag_id = t.id
                """)
                tags_rows = c.fetchall()

                # Get all markers for all videos
                c.execute("""
                    SELECT video_id, position_seconds, label, color 
                    FROM video_markers
                    ORDER BY position_seconds
                """)
                markers_rows = c.fetchall()

                # Map tags by video_id
                tags_map = {}
                for row in tags_rows:
                    vid = row["video_id"]
                    tag = {"id": row["id"], "name": row["name"], "color": row["color"]}
                    if vid not in tags_map:
                        tags_map[vid] = []
                    tags_map[vid].append(tag)

                # Map markers by video_id
                markers_map = {}
                for row in markers_rows:
                    vid = row["video_id"]
                    marker = {
                        "position_seconds": row["position_seconds"],
                        "label": row["label"],
                        "color": row["color"],
                    }
                    if vid not in markers_map:
                        markers_map[vid] = []
                    markers_map[vid].append(marker)

                # Attach tags and markers to videos
                for video in videos:
                    video["tags"] = tags_map.get(video["id"], [])
                    video["markers"] = markers_map.get(video["id"], [])

                return folders, videos
        except Exception as e:
            logging.error(f"Error loading courses: {e}", exc_info=True)
            return [], []

    def clear_all_metadata(self):
        """Truncates all tables except for configuration if any."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM subtitle_tracks")
                c.execute("DELETE FROM audio_tracks")
                c.execute("DELETE FROM video_markers")
                c.execute("DELETE FROM video_tags")
                c.execute("DELETE FROM tags")
                c.execute("DELETE FROM video_files")
                c.execute("DELETE FROM folders")
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error clearing metadata: {e}", exc_info=True)
            return False

    def mark_video_as_watched(self, file_path):
        """Marks a video as fully watched."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE video_files SET watched_percent = 100, last_position = duration WHERE file_path = ?",
                    (str(file_path),),
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Error marking as watched: {e}", exc_info=True)

    def mark_folder_as_watched(self, folder_path):
        """Marks all videos in a folder as fully watched."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE video_files SET watched_percent = 100, last_position = duration WHERE folder_path = ?",
                    (str(folder_path),),
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Error marking folder as watched: {e}", exc_info=True)

    def reset_folder_progress(self, folder_path):
        """Resets playback progress for all videos in a folder."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE video_files SET watched_percent = 0, last_position = 0 WHERE folder_path = ?",
                    (str(folder_path),),
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Error resetting folder progress: {e}", exc_info=True)

    def reset_video_progress(self, file_path):
        """Resets playback progress for a video."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE video_files SET watched_percent = 0, last_position = 0 WHERE file_path = ?",
                    (str(file_path),),
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Error resetting progress: {e}", exc_info=True)

    def get_video_progress(self, file_path):
        """Retrieves last position and volume for a video."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute(
                    "SELECT last_position, volume FROM video_files WHERE file_path = ?",
                    (str(file_path),),
                )
                row = c.fetchone()
                if row:
                    return {
                        "last_position": row["last_position"],
                        "volume": row["volume"] or 100,
                    }
        except Exception as e:
            logging.error(f"Error getting video progress: {e}", exc_info=True)
        return None

    def get_marker_count(self, file_path):
        """Returns the number of markers for a given video file."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                # Get video id first
                c.execute(
                    "SELECT id FROM video_files WHERE file_path = ?", (str(file_path),)
                )
                row = c.fetchone()
                if row:
                    video_id = row[0]
                    c.execute(
                        "SELECT COUNT(*) FROM video_markers WHERE video_id = ?",
                        (video_id,),
                    )
                    return c.fetchone()[0]
        except Exception as e:
            logging.error(f"Error getting marker count: {e}", exc_info=True)
        return 0

    def get_video_info(self, file_path):
        """Retrieves basic info for a video file."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute(
                    "SELECT id, file_path, folder_path FROM video_files WHERE file_path = ?",
                    (str(file_path),),
                )
                row = c.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logging.error(f"Error getting video info: {e}", exc_info=True)
        return None

    def get_folder_statistics(self, folder_path):
        """
        Calculates statistics for a folder (recursive).
        Returns a dict with:
        - total_videos, watched_videos, in_progress_videos, unwatched_videos
        - total_duration, watched_duration, remaining_duration
        - progress_percent
        """
        try:
            with self.get_connection() as conn:
                c = conn.cursor()

                # Use LIKE query to match folder and all subfolders
                # Ensure folder_path ends with separator or match exact
                # We need to escape special characters for LIKE
                escaped_path = str(folder_path).replace("%", "\\%").replace("_", "\\_")

                # Windows paths use backslashes, check if we need to handle that specifically for SQLite
                # The paths in DB seem to be stored as is.
                # Let's assume standard path separator behavior.

                c.execute(
                    """
                    SELECT 
                        COUNT(*) as total_videos,
                        SUM(CASE WHEN watched_percent >= 90 THEN 1 ELSE 0 END) as watched,
                        SUM(CASE WHEN watched_percent > 0 AND watched_percent < 90 THEN 1 ELSE 0 END) as in_progress,
                        SUM(CASE WHEN watched_percent = 0 THEN 1 ELSE 0 END) as unwatched,
                        SUM(duration) as total_duration,
                        SUM(CASE 
                            WHEN watched_percent >= 90 THEN duration 
                            ELSE last_position 
                        END) as watched_duration
                    FROM video_files 
                    WHERE folder_path = ? OR folder_path LIKE ? ESCAPE '\\'
                """,
                    (str(folder_path), f"{escaped_path}\\%"),
                )

                row = c.fetchone()
                if not row:
                    return None

                total_videos = row[0] or 0
                watched = row[1] or 0
                in_progress = row[2] or 0
                unwatched = row[3] or 0
                total_duration = row[4] or 0
                watched_duration = row[5] or 0

                remaining_duration = max(0, total_duration - watched_duration)
                progress_percent = (
                    (watched_duration / total_duration * 100)
                    if total_duration > 0
                    else 0
                )

                return {
                    "total_videos": total_videos,
                    "watched_videos": watched,
                    "in_progress_videos": in_progress,
                    "unwatched_videos": unwatched,
                    "total_duration": total_duration,
                    "watched_duration": watched_duration,
                    "remaining_duration": remaining_duration,
                    "progress_percent": int(progress_percent),
                }

        except Exception as e:
            logging.error(f"Error calculating folder stats: {e}", exc_info=True)
            return None

    # ===================== MARKERS =====================
    def add_marker(self, file_path, position_seconds, label, color="#FFD700"):
        """Adds a new marker for the video."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                # Get video_id first
                c.execute(
                    "SELECT id FROM video_files WHERE file_path = ?", (str(file_path),)
                )
                row = c.fetchone()
                if not row:
                    return None

                video_id = row[0]
                c.execute(
                    """
                    INSERT INTO video_markers (video_id, position_seconds, label, color)
                    VALUES (?, ?, ?, ?)
                """,
                    (video_id, position_seconds, label, color),
                )
                conn.commit()
                return c.lastrowid
        except Exception as e:
            logging.error(f"Error adding marker: {e}", exc_info=True)
            return None

    def get_markers(self, file_path):
        """Retrieves all markers for a video."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute(
                    """
                    SELECT m.* FROM video_markers m
                    JOIN video_files v ON m.video_id = v.id
                    WHERE v.file_path = ?
                    ORDER BY m.position_seconds ASC
                """,
                    (str(file_path),),
                )
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            logging.error(f"Error getting markers: {e}", exc_info=True)
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
            logging.error(f"Error deleting marker: {e}", exc_info=True)
            return False

    def update_marker(self, marker_id, label, color, position=None):
        """Updates a marker's label, color, and optionally position."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                if position is not None:
                    c.execute(
                        "UPDATE video_markers SET label = ?, color = ?, position_seconds = ? WHERE id = ?",
                        (label, color, position, marker_id),
                    )
                else:
                    c.execute(
                        "UPDATE video_markers SET label = ?, color = ? WHERE id = ?",
                        (label, color, marker_id),
                    )
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error updating marker: {e}", exc_info=True)
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

    # ===================== FAVORITES & TAGS =====================
    def toggle_favorite(self, file_path, new_state=None):
        """Toggles the is_favorite status of a video."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                if new_state is None:
                    # Get current status if not provided
                    c.execute(
                        "SELECT is_favorite FROM video_files WHERE file_path = ?",
                        (str(file_path),),
                    )
                    row = c.fetchone()
                    if row:
                        new_state = 0 if row[0] else 1
                    else:
                        new_state = 1  # Default to favorite if adding? Or strict?
                        # Actually logic in main.py handles defaults, here we just update.
                        # But if row doesn't exist, we can't update.
                        return False

                c.execute(
                    "UPDATE video_files SET is_favorite = ? WHERE file_path = ?",
                    (1 if new_state else 0, str(file_path)),
                )
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error toggling favorite: {e}", exc_info=True)
        return False

    def get_tags(self):
        """Retrieves all available tags."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT * FROM tags ORDER BY name")
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            logging.error(f"Error getting tags: {e}", exc_info=True)
            return []

    def create_tag(self, name, color="#3498db"):
        """Creates a new tag."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("INSERT INTO tags (name, color) VALUES (?, ?)", (name, color))
                conn.commit()
                return c.lastrowid
        except sqlite3.IntegrityError:
            return None  # Tag likely exists
        except Exception as e:
            logging.error(f"Error creating tag: {e}", exc_info=True)
            return None

    def update_tag(self, tag_id, name, color):
        """Updates an existing tag's name and color."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE tags SET name = ?, color = ? WHERE id = ?",
                    (name, color, tag_id),
                )
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error updating tag: {e}", exc_info=True)
            return False

    def delete_tag(self, tag_id):
        """Deletes a tag completely."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error deleting tag: {e}", exc_info=True)
            return False

    def add_tag_to_video(self, file_path, tag_id):
        """Associates a tag with a video."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT id FROM video_files WHERE file_path = ?", (str(file_path),)
                )
                row = c.fetchone()
                if row:
                    video_id = row[0]
                    c.execute(
                        "INSERT OR IGNORE INTO video_tags (video_id, tag_id) VALUES (?, ?)",
                        (video_id, tag_id),
                    )
                    conn.commit()
                    return True
        except Exception as e:
            logging.error(f"Error adding tag to video: {e}", exc_info=True)
            return False

    def remove_tag_from_video(self, file_path, tag_id):
        """Removes a tag from a video."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT id FROM video_files WHERE file_path = ?", (str(file_path),)
                )
                row = c.fetchone()
                if row:
                    video_id = row[0]
                    c.execute(
                        "DELETE FROM video_tags WHERE video_id = ? AND tag_id = ?",
                        (video_id, tag_id),
                    )
                    conn.commit()
                    return True
        except Exception as e:
            logging.error(f"Error removing tag from video: {e}", exc_info=True)
            return False

    def remove_all_tags_from_video(self, file_path):
        """Removes all tags associated with a video."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT id FROM video_files WHERE file_path = ?", (str(file_path),)
                )
                row = c.fetchone()
                if row:
                    video_id = row[0]
                    c.execute(
                        "DELETE FROM video_tags WHERE video_id = ?",
                        (video_id,),
                    )
                    conn.commit()
                    return True
        except Exception as e:
            logging.error(f"Error removing all tags from video: {e}", exc_info=True)
            return False

    def get_video_tags(self, file_path):
        """Gets all tags for a specific video."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute(
                    """
                    SELECT t.* FROM tags t
                    JOIN video_tags vt ON t.id = vt.tag_id
                    JOIN video_files v ON vt.video_id = v.id
                    WHERE v.file_path = ?
                    ORDER BY t.name
                """,
                    (str(file_path),),
                )
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            logging.error(f"Error getting video tags: {e}", exc_info=True)
            return []

    def mark_files_unavailable(self, root_path, except_file_paths):
        """
        Marks all video files in root_path as unavailable,
        EXCEPT those in the except_file_paths list.
        """
        try:
            with self.get_connection() as conn:
                c = conn.cursor()

                escaped_root = str(root_path).replace("%", "\\%").replace("_", "\\_")
                root_pattern = f"{escaped_root}\\%"

                c.execute(
                    "CREATE TEMP TABLE IF NOT EXISTS available_files (path TEXT PRIMARY KEY)"
                )
                c.execute("DELETE FROM available_files")

                if except_file_paths:
                    c.executemany(
                        "INSERT INTO available_files (path) VALUES (?)",
                        [(p,) for p in except_file_paths],
                    )

                # Update video_files
                # We need to join with folders to check root_path
                c.execute(
                    """
                    UPDATE video_files
                    SET is_available = 0
                    WHERE id IN (
                        SELECT v.id FROM video_files v
                        JOIN folders f ON v.folder_path = f.path
                        WHERE f.root_path = ?
                        AND v.file_path NOT IN (SELECT path FROM available_files)
                    )
                """,
                    (str(root_path),),
                )

                c.execute("DROP TABLE available_files")
                conn.commit()
        except Exception as e:
            logging.error(f"Error marking files unavailable: {e}", exc_info=True)

    def mark_folders_unavailable(self, root_path, except_folder_paths):
        """
        Marks all folders in root_path as unavailable,
        EXCEPT those in the except_folder_paths list.
        """
        try:
            with self.get_connection() as conn:
                c = conn.cursor()

                c.execute(
                    "CREATE TEMP TABLE IF NOT EXISTS available_folders (path TEXT PRIMARY KEY)"
                )
                c.execute("DELETE FROM available_folders")

                if except_folder_paths:
                    c.executemany(
                        "INSERT INTO available_folders (path) VALUES (?)",
                        [(p,) for p in except_folder_paths],
                    )

                c.execute(
                    """
                    UPDATE folders
                    SET is_available = 0
                    WHERE root_path = ?
                    AND path NOT IN (SELECT path FROM available_folders)
                """,
                    (str(root_path),),
                )

                c.execute("DROP TABLE available_folders")
                conn.commit()
        except Exception as e:
            logging.error(f"Error marking folders unavailable: {e}", exc_info=True)

    # ===================== TRANSLATIONS CACHE =====================
    def get_cached_translation(self, text, target_lang):
        """Retrieves a cached translation from the database."""
        cleaned = text.strip()
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute(
                    "SELECT translation, parts_of_speech_json, synonyms_json FROM translations_cache WHERE original_text = ? AND target_lang = ?",
                    (cleaned, target_lang)
                )
                row = c.fetchone()
                if row:
                    return {
                        "translation": row["translation"],
                        "parts_of_speech": json.loads(row["parts_of_speech_json"]) if row["parts_of_speech_json"] else {},
                        "synonyms": json.loads(row["synonyms_json"]) if row["synonyms_json"] else {}
                    }
        except Exception as e:
            logging.error(f"Error reading translation cache: {e}", exc_info=True)
        return None

    def save_cached_translation(self, text, target_lang, result_dict):
        """Saves a translation result to the database cache."""
        cleaned = text.strip()
        translation = result_dict.get("translation", "")
        parts_of_speech_json = json.dumps(result_dict.get("parts_of_speech", {}))
        synonyms_json = json.dumps(result_dict.get("synonyms", {}))
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    INSERT OR REPLACE INTO translations_cache 
                    (original_text, target_lang, translation, parts_of_speech_json, synonyms_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (cleaned, target_lang, translation, parts_of_speech_json, synonyms_json)
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Error writing to translation cache: {e}", exc_info=True)

    # ===================== USER DICTIONARY =====================
    def add_to_dictionary(self, word: str, translation: str) -> bool:
        """
        Adds a word and its translation to the user dictionary.
        Returns True if added successfully, False otherwise.
        """
        cleaned_word = word.strip()
        cleaned_trans = translation.strip()
        if not cleaned_word:
            return False
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "INSERT OR IGNORE INTO dictionary (word, translation) VALUES (?, ?)",
                    (cleaned_word, cleaned_trans)
                )
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error adding to dictionary: {e}", exc_info=True)
            return False

    def is_in_dictionary(self, word: str) -> bool:
        """Checks if a word is already in the dictionary."""
        cleaned_word = word.strip()
        if not cleaned_word:
            return False
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT 1 FROM dictionary WHERE LOWER(word) = LOWER(?)",
                    (cleaned_word,)
                )
                return c.fetchone() is not None
        except Exception as e:
            logging.error(f"Error checking dictionary: {e}", exc_info=True)
            return False

    def remove_from_dictionary(self, word: str) -> bool:
        """Removes a word from the dictionary."""
        cleaned_word = word.strip()
        if not cleaned_word:
            return False
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "DELETE FROM dictionary WHERE LOWER(word) = LOWER(?)",
                    (cleaned_word,)
                )
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error removing from dictionary: {e}", exc_info=True)
            return False
