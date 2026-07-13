"""
Translator module for managing translations across the application.
"""
import json
import logging
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
            logging.warning(f"Language file not found: {lang_file}")
            return False
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            self.current_lang = lang_code
            return True
        except Exception as e:
            logging.error(f"Error loading language file: {e}")
            return False

    def get_available_languages(self):
        """Scan translations directory and return dictionary of code -> name"""
        languages = {}
        if not self.lang_dir.exists():
            return languages
        for lang_file in self.lang_dir.glob('*.json'):
            lang_code = lang_file.stem
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    languages[lang_code] = data.get('language_name', lang_code)
            except Exception as e:
                logging.error(f"Error reading language name from {lang_file.name}: {e}")
        return languages

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
