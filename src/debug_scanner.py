
import re
from pathlib import Path
import sys

# Mocking the Scanner class to test the logic
class ScannerDebug:
    def __init__(self):
        self.subtitle_extensions = {'.srt', '.ass', '.ssa', '.sub', '.idx', '.vtt', '.sup', '.stl', '.smi', '.txt'}

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
        
        print(f"Comparing '{video_norm}' with '{audio_norm}'")

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
        
        # Language tags (copied from scanner.py _calculate_match_score, though not used for subs there directly?)
        # Wait, the method in scanner.py line 737 checks for audio language tags. 
        # But _find_external_subtitles calls _calculate_match_score.
        
        return score

    def _find_external_subtitles(self, video_file, folder):
        """Find external subtitle files matching video file. (Exact copy from scanner.py with print debugging)"""
        external_subtitles = []
        
        print(f"\nScanning for subtitles for: {video_file.name}")
        
        try:
            # Mocking folder.iterdir() by checking our mock file system list if provided, 
            # effectively we assume 'folder' is a list of Path objects for this test
            subtitle_files = [
                f for f in folder
                if f.is_file() and f.suffix.lower() in self.subtitle_extensions
            ]
            
            print(f"Found subtitle files in folder: {[f.name for f in subtitle_files]}")

            if not subtitle_files:
                return []
            
            video_name = video_file.name
            video_stem = video_file.stem.lower()
            
            for sub_file in subtitle_files:
                sub_name = sub_file.name
                sub_stem = sub_file.stem.lower()
                
                print(f"Checking subtitle: {sub_name}")

                match_score = self._calculate_match_score(video_name, sub_name)
                print(f"Initial match score: {match_score}")
                
                # Also check exact name match (video.ru.srt -> video.mp4)
                if sub_stem.startswith(video_stem):
                    match_score = max(match_score, 80)
                    print(f"Boosted score (startswith): {match_score}")
                
                # Minimum match threshold
                if match_score >= 30:
                    # Determine language from filename
                    language = None
                    # COPIED REGEX FROM SCANNER.PY
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
                            print(f"Found language: {lang} with pattern {pattern}")
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
            print(f"EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            pass
        
        return external_subtitles

# Test execution
def run_test():
    scanner = ScannerDebug()
    
    # Create dummy files
    video_file = Path("C:/Movies/My Video.mp4")
    
    folder_files = [
        Path("C:/Movies/My Video.srt"),
        Path("C:/Movies/My Video.en.srt"),
        Path("C:/Movies/My Video.ru.srt"),
        Path("C:/Movies/Other.srt"),
        Path("C:/Movies/My Video (eng).srt")
    ]
    
    # Mocking is_file() to always return True for our test paths within the function logic
    # But since I copied the logic which calls f.is_file(), I need to make sure my objects have it or I mock it.
    # Since they are Path objects, is_file() checks real FS.
    # So I should mock the objects.
    
    class MockPath:
        def __init__(self, path):
            self.path = path
            self.name = Path(path).name
            self.stem = Path(path).stem
            self.suffix = Path(path).suffix
        
        def is_file(self):
            return True
            
        def __str__(self):
            return str(self.path)

    video_mock = MockPath("C:/Movies/My Video.mp4")
    folder_mocks = [MockPath(p) for p in folder_files]
    
    results = scanner._find_external_subtitles(video_mock, folder_mocks)
    
    print("\nResults:")
    for res in results:
        print(f"Found: {res['subtitle_file_name']} (Lang: {res['language']}, Score: {res['match_score']})")

if __name__ == "__main__":
    run_test()
