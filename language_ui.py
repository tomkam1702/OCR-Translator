import os
import csv
from logger import log_debug
from resource_handler import get_resource_path

class UILanguageManager:
    def __init__(self, resources_dir="resources"):
        self.resources_dir = resources_dir
        self.default_lang = "eng"
        self.current_lang = self.default_lang
        self.labels = {}
        self.available_languages = self._scan_available_languages()
        self.load_language(self.default_lang)
    
    def _scan_available_languages(self):
        """Scan the resources directory for available GUI language files"""
        languages = {}
        try:
            # Use get_resource_path to find the resources directory
            resources_path = get_resource_path(self.resources_dir)
            
            if os.path.exists(resources_path) and os.path.isdir(resources_path):
                for filename in os.listdir(resources_path):
                    if filename.startswith("gui_") and filename.endswith(".csv"):
                        lang_code = filename[4:-4]  # Extract 'eng' from 'gui_eng.csv'
                        # Map language codes to display names
                        display_name = {
                            "eng": "English",
                            "pol": "polski"
                        }.get(lang_code, lang_code.capitalize())
                        languages[lang_code] = display_name
            else:
                # If resources is not a directory, it might be the path itself
                # Try to scan the parent directory
                parent_dir = os.path.dirname(resources_path)
                if os.path.exists(parent_dir) and os.path.isdir(parent_dir):
                    for filename in os.listdir(parent_dir):
                        if filename.startswith("gui_") and filename.endswith(".csv"):
                            lang_code = filename[4:-4]
                            display_name = {
                                "eng": "English",
                                "pol": "polski"
                            }.get(lang_code, lang_code.capitalize())
                            languages[lang_code] = display_name
            
            if not languages:
                log_debug(f"No language files found in resources directory: {resources_path}")
        except Exception as e:
            log_debug(f"Error scanning for language files: {e}")
        
        return languages
    
    def get_available_languages(self):
        """Return a dictionary of available languages {code: display_name}"""
        return self.available_languages
    
    def get_language_list(self):
        """Return a list of language display names for UI dropdown"""
        return list(self.available_languages.values())
    
    def get_language_code_from_name(self, display_name):
        """Convert a display name back to language code"""
        for code, name in self.available_languages.items():
            if name == display_name:
                return code
        return self.default_lang
    
    def load_language(self, lang_code):
        """Load labels from the specified language CSV file"""
        if not lang_code:
            lang_code = self.default_lang
        
        self.current_lang = lang_code
        self.labels = {}
        
        try:
            # Use get_resource_path to find the language file
            lang_file_path = os.path.join(self.resources_dir, f"gui_{lang_code}.csv")
            lang_file = get_resource_path(lang_file_path)
            
            if os.path.exists(lang_file):
                with open(lang_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader, None)  # Skip header
                    for row in reader:
                        if len(row) >= 2:
                            key, value = row[0], row[1]
                            self.labels[key] = value.replace("\\n", "\n")
                log_debug(f"Loaded {len(self.labels)} UI labels from {lang_file}")
                
                # Log the first few labels for debugging
                sample_labels = list(self.labels.items())[:5]
                log_debug(f"Sample labels: {sample_labels}")
            else:
                log_debug(f"Language file not found: {lang_file}")
                if lang_code != self.default_lang:
                    log_debug(f"Falling back to default language: {self.default_lang}")
                    self.load_language(self.default_lang)
        except Exception as e:
            log_debug(f"Error loading language file: {e}")
            if lang_code != self.default_lang:
                log_debug(f"Falling back to default language: {self.default_lang}")
                self.load_language(self.default_lang)
    
    def get_label(self, key, default=None):
        """Get a UI label by key with fallback to default text"""
        if key in self.labels:
            return self.labels[key]
        
        if default:
            return default
        
        # If no default provided, return the key as a fallback
        return key
