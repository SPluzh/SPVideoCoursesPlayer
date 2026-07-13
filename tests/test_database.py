import unittest
import tempfile
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from database import DatabaseManager

class TestDatabaseSecondarySubtitles(unittest.TestCase):
    def setUp(self):
        # Create a temporary database file
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db = DatabaseManager(self.db_path)

    def tearDown(self):
        # Close and delete the database file
        os.close(self.db_fd)
        try:
            os.remove(self.db_path)
        except OSError:
            pass

    def test_save_and_load_secondary_subtitle(self):
        folder_path = "C:/Test/Folder"
        file_path = "C:/Test/Folder/video.mp4"

        # 1. Insert folder record
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO folders (path, name) VALUES (?, ?)",
                (folder_path, "Folder")
            )
            # 2. Insert video record
            c.execute(
                "INSERT INTO video_files (folder_path, file_path, file_name) VALUES (?, ?, ?)",
                (folder_path, file_path, "video.mp4")
            )
            conn.commit()

        # 3. Initially, it should return None, False
        track_id, enabled = self.db.load_secondary_subtitle(file_path)
        self.assertIsNone(track_id)
        self.assertFalse(enabled)

        # 4. Save secondary subtitle selection
        self.db.save_secondary_subtitle(file_path, 42, True)

        # 5. Load and verify
        track_id, enabled = self.db.load_secondary_subtitle(file_path)
        self.assertEqual(track_id, 42)
        self.assertTrue(enabled)

        # 6. Save disabled state
        self.db.save_secondary_subtitle(file_path, 42, False)
        track_id, enabled = self.db.load_secondary_subtitle(file_path)
        self.assertEqual(track_id, 42)
        self.assertFalse(enabled)

        # 7. Save None track
        self.db.save_secondary_subtitle(file_path, None, False)
        track_id, enabled = self.db.load_secondary_subtitle(file_path)
        self.assertIsNone(track_id)
        self.assertFalse(enabled)

    def test_file_name_without_ext(self):
        folder_path = "C:/Test/Folder"
        file_path = "C:/Test/Folder/lesson_1.mp4"

        # 1. Simulate old schema by dropping the column
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("ALTER TABLE video_files DROP COLUMN file_name_without_ext")
            c.execute(
                "INSERT INTO folders (path, name) VALUES (?, ?)",
                (folder_path, "Folder")
            )
            # Insert video record without explicit stem
            c.execute(
                "INSERT INTO video_files (folder_path, file_path, file_name) VALUES (?, ?, ?)",
                (folder_path, file_path, "lesson_1.mp4")
            )
            conn.commit()

        # Run migration/init_database to verify it populates file_name_without_ext
        self.db.init_database()

        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT file_name_without_ext FROM video_files WHERE file_path = ?", (file_path,))
            row = c.fetchone()
            self.assertEqual(row[0], "lesson_1")

        # 2. Test update_video_path updates the stem correctly
        new_file_path = "C:/Test/Folder/lesson_1_renamed.mkv"
        self.db.update_video_path(
            old_file_path=file_path,
            new_file_path=new_file_path,
            new_folder_path=folder_path,
            new_file_name="lesson_1_renamed.mkv"
        )

        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT file_name, file_name_without_ext FROM video_files WHERE file_path = ?", (new_file_path,))
            row = c.fetchone()
            self.assertEqual(row[0], "lesson_1_renamed.mkv")
            self.assertEqual(row[1], "lesson_1_renamed")

if __name__ == "__main__":
    unittest.main()
