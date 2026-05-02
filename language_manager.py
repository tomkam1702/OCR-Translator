# language_manager.py
import os
import csv
from logger import log_debug
from resource_handler import get_resource_path
from constants import RTL_LANGUAGES

class LanguageManager:
    """
    Manages language lists and code mappings for different translation services.
    Each translation service has its own separate language lists with its own language codes.
    """
    
    def __init__(self):
        """Initialize language lists and mappings."""
        # DeepL language lists
        self.deepl_source_languages = []   # List of (name, code) tuples
        self.deepl_target_languages = []   # List of (name, code) tuples
        self.deepl_source_names = []       # List of names only for UI display
        self.deepl_target_names = []       # List of names only for UI display
        
        # Gemini language lists (same as Google Translate)
        self.gemini_source_languages = []  # List of (name, code) tuples
        self.gemini_target_languages = []  # List of (name, code) tuples
        self.gemini_source_names = []      # List of names only for UI display
        self.gemini_target_names = []      # List of names only for UI display
        
        # Generic name to ISO code mapping (for display name parsing)
        self.generic_name_to_iso_code = {} # e.g., {'english': 'en', 'polish': 'pl'}
        
        # Language display names for localization
        self.language_display_names = []  # List of dicts with code, provider, english_name, polish_name

        self.load_language_lists()
        self.load_generic_name_map()
        self.load_language_display_names()
        
    def load_language_lists(self):
        """Load language lists from CSV files."""
        try:
            self._load_csv_to_list(get_resource_path('resources/deepl_trans_source.csv'), self.deepl_source_languages, self.deepl_source_names)
            self._load_csv_to_list(get_resource_path('resources/deepl_trans_target.csv'), self.deepl_target_languages, self.deepl_target_names)
            self._load_csv_to_list(get_resource_path('resources/gemini_trans_source.csv'), self.gemini_source_languages, self.gemini_source_names)
            self._load_csv_to_list(get_resource_path('resources/gemini_trans_target.csv'), self.gemini_target_languages, self.gemini_target_names)
            
            log_debug(f"Loaded language lists: DeepL Src({len(self.deepl_source_names)}), DeepL Tgt({len(self.deepl_target_names)}), Gemini Src({len(self.gemini_source_names)}), Gemini Tgt({len(self.gemini_target_names)})")
        except Exception as e:
            log_debug(f"Error loading language lists: {e}")
            self._initialize_default_languages() # Fallback

    def _load_csv_to_list(self, file_path, lang_tuple_list, name_list_only):
        """Helper to load a Name,Code CSV into a list of tuples and a list of names."""
        lang_tuple_list.clear()
        name_list_only.clear()
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row_num, row in enumerate(reader):
                    if row and len(row) == 2:
                        name, code = row[0].strip(), row[1].strip()
                        if name and code: # Ensure both are non-empty
                            lang_tuple_list.append((name, code))
                            name_list_only.append(name)
                        else:
                            log_debug(f"Skipped empty name/code in {os.path.basename(file_path)} at row {row_num+1}: {row}")
                    elif row: # Log malformed row
                        log_debug(f"Skipped malformed row in {os.path.basename(file_path)} at row {row_num+1}: {row}")

        else:
            log_debug(f"Language file not found: {file_path}")
        
        # Sort tuples and names alphabetically, special handling for "Auto" if present
        def get_sort_key(item):
            name = item[0] if isinstance(item, tuple) else item
            if name == "Auto": return "000" # Sort Auto to start
            return name
            
        lang_tuple_list.sort(key=get_sort_key)
        
        if "Auto" in name_list_only:
            name_list_only.remove("Auto")
            name_list_only.sort()
            name_list_only.insert(0, "Auto")
        else:
            name_list_only.sort()

    def load_generic_name_map(self):
        """Loads the generic language name to ISO code map from lang_codes.csv."""
        self.generic_name_to_iso_code.clear()
        file_path = get_resource_path('resources/lang_codes.csv')
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None) # Skip header row
                for row in reader:
                    if len(row) >= 2: # Need at least Language Name and 2-letter code
                        lang_name = row[0].strip().lower()
                        iso_code = row[1].strip().lower()
                        if lang_name and iso_code:
                            self.generic_name_to_iso_code[lang_name] = iso_code
            log_debug(f"Loaded {len(self.generic_name_to_iso_code)} generic language name mappings.")
        else:
            log_debug(f"Generic lang_codes.csv not found: {file_path}. Language name parsing might be limited.")
            # Populate with some common defaults if file is missing
            self.generic_name_to_iso_code.update({
                'english': 'en', 'french': 'fr', 'german': 'de', 'polish': 'pl', 
                'spanish': 'es', 'italian': 'it', 'russian': 'ru', 'chinese': 'zh',
                'japanese': 'ja', 'korean': 'ko', 'arabic': 'ar', 'portuguese': 'pt',
                'dutch': 'nl', 'swedish': 'sv', 'norwegian': 'no', 'danish': 'da',
                'finnish': 'fi', 'czech': 'cs', 'hungarian': 'hu', 'romanian': 'ro',
                'bulgarian': 'bg', 'greek': 'el', 'ukrainian': 'uk', 'turkish': 'tr'
            })


    def _initialize_default_languages(self):
        """Fallback if CSV loading fails."""
        log_debug("Initializing with minimal default language lists due to loading error.")
        
        self.deepl_source_languages = [("Auto", "auto"), ("English", "EN"), ("Polish", "PL")]
        self.deepl_source_names = ["Auto", "English", "Polish"]
        self.deepl_target_languages = [("English (British)", "EN-GB"), ("Polish", "PL")]
        self.deepl_target_names = ["English (British)", "Polish"]
        
        self.gemini_source_languages = [("Auto", "auto"), ("English", "en"), ("Polish", "pl")]
        self.gemini_source_names = ["Auto", "English", "Polish"]
        self.gemini_target_languages = [("English", "en"), ("Polish", "pl")]
        self.gemini_target_names = ["English", "Polish"]

    def get_code_from_name(self, name_to_find, service_type, lang_direction="source"):
        """Gets API code from display name for a specific service."""
        lst = None
        if service_type == 'deepl_api':
            lst = self.deepl_source_languages if lang_direction == "source" else self.deepl_target_languages
        elif service_type == 'gemini_api':
            lst = self.gemini_source_languages if lang_direction == "source" else self.gemini_target_languages
        
        if lst:
            for name, code in lst:
                if name == name_to_find:
                    return code
        return None

    def get_name_from_code(self, code_to_find, service_type, lang_direction="source"):
        """Gets display name from API code for a specific service."""
        lst = None
        if service_type == 'deepl_api':
            lst = self.deepl_source_languages if lang_direction == "source" else self.deepl_target_languages
        elif service_type == 'gemini_api':
            lst = self.gemini_source_languages if lang_direction == "source" else self.gemini_target_languages
        
        if lst:
            for name, code in lst:
                # DeepL codes can be case-sensitive in their API (e.g. EN-GB vs en-gb)
                # but comparison here should be flexible if CSV is consistent
                if code == code_to_find:
                    return name
                # Fallback for case variations if needed
                if code.lower() == code_to_find.lower():
                    return name
        return None



    def get_iso_code_from_generic_name(self, language_name_lower):
        """Gets a 2-letter ISO code from a generic language name (lowercase)."""
        return self.generic_name_to_iso_code.get(language_name_lower)

    def load_language_display_names(self):
        """Load language display names from CSV file for localization."""
        self.language_display_names.clear()
        file_path = get_resource_path('resources/language_display_names.csv')
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader, None)  # Skip header row
                    for row in reader:
                        if len(row) >= 4:  # Need code, provider, english_name, polish_name
                            code = row[0].strip()
                            provider = row[1].strip()
                            english_name = row[2].strip()
                            polish_name = row[3].strip()
                            if code and provider and english_name and polish_name:
                                self.language_display_names.append({
                                    'code': code,
                                    'provider': provider,
                                    'english_name': english_name,
                                    'polish_name': polish_name
                                })
                log_debug(f"Loaded {len(self.language_display_names)} language display name mappings.")
            except Exception as e:
                log_debug(f"Error loading language display names: {e}")
        else:
            log_debug(f"Language display names file not found: {file_path}")

    def get_localized_language_name(self, code, provider, ui_language='english'):
        """Get localized language name for given code and provider."""
        if not code: return ""
        try:
            provider_normalized = provider.lower().replace('_api', '')
            code_lower = str(code).lower()
            for entry in self.language_display_names:
                if entry['code'].lower() == code_lower and entry['provider'].lower() == provider_normalized:
                    # Check for Polish UI language variants
                    if ui_language.lower() in ['polish', 'polski', 'pol']:
                        return entry['polish_name']
                    else:
                        return entry['english_name']
            
            # Fallback lookup if not found in language_display_names.csv
            fallback_provider = f"{provider_normalized}_api" if not provider.endswith('_api') else provider
            fallback_name = self.get_name_from_code(code, fallback_provider, "source")
            if not fallback_name:
                fallback_name = self.get_name_from_code(code, fallback_provider, "target")
                
            return fallback_name if fallback_name else code
        except Exception as e:
            log_debug(f"Error getting localized language name: {e}")
            return code

    def get_code_from_localized_name(self, localized_name, provider, ui_language='english'):
        """Get language code from localized display name for specific provider."""
        try:
            log_debug(f"Looking up code for: name='{localized_name}', provider='{provider}', ui_language='{ui_language}'")
            
            # Normalize provider name for consistent lookup
            provider_normalized = provider.lower().replace('_api', '')  # 'google_api' -> 'google'
            
            for entry in self.language_display_names:
                if entry['provider'].lower() == provider_normalized or entry['provider'] == provider:
                    # Check for Polish UI language variants
                    if ui_language.lower() in ['polish', 'polski', 'pol']:
                        if entry['polish_name'] == localized_name:
                            log_debug(f"Found match (Polish): {localized_name} -> {entry['code']}")
                            return entry['code']
                    else:
                        if entry['english_name'] == localized_name:
                            log_debug(f"Found match (English): {localized_name} -> {entry['code']}")
                            return entry['code']
            
            log_debug(f"No direct match found, trying fallback...")
            
            # For API providers, need to map provider correctly
            fallback_provider = provider
            if provider == 'deepl_api':
                fallback_provider = 'deepl_api'
            
            log_debug(f"Direct lookup failed for '{localized_name}', trying fallback with provider '{fallback_provider}'...")
            fallback_code = self.get_code_from_name(localized_name, fallback_provider, "source")
            if not fallback_code:
                fallback_code = self.get_code_from_name(localized_name, fallback_provider, "target")
            
            if fallback_code:
                log_debug(f"Fallback successful: '{localized_name}' -> '{fallback_code}'")
                return fallback_code
            
            # If still not found, log and return None instead of the display name
            log_debug(f"Could not find code for localized name '{localized_name}' with provider '{provider}' and language '{ui_language}'")
            
            # Debug: Show available names for this provider
            available_names = []
            for entry in self.language_display_names:
                if entry['provider'].lower() == provider_normalized or entry['provider'] == provider:
                    if ui_language.lower() in ['polish', 'polski', 'pol']:
                        available_names.append(entry['polish_name'])
                    else:
                        available_names.append(entry['english_name'])
            
            log_debug(f"Available {ui_language} names for {provider}: {sorted(available_names)[:10]}...")  # Show first 10
            
            return None
        except Exception as e:
            log_debug(f"Error getting code from localized name: {e}")
            return None

    def _polish_sort_key(self, text):
        """
        Generate a sort key for Polish text that respects Polish alphabetical order.
        Polish alphabet: a, ą, b, c, ć, d, e, ę, f, g, h, i, j, k, l, ł, m, n, ń, o, ó, p, q, r, s, ś, t, u, v, w, x, y, z, ź, ż
        """
        # Polish alphabet mapping to ensure correct sorting order
        polish_order = {
            'a': '01', 'ą': '02', 'b': '03', 'c': '04', 'ć': '05', 'd': '06', 
            'e': '07', 'ę': '08', 'f': '09', 'g': '10', 'h': '11', 'i': '12', 
            'j': '13', 'k': '14', 'l': '15', 'ł': '16', 'm': '17', 'n': '18', 
            'ń': '19', 'o': '20', 'ó': '21', 'p': '22', 'q': '23', 'r': '24', 
            's': '25', 'ś': '26', 't': '27', 'u': '28', 'v': '29', 'w': '30', 
            'x': '31', 'y': '32', 'z': '33', 'ź': '34', 'ż': '35'
        }
        
        result = []
        for char in text.lower():
            if char in polish_order:
                result.append(polish_order[char])
            else:
                # For non-Polish characters, use Unicode value with high prefix to sort after Polish chars
                result.append(f"99{ord(char):04d}")
        
        return ''.join(result)

    def sort_polish_names(self, names_list):
        """Sort a list of names using Polish alphabetical order."""
        try:
            return sorted(names_list, key=self._polish_sort_key)
        except Exception as e:
            log_debug(f"Error in Polish sorting, falling back to default: {e}")
            return sorted(names_list)  # Fallback to default sorting


    def is_rtl_language(self, language_code):
        """
        Check if a language code represents a right-to-left language.
        
        Args:
            language_code (str): Language code (e.g., 'fa', 'ar', 'he')
            
        Returns:
            bool: True if the language is RTL, False otherwise
        """
        if not language_code:
            return False
            
        # Normalize the language code to lowercase
        normalized_code = language_code.lower().strip()
        
        # Handle special cases and variations
        if normalized_code in ['auto', 'unknown']:
            return False
            
        # Check for common variations
        if normalized_code.startswith('ar'):  # Arabic variants (ar, ar-SA, etc.)
            return True
        elif normalized_code.startswith('fa'):  # Persian variants (fa, fa-IR, etc.)
            return True
        elif normalized_code.startswith('he'):  # Hebrew variants (he, he-IL, etc.)
            return True
        elif normalized_code in RTL_LANGUAGES:
            return True
            
        log_debug(f"LanguageManager: Language '{language_code}' is not RTL")
        return False

    def get_text_direction(self, language_code):
        """
        Get the text direction for a given language code.
        
        Args:
            language_code (str): Language code
            
        Returns:
            str: 'rtl' for right-to-left languages, 'ltr' for left-to-right languages
        """
        return 'rtl' if self.is_rtl_language(language_code) else 'ltr'