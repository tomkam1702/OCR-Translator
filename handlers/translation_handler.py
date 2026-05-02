# handlers/translation_handler.py
import re
import os
import gc
import sys
import time
import html
import traceback
import threading
from datetime import datetime, timedelta

from logger import log_debug
from unified_translation_cache import UnifiedTranslationCache

# Import the new LLM provider classes
from .gemini_provider import GeminiProvider

# Import the new OCR provider classes
from .gemini_ocr_provider import GeminiOCRProvider

# Import other dependencies
try:
    import requests
    REQUESTS_AVAILABLE = True
    log_debug("Pre-loaded requests library")
except ImportError:
    REQUESTS_AVAILABLE = False
    log_debug("Requests library not available")


class TranslationHandler:
    def __init__(self, app):
        self.app = app
        self.unified_cache = UnifiedTranslationCache(max_size=1000)
        
        # Initialize LLM providers using the new architecture
        self.providers = {
            'gemini': GeminiProvider(app)
        }
        
        # Initialize OCR providers using the new architecture
        self.ocr_providers = {
            'gemini': GeminiOCRProvider(app)
        }
        
        # (DeepL removed in open-source edition)
        
        log_debug("Translation handler initialized with unified cache, LLM providers, and OCR providers")

    def _get_active_llm_provider(self):
        """Get the currently active LLM provider based on selected translation model."""
        selected_model = self.app.translation_model
        if selected_model == 'gemini_api':
            return self.providers.get('gemini')

        return None

    def _get_active_ocr_provider(self):
        """Get the currently active OCR provider based on selected OCR model."""
        selected_ocr_model = self.app.ocr_model
        if self.app.is_gemini_model(selected_ocr_model):
            return self.ocr_providers.get('gemini')

        return None

    def perform_ocr(self, image_data, source_lang, is_auto_detect=False):
        """Main public method for performing OCR. Delegates to the currently selected API provider."""
        provider = self._get_active_ocr_provider()
        if provider:
            try:
                # The recognize method in the base class will handle all logic
                return provider.recognize(image_data, source_lang, is_auto_detect=is_auto_detect)
            except Exception as e:
                log_debug(f"Error performing OCR with {provider.provider_name}: {e}")
                return "<EMPTY>"
        else:
            log_debug(f"No active OCR provider found for model: {self.app.ocr_model}")
            return "<EMPTY>"  # Fallback

    # === LLM SESSION MANAGEMENT ===
    def start_translation_session(self):
        provider = self._get_active_llm_provider()
        if provider:
            provider.start_translation_session()
        

    def request_end_translation_session(self):        
        provider = self._get_active_llm_provider()
        if provider:
            result = provider.request_end_translation_session()
        else:
            result = True
        
        
        return result

    # === CONTEXT MANAGEMENT ===
    def _clear_active_context(self):
        """Clear context window for the currently active LLM provider. Called when language, model, or settings change."""
        provider = self._get_active_llm_provider()
        if provider:
            provider._clear_context()
            log_debug(f"{provider.provider_name.title()} context cleared via active provider")
        else:
            log_debug("No active LLM provider found for context clearing")

    # === OCR SESSION MANAGEMENT ===
    def start_ocr_session(self):
        """Start OCR session for the active OCR provider."""
        provider = self._get_active_ocr_provider()
        if provider:
            provider.start_ocr_session()

    def request_end_ocr_session(self):
        """Request to end OCR session for the active OCR provider."""
        provider = self._get_active_ocr_provider()
        if provider:
            return provider.request_end_ocr_session()
        return True

    def force_end_sessions_on_app_close(self):
        # Context clearing is now handled automatically in base class after session end logging        
        # End translation sessions
        for provider in self.providers.values():
            try:
                provider.end_translation_session(force=True)
            except Exception as e:
                log_debug(f"Error force ending {provider.provider_name} session: {e}")
        
        # End OCR sessions
        for provider in self.ocr_providers.values():
            try:
                provider.end_ocr_session(force=True)
            except Exception as e:
                log_debug(f"Error force ending {provider.provider_name} OCR session: {e}")
        

    def translate_text_with_timeout(self, text_content, timeout_seconds=10.0, ocr_batch_number=None):
        result = [None]
        exception = [None]
        
        def translation_worker():
            try:
                result[0] = self.translate_text(text_content, ocr_batch_number)
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=translation_worker, daemon=True)
        thread.start()
        thread.join(timeout=timeout_seconds)
        
        if thread.is_alive():
            log_debug(f"Translation timed out for {timeout_seconds}s for: '{text_content}' (message suppressed)")
            return None
        
        if exception[0]:
            log_debug(f"Translation exception: {exception[0]}")
            return f"Translation error: {str(exception[0])}"
        
        return result[0]

    def translate_text(self, text_content_main, ocr_batch_number=None):
        cleaned_text_main = text_content_main.strip() if text_content_main else ""
        if not cleaned_text_main or self.is_placeholder_text(cleaned_text_main):
            return None

        translation_start_monotonic = time.monotonic()
        selected_model = self.app.translation_model
        log_debug(f"Translate request for \"{cleaned_text_main}\" using {selected_model}")
        
        source_lang, target_lang, extra_params = None, None, {}
        
        # Setup provider-specific parameters
        if selected_model == 'deepl_api':
            return "DeepL is not available in the open-source edition."
        elif selected_model == 'gemini_api':
            source_lang, target_lang = self.app.gemini_source_lang, self.app.gemini_target_lang
            provider = self.providers['gemini']
            extra_params = {"context_window": provider._get_context_window_size()}
        else:
            return f"Error: Unknown translation model '{selected_model}'"

        # 1. Check Unified Cache (In-Memory LRU)
        cached_result = self.unified_cache.get(cleaned_text_main, source_lang, target_lang, selected_model, **extra_params)
        if cached_result:
            log_debug(f"Translation \"{cleaned_text_main}\" -> \"{cached_result}\" from unified cache")
            
            # Check if file cache is enabled and save LRU result to file cache if not already there
            file_cache_enabled = False
            cache_key_for_file = None
            
            if selected_model == 'gemini_api' and self.app.gemini_cache_enabled:
                file_cache_enabled = True
                cache_key_for_file = f"gemini:{source_lang}:{target_lang}:{cleaned_text_main}"

            
            # If file cache is enabled, check if translation exists in file cache
            if file_cache_enabled and cache_key_for_file:
                provider_name = selected_model.replace('_api', '') if '_api' in selected_model else selected_model
                file_cache_result = self.app.cache_manager.check_file_cache(provider_name, cache_key_for_file)
                
                # If not in file cache, save the LRU result to file cache
                if not file_cache_result:
                    log_debug(f"LRU cache hit but file cache miss. Saving to {provider_name} file cache.")
                    self.app.cache_manager.save_to_file_cache(provider_name, cache_key_for_file, cached_result)
                else:
                    log_debug(f"Translation found in both LRU cache and {provider_name} file cache.")
            
            provider = self._get_active_llm_provider()
            if provider and not self._is_error_message(cached_result):
                # Synchronize provider language state to prevent correct labeling in context window
                provider.current_source_lang = source_lang
                provider.current_target_lang = target_lang
                provider._update_sliding_window(cleaned_text_main, cached_result)
            return self._format_dialog_text(cached_result)

        # 2. Check File Cache
        file_cache_hit = None
        if selected_model == 'gemini_api' and self.app.gemini_cache_enabled:
            key = f"gemini:{source_lang}:{target_lang}:{cleaned_text_main}"
            file_cache_hit = self.app.cache_manager.check_file_cache('gemini', key)

        
        if file_cache_hit:
            log_debug(f"Found \"{cleaned_text_main}\" in {selected_model} file cache.")
            self.unified_cache.store(cleaned_text_main, source_lang, target_lang, selected_model, file_cache_hit, **extra_params)
            
            provider = self._get_active_llm_provider()
            if provider and not self._is_error_message(file_cache_hit):
                # Synchronize provider language state to prevent correct labeling in context window
                provider.current_source_lang = source_lang
                provider.current_target_lang = target_lang
                provider._update_sliding_window(cleaned_text_main, file_cache_hit)
                
            return self._format_dialog_text(file_cache_hit)

        # 3. All Caches Miss - Perform API Call
        log_debug(f"All caches MISS for \"{cleaned_text_main}\". Calling API.")
        translated_api_text = None
        
        if selected_model == 'gemini_api':
            provider = self.providers['gemini']
            translated_api_text = provider.translate(cleaned_text_main, source_lang, target_lang, ocr_batch_number)
        
        # 4. Store successful translation
        if translated_api_text and not self._is_error_message(translated_api_text):
            if selected_model == 'gemini_api' and self.app.gemini_cache_enabled:
                cache_key_to_save = f"gemini:{source_lang}:{target_lang}:{cleaned_text_main}"
                self.app.cache_manager.save_to_file_cache('gemini', cache_key_to_save, translated_api_text)


            self.unified_cache.store(cleaned_text_main, source_lang, target_lang, selected_model, translated_api_text, **extra_params)
        
        log_debug(f"Translation \"{cleaned_text_main}\" -> \"{str(translated_api_text)}\" took {time.monotonic() - translation_start_monotonic:.3f}s")
        return self._format_dialog_text(translated_api_text)


    # === NON-LLM PROVIDER METHODS (UNCHANGED) ===


    # === UTILITY METHODS (UNCHANGED) ===
    def _format_dialog_text(self, text):
        """Format dialog text by adding line breaks before dashes that follow sentence-ending punctuation.
        
        This pre-processing ensures that dialog like:
        "- How are you? - Fine. - Great."
        
        becomes:
        "- How are you?
        - Fine.
        - Great."
        
        Args:
            text (str): The translation text to format
            
        Returns:
            str: The formatted text with proper dialog line breaks
        """
        # DEBUG: Always log when this function is called
        log_debug(f"DIALOG_FORMAT_DEBUG: _format_dialog_text called with: {repr(text)}")
        
        if not text or not isinstance(text, str):
            log_debug(f"DIALOG_FORMAT_DEBUG: Text is None or not string, returning: {repr(text)}")
            return text
        
        # Check if the text starts with any dash (more robust - no space required)
        dash_check = (text.startswith("-") or text.startswith("–") or text.startswith("—"))
        log_debug(f"DIALOG_FORMAT_DEBUG: Text starts with dash: {dash_check}")
        
        if not dash_check:
            log_debug(f"DIALOG_FORMAT_DEBUG: Text doesn't start with dash, returning unchanged")
            return text
        
        log_debug(f"DIALOG_FORMAT_DEBUG: Text starts with dash, proceeding with formatting")
        
        # Apply the formatting transformations
        formatted_text = text
        
        # Check for patterns before applying
        patterns_found = []
        patterns_to_check = [". -", ". –", ". —", "? -", "? –", "? —", "! -", "! –", "! —"]
        for pattern in patterns_to_check:
            if pattern in text:
                patterns_found.append(pattern)
        
        log_debug(f"DIALOG_FORMAT_DEBUG: Patterns found: {patterns_found}")
        
        # New rule: Handle quoted dialogue format
        dialogue_patterns = ['"-', '" "', '- "', '" - "']
        has_dialogue_quotes = formatted_text.count('"') >= 4
        has_dialogue_pattern = any(pattern in formatted_text for pattern in dialogue_patterns)

        if has_dialogue_quotes and has_dialogue_pattern:
            # Check if there are occurrences of '"-'
            if '"-' in formatted_text:
                # Replace '"-' with '-'
                formatted_text = formatted_text.replace('"-', '-')
            # Check if there are occurrences of '- "' (dash + space + quote)
            elif '- "' in formatted_text:
                # Replace '- "' with '-'
                formatted_text = formatted_text.replace('- "', '-')
            else:
                # Replace odd occurrences of '"' with '-'
                result = []
                quote_count = 0
                for char in formatted_text:
                    if char == '"':
                        quote_count += 1
                        if quote_count % 2 == 1:  # Odd occurrence (1st, 3rd, 5th, etc.)
                            result.append('-')
                        else:  # Even occurrence (2nd, 4th, 6th, etc.)
                            result.append('"')
                    else:
                        result.append(char)
                formatted_text = ''.join(result)
            
            # Remove all remaining quotes
            formatted_text = formatted_text.replace('"', '')

        # Replace ". -" with ".\n-" (period + space + hyphen)
        formatted_text = formatted_text.replace(". -", ".\n-")
        formatted_text = formatted_text.replace(". –", ".\n–")
        formatted_text = formatted_text.replace(". —", ".\n—")
        
        # Replace "? -" with "?\n-" (question mark + space + hyphen)
        formatted_text = formatted_text.replace("? -", "?\n-")
        formatted_text = formatted_text.replace("? –", "?\n–")
        formatted_text = formatted_text.replace("? —", "?\n—")
        
        # Replace "! -" with "!\n-" (exclamation mark + space + hyphen)
        formatted_text = formatted_text.replace("! -", "!\n-")
        formatted_text = formatted_text.replace("! –", "?\n–")
        formatted_text = formatted_text.replace("! —", "!\n—")
        
        if formatted_text != text:
            log_debug(f"DIALOG_FORMAT_DEBUG: Dialog formatting applied!")
            log_debug(f"DIALOG_FORMAT_DEBUG: Original: {repr(text)}")
            log_debug(f"DIALOG_FORMAT_DEBUG: Formatted: {repr(formatted_text)}")
        else:
            log_debug(f"DIALOG_FORMAT_DEBUG: No changes made to text")
        
        return formatted_text
    
    def _is_error_message(self, text):
        if not isinstance(text, str): return True
        error_indicators = ["error:", "api error", "not initialized", "missing", "failed", "not available", "not supported", "invalid result", "empty result"]
        return any(indicator in text.lower() for indicator in error_indicators)
    
    def is_placeholder_text(self, text_content):
        if not text_content: return True
        text_lower = text_content.lower().strip()
        placeholders = ["source text will appear here", "translation will appear here", "translation...", "ocr source", "source text", "loading...", "translating...", "", "translation", "...", "translation error:"]
        return text_lower in placeholders or text_lower.startswith("translation error:")

    def clear_cache(self):
        """Clear the unified translation cache."""
        self.unified_cache.clear_all()
        log_debug("Cleared unified translation cache")

    def calculate_text_similarity(self, text1_sim, text2_sim):
        if not text1_sim or not text2_sim: return 0.0
        if len(text1_sim) < 10 or len(text2_sim) < 10: 
            return 1.0 if text1_sim == text2_sim else 0.0
        
        words1_set = set(text1_sim.lower().split())
        words2_set = set(text2_sim.lower().split())
        intersection_len = len(words1_set.intersection(words2_set))
        union_len = len(words1_set.union(words2_set))
        return intersection_len / union_len if union_len > 0 else 0.0
