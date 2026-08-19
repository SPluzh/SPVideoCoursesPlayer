import os
import re
import json
from pathlib import Path

def get_translation_keys_from_code(project_root):
    """Scan .py files for tr('key') or tr("key") patterns."""
    keys = set()
    # Pattern to match tr('...') or tr("...")
    # Matches tr('key'), tr('key', ...), tr("key"), etc.
    pattern = re.compile(r"tr\(['\"]([^'\"]+)['\"]")
    
    for root, _, files in os.walk(project_root):
        if "_build_" in root or ".venv" in root or "__pycache__" in root:
            continue
            
        for file in files:
            if file.endswith(".py") and file != "check_translations.py":
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        found = pattern.findall(content)
                        for key in found:
                            keys.add(key)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    
    return keys

def check_key_in_translations(key, translations):
    """Check if a dot-separated key exists in the translations dict."""
    parts = key.split('.')
    current = translations
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False
    return True

def flatten_dict(d, current_path=[]):
    """Recursively flattens a nested dictionary into a list of (dotted_key, value) tuples."""
    items = []
    for k, v in d.items():
        new_path = current_path + [k]
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_path))
        else:
            items.append((".".join(new_path), v))
    return items

def extract_placeholders(text):
    """Extract all formatting placeholders like {folders} from text."""
    if not isinstance(text, str):
        return set()
    return set(re.findall(r"\{[^{}]*\}", text))

def is_potentially_untranslated(key, value, en_value, lang_code):
    """Check if the translation is potentially left untranslated."""
    if not isinstance(value, str) or not isinstance(en_value, str):
        return False
    if key == "language_name":
        return False
        
    # Remove format placeholders like {name}, {path}, {count}
    clean_val = re.sub(r"\{[^{}]*\}", "", value)
    clean_en = re.sub(r"\{[^{}]*\}", "", en_value)

    # Exclude technical words, keyboard keys, and variables
    alphas = "".join(c for c in clean_val if c.isalpha())
    if not alphas:
        return False
        
    # Normalize and split into words
    exceptions = {
        # Brand names & Technical libraries & proper nouns
        'pureref', 'ffmpeg', 'libmpv', 'url', 'github', 'osd', 'pip', 'db', 'kb', 'mb', 'gb', 
        'arnndn', 'mpv', 'dll', 'exe', 'sp', 'video', 'videos', 'courses', 'player', 'google', 'translate',
        'dictionary', 'free', 'cache', 'subs', 'script', 'archive',
        # Shortcuts & single keys
        'l-click', 'r-click', 'space', 'shift', 'alt', 'enter', 'numpad',
        'f', 'm', 's', 'c', 'r', 'z', 'b', 'g', 'p', 't', 'e', 'w', 'h', 'x',
        # Common international terms, cognates & units
        '1.0', 'time', 'times', 'watched', 'total', 'position', 'percent', 'count', 
        'hours', 'minutes', 'sec', 'ok', 'audio', 'no', 'yes', 'auto', 'mono', 
        'deess', 'deesser', 'de-esser', 'compressor', 'denoise', 'ai', 'eta', 'ms', 'fps', 
        'status', 'id', 'gui', 'log', 'info', 'normal', 'comp', 'noise', 'fit',
        'zoom', 'color', 'text', 'pause', 'error', 'volume', 'confirmation', 'version', 'phrase',
        'adverb', 'verb'
    }
    
    words = [w.strip('{}().,;:!?-+/*%@[]_<>|\"\'').lower() for w in clean_val.split()]
    words = [w for w in words if any(c.isalpha() for c in w)]
    if words and all(w in exceptions or w.isdigit() for w in words):
        return False
        
    # Check for script-specific characters for non-Latin scripts
    if lang_code == 'ko':
        if not any(0xac00 <= ord(c) <= 0xd7a3 or 0x1100 <= ord(c) <= 0x11ff or 0x3130 <= ord(c) <= 0x318f for c in clean_val):
            return True
    elif lang_code == 'ru':
        if not any(0x0400 <= ord(c) <= 0x04ff for c in clean_val):
            return True
    elif lang_code == 'zh':
        if not any(0x4e00 <= ord(c) <= 0x9fff for c in clean_val):
            return True
    elif lang_code == 'ja':
        if not any(0x3040 <= ord(c) <= 0x309f or 0x30a0 <= ord(c) <= 0x30ff or 0x4e00 <= ord(c) <= 0x9fff for c in clean_val):
            return True
    elif lang_code == 'ar':
        if not any(0x0600 <= ord(c) <= 0x06ff for c in clean_val):
            return True
            
    # For Latin target languages (es, de, fr, pt), or general fallback: check if identical to English
    if lang_code != 'en' and clean_val.strip().lower() == clean_en.strip().lower():
        return True
        
    return False

def main():
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent
    translations_dir = project_root / 'src' / 'resources' / 'translations'
    
    print(f"Project root: {project_root}")
    print(f"Translations dir: {translations_dir}")
    print("-" * 50)
    
    # 1. Get keys from code
    code_keys = get_translation_keys_from_code(project_root)
    print(f"Found {len(code_keys)} unique translation keys in code.")
    
    # 2. Get translation files
    translation_files = list(translations_dir.glob("*.json"))
    if not translation_files:
        print("No translation files found!")
        return
        
    en_file = translations_dir / 'en.json'
    if not en_file.exists():
        print("Error: en.json is missing. It is required as the reference file.")
        return
        
    try:
        with open(en_file, 'r', encoding='utf-8') as f:
            en_translations = json.load(f)
    except Exception as e:
        print(f"Error loading en.json: {e}")
        return
        
    en_flat = dict(flatten_dict(en_translations))
    en_keys = set(en_flat.keys())
    
    # 3. Check each file
    has_errors = False
    for trans_file in translation_files:
        lang_code = trans_file.stem
        print(f"\nChecking language: {lang_code.upper()} ({trans_file.name})")
        
        try:
            with open(trans_file, 'r', encoding='utf-8') as f:
                translations = json.load(f)
        except Exception as e:
            print(f"  [ERROR] Loading failed: {e}")
            has_errors = True
            continue
            
        flat_translations = dict(flatten_dict(translations))
        trans_keys = set(flat_translations.keys())
        
        # Check 1: Keys from code
        missing_code_keys = []
        for key in sorted(code_keys):
            if not check_key_in_translations(key, translations):
                missing_code_keys.append(key)
                
        if missing_code_keys:
            print(f"  [WARNING] Found {len(missing_code_keys)} keys referenced in code but missing in file:")
            for key in missing_code_keys:
                print(f"    - {key}")
            has_errors = True
            
        # Check 2: Missing keys compared to en.json
        missing_ref_keys = en_keys - trans_keys
        if missing_ref_keys:
            print(f"  [ERROR] Found {len(missing_ref_keys)} keys present in en.json but missing in this file:")
            for key in sorted(missing_ref_keys):
                print(f"    - {key}")
            has_errors = True
            
        # Check 3: Extra keys compared to en.json
        extra_keys = trans_keys - en_keys
        if extra_keys:
            print(f"  [WARNING] Found {len(extra_keys)} extra keys not present in en.json:")
            for key in sorted(extra_keys):
                print(f"    - {key}")
                
        # Check 4: Placeholders verification & Empty values
        placeholder_mismatches = []
        empty_values = []
        
        common_keys = en_keys & trans_keys
        for key in common_keys:
            en_val = en_flat[key]
            trans_val = flat_translations[key]
            
            # Check empty
            if isinstance(trans_val, str) and not trans_val.strip() and key != "language_name":
                empty_values.append(key)
                
            # Check placeholders
            en_placeholders = extract_placeholders(en_val)
            trans_placeholders = extract_placeholders(trans_val)
            if en_placeholders != trans_placeholders:
                placeholder_mismatches.append((key, en_placeholders, trans_placeholders))
                
        # Check 5: Potentially untranslated keys
        untranslated_keys = []
        for key in common_keys:
            en_val = en_flat[key]
            trans_val = flat_translations[key]
            if is_potentially_untranslated(key, trans_val, en_val, lang_code):
                untranslated_keys.append((key, trans_val))
                
        if empty_values:
            print(f"  [ERROR] Found {len(empty_values)} empty translation values:")
            for key in sorted(empty_values):
                print(f"    - {key}")
            has_errors = True
            
        if placeholder_mismatches:
            print(f"  [ERROR] Found {len(placeholder_mismatches)} placeholder variable mismatch errors (this will crash Python formatting!):")
            for key, expected, found in sorted(placeholder_mismatches):
                print(f"    - {key}: Expected {expected}, but found {found}")
            has_errors = True
            
        if untranslated_keys:
            print(f"  [ERROR] Found {len(untranslated_keys)} untranslated keys (matching English or missing target language script):")
            for key, val in sorted(untranslated_keys):
                val_safe = repr(val).encode('ascii', 'backslashreplace').decode('ascii')
                print(f"    - {key}: {val_safe}")
            has_errors = True
            
        if not missing_code_keys and not missing_ref_keys and not empty_values and not placeholder_mismatches and not untranslated_keys:
            print("  [OK] Passed all translation checks!")
            
    if has_errors:
        print("\n[RESULT] Translation verification failed with errors.")
        exit(1)
    else:
        print("\n[RESULT] All translation files verified successfully.")

if __name__ == "__main__":
    main()
