"""
Translator module for managing translations across the application.
"""
import json
from pathlib import Path


class Translator:
    """Class for managing translations"""
    def __init__(self, lang_dir=None):
        self.lang_dir = lang_dir or Path(__file__).parent / 'resources' / 'translations'
        self.current_lang = 'ru'
        self.translations = {}
        self.load_language(self.current_lang)

    def load_language(self, lang_code):
        """Load language file"""
        lang_file = self.lang_dir / f'{lang_code}.json'
        if not lang_file.exists():
            print(f"Language file not found: {lang_file}")
            return False
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            self.current_lang = lang_code
            return True
        except Exception as e:
            print(f"Error loading language file: {e}")
            return False

    def get(self, key, **kwargs):
        keys = key.split('.')
        value = self.translations
        try:
            for k in keys:
                value = value[k]
            if kwargs:
                return value.format(**kwargs)
            return value
        except (KeyError, TypeError):
            return key

    def __call__(self, key, **kwargs):
        return self.get(key, **kwargs)


# Global translator instance
tr = Translator()
