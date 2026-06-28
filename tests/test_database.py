import unittest
import tempfile
import os
from pathlib import Path
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

if __name__ == "__main__":
    unittest.main()
