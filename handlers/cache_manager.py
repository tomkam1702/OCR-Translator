import os
import time
from logger import log_debug

class CacheManager:
    """Handles file caching operations for translation services"""
    
    def __init__(self, app):
        """Initialize with a reference to the main application
        
        Args:
            app: The main GameChangingTranslator application instance
        """
        self.app = app
        ### FIX: Add dictionaries to track file modification times.
        self._file_timestamps = {
            'deepl': 0.0,
            'gemini': 0.0
        }
        # This will store the actual in-memory cache dictionaries.
        self._in_memory_caches = {
            'deepl': self.app.deepl_cache_dict,
            'gemini': self.app.gemini_cache_dict,
        }

    def _get_cache_path(self, cache_type):
        """Helper to get the correct file path for a given cache type."""
        if cache_type == 'deepl':
            return self.app.deepl_cache_file
        elif cache_type == 'gemini':
            return self.app.gemini_cache_file
        return None

    ### FIX: This function now handles all cache types and is more robust.
    def _load_specific_file_cache(self, cache_type):
        """Loads a single cache file from disk into memory."""
        cache_file_path = self._get_cache_path(cache_type)
        memory_cache = self._in_memory_caches.get(cache_type)
        
        if not cache_file_path or memory_cache is None:
            log_debug(f"Cannot load cache for unknown type: {cache_type}")
            return

        memory_cache.clear() # Clear the existing in-memory cache before reloading

        try:
            if os.path.exists(cache_file_path):
                with open(cache_file_path, 'r', encoding='utf-8-sig') as f:
                    for line in f:
                        line = line.strip()
                        # Universal key-value separator
                        if not line or line.startswith('#') or ':==:' not in line:
                            continue
                        
                        parts = line.split(':==:', 1)
                        if len(parts) == 2:
                            full_cache_key_from_file = parts[0]
                            translated_text = parts[1]
                            
                            # Universal parsing logic for the standard key format
                            # e.g., "Gemini(CS-PL,2025-07-03 10:24:36):Original text"
                            if '(' in full_cache_key_from_file and ')' in full_cache_key_from_file:
                                try:
                                    service_part, text_part = full_cache_key_from_file.split(')', 1)
                                    service_name_from_file, lang_part_with_time = service_part.split('(', 1)
                                    lang_part = lang_part_with_time.split(',', 1)[0]
                                    source_lang, target_lang = lang_part.split('-', 1)
                                    
                                    # Clean up the key parts
                                    service_name_from_file = service_name_from_file.lower()
                                    text_part = text_part.lstrip(':')
                                    
                                    # Reconstruct the internal key format used by the application
                                    # e.g., "gemini:cs:pl:Original text"
                                    internal_cache_key = f"{service_name_from_file}:{source_lang.lower()}:{target_lang.lower()}:{text_part}"
                                    memory_cache[internal_cache_key] = translated_text
                                except (ValueError, IndexError):
                                    # Fallback for malformed lines
                                    memory_cache[full_cache_key_from_file] = translated_text
                            else:
                                # Fallback for old format lines
                                memory_cache[full_cache_key_from_file] = translated_text

                # After successful load, update the timestamp
                self._file_timestamps[cache_type] = os.path.getmtime(cache_file_path)
                log_debug(f"Loaded/Refreshed {len(memory_cache)} entries from {cache_type} file cache.")
            else:
                # If file doesn't exist, ensure timestamp is zero
                self._file_timestamps[cache_type] = 0.0

        except Exception as e:
            log_debug(f"Error loading {cache_type} file cache: {e}")

    ### FIX: `load_file_caches` now just calls the specific loader for each type.
    def load_file_caches(self):
        """Loads all cached translations from disk files into memory."""
        self._load_specific_file_cache('deepl')
        self._load_specific_file_cache('gemini')

    ### FIX: This function remains mostly the same, but the surrounding logic makes it safe.
    def save_to_file_cache(self, cache_type, cache_key, translated_text):
        """Saves a translation to the appropriate file cache with timestamp"""
        cache_file_path = self._get_cache_path(cache_type)
        memory_cache = self._in_memory_caches.get(cache_type)
        
        if cache_type == 'deepl':
            enabled_tk_var = self.app.deepl_cache_enabled
            service_name = "DeepL"
        elif cache_type == 'gemini':
            enabled_tk_var = self.app.gemini_cache_enabled
            service_name = "Gemini"
        else:
            return False

        if not cache_file_path or not enabled_tk_var:
            return False
            
        try:
            # First, ensure our in-memory cache is up-to-date before we check/save
            self.check_file_cache(cache_type, "dummy_key_to_force_reload")

            # Key parsing logic to extract original text
            parts = cache_key.split(':', 3)
            if len(parts) >= 4:
                source_lang = parts[1].upper()
                target_lang = parts[2].upper()
                original_text = parts[3]
                lang_pair = f"{source_lang}-{target_lang}"
            else:
                lang_pair = "UNK-UNK"
                original_text = cache_key

            # Check if an entry with the same source text already exists
            if os.path.exists(cache_file_path):
                try:
                    with open(cache_file_path, 'r', encoding='utf-8-sig') as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith('#') or ':==:' not in line:
                                continue
                            
                            parts_check = line.split(':==:', 1)
                            if len(parts_check) == 2:
                                full_cache_key_from_file = parts_check[0]
                                
                                # Extract source text and language pair from existing entry
                                if ')' in full_cache_key_from_file:
                                    try:
                                        # Split on ')' to separate service part and text part
                                        service_part, text_part = full_cache_key_from_file.split(')', 1)
                                        # Clean up the text part (remove leading ':')
                                        existing_source_text = text_part.lstrip(':')
                                        
                                        # Extract language pair from service part
                                        # Format: ServiceName(LANG-PAIR,timestamp)
                                        if '(' in service_part:
                                            lang_and_timestamp = service_part.split('(', 1)[1]
                                            if ',' in lang_and_timestamp:
                                                existing_lang_pair = lang_and_timestamp.split(',', 1)[0]
                                            else:
                                                existing_lang_pair = lang_and_timestamp
                                        else:
                                            existing_lang_pair = ""
                                        
                                        # FIXED: Only treat as duplicate if BOTH source text AND language pair match
                                        if existing_source_text == original_text and existing_lang_pair == lang_pair:
                                            log_debug(f"Duplicate source text and language pair ({existing_lang_pair}) found in {cache_type} file cache, skipping save: {original_text}")
                                            return False
                                    except (ValueError, IndexError):
                                        # Continue checking other lines if this one is malformed
                                        continue
                except Exception as e_check:
                    log_debug(f"Error checking for duplicates in {cache_type} file cache: {e_check}")
                    # Continue with save if we can't check for duplicates

            # Update in-memory cache
            memory_cache[cache_key] = translated_text
            
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            formatted_cache_key = f"{service_name}({lang_pair},{timestamp}):{original_text}"
            
            # Append new entry only if no duplicate was found
            with open(cache_file_path, 'a', encoding='utf-8-sig') as f:
                f.write(f"{formatted_cache_key}:==:{translated_text}\n")
            
            # Update the timestamp since we just modified the file
            self._file_timestamps[cache_type] = os.path.getmtime(cache_file_path)
            log_debug(f"Added new translation to {cache_type} file cache: {original_text}")
            
            return True
        except Exception as e_stfc:
            log_debug(f"Error saving to {cache_type} file cache: {e_stfc}")
        
        return False

    ### FIX: The MOST IMPORTANT change is here. This function now checks for file modifications.
    def check_file_cache(self, cache_type, cache_key):
        """
        Checks if a translation exists. Reloads from disk if the file has been modified.
        """
        memory_cache = self._in_memory_caches.get(cache_type)
        cache_file_path = self._get_cache_path(cache_type)
        
        if cache_type == 'deepl':
            enabled_tk_var = self.app.deepl_cache_enabled
        elif cache_type == 'gemini':
            enabled_tk_var = self.app.gemini_cache_enabled
        else:
            return None # Unknown cache type
        
        if memory_cache is None or not enabled_tk_var:
            return None

        # --- TIMESTAMP CHECK ---
        try:
            # Get the current modification time of the file on disk
            current_mod_time = os.path.getmtime(cache_file_path)
        except FileNotFoundError:
            current_mod_time = 0.0 # File doesn't exist

        # Get the timestamp of when we last loaded this file
        last_load_time = self._file_timestamps.get(cache_type, 0.0)

        # If file on disk is newer than our in-memory version, reload it
        if current_mod_time > last_load_time:
            log_debug(f"Cache file '{cache_file_path}' has been modified. Reloading...")
            self._load_specific_file_cache(cache_type)

        # Now, perform the check against the fresh (or existing) in-memory cache
        return memory_cache.get(cache_key)
    
    ### FIX: Clear_file_caches must also reset the timestamps.
    def clear_file_caches(self):
        """Clears both in-memory and on-disk file caches and resets timestamps."""
        try:
            for cache_type in ['deepl', 'gemini']:
                memory_cache = self._in_memory_caches.get(cache_type)
                cache_file_path = self._get_cache_path(cache_type)

                if memory_cache is not None:
                    memory_cache.clear()

                if cache_file_path and os.path.exists(cache_file_path):
                    # Define a header for each file
                    header = f"# {cache_type.capitalize()} Cache File\n"
                    header += f"# Format: {cache_type.capitalize()}(SOURCE-TARGET,TIMESTAMP):text:==:translation\n"
                    with open(cache_file_path, 'w', encoding='utf-8-sig') as f:
                        f.write(header)
                
                # Reset the timestamp for this cache
                self._file_timestamps[cache_type] = 0.0
            
            log_debug("Cleared all translation file caches (in-memory, on disk, and timestamps).")
        except Exception as e_cfc:
            log_debug(f"Error clearing file caches: {e_cfc}")