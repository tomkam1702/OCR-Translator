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
from marian_mt_translator import MarianMTTranslator
from unified_translation_cache import UnifiedTranslationCache
from constants import DEEPL_BETA_LANGUAGES

# Import the new LLM provider classes
from .llm_provider_base import NetworkCircuitBreaker # Used by legacy OCR (if needed)
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider

# Import the new OCR provider classes
from .gemini_ocr_provider import GeminiOCRProvider
from .openai_ocr_provider import OpenAIOCRProvider

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
            'gemini': GeminiProvider(app),
            'openai': OpenAIProvider(app)
        }
        
        # Initialize OCR providers using the new architecture
        self.ocr_providers = {
            'gemini': GeminiOCRProvider(app),
            'openai': OpenAIOCRProvider(app)
        }
        
        # DeepL-specific context storage
        self.deepl_context_window = []  # List of source texts only
        self.deepl_current_source_lang = None
        self.deepl_current_target_lang = None
        
        # DeepL logging system
        self.deepl_log_file = 'DeepL_Translation_Long_Log.txt'
        self.deepl_log_lock = threading.Lock()
        self._initialize_deepl_log_file()
        
        log_debug("Translation handler initialized with unified cache, LLM providers, and OCR providers")

    def _get_active_llm_provider(self):
        """Get the currently active LLM provider based on selected translation model."""
        selected_model = self.app.translation_model_var.get()
        if selected_model == 'gemini_api':
            return self.providers.get('gemini')
        elif self.app.is_openai_model(selected_model):
            return self.providers.get('openai')
        return None

    def _get_active_ocr_provider(self):
        """Get the currently active OCR provider based on selected OCR model."""
        selected_ocr_model = self.app.ocr_model_var.get()
        if self.app.is_gemini_model(selected_ocr_model):
            return self.ocr_providers.get('gemini')
        elif self.app.is_openai_model(selected_ocr_model):
            return self.ocr_providers.get('openai')
        return None

    def perform_ocr(self, image_data, source_lang):
        """Main public method for performing OCR. Delegates to the currently selected API provider."""
        provider = self._get_active_ocr_provider()
        if provider:
            try:
                # The recognize method in the base class will handle all logic
                return provider.recognize(image_data, source_lang)
            except Exception as e:
                log_debug(f"Error performing OCR with {provider.provider_name}: {e}")
                return "<EMPTY>"
        else:
            log_debug(f"No active OCR provider found for model: {self.app.ocr_model_var.get()}")
            return "<EMPTY>"  # Fallback

    # === LLM SESSION MANAGEMENT ===
    def start_translation_session(self):
        provider = self._get_active_llm_provider()
        if provider:
            provider.start_translation_session()
        
        # Clear DeepL context at session start
        self._clear_deepl_context()
        log_debug("DeepL context cleared for new translation session")

    def request_end_translation_session(self):        
        provider = self._get_active_llm_provider()
        if provider:
            result = provider.request_end_translation_session()
        else:
            result = True
        
        # Clear DeepL context at session end
        self._clear_deepl_context()
        log_debug("DeepL context cleared on translation session end")
        
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
                provider.end_session(force=True)
            except Exception as e:
                log_debug(f"Error force ending {provider.provider_name} OCR session: {e}")
        
        # Clear DeepL context on app close
        self._clear_deepl_context()

    # === DEEPL CONTEXT MANAGEMENT ===
    def _clear_deepl_context(self):
        """Clear DeepL context window (called on language change or session end)."""
        try:
            self.deepl_context_window = []
            self.deepl_current_source_lang = None
            self.deepl_current_target_lang = None
            log_debug("DeepL context cleared")
        except Exception as e:
            log_debug(f"Error clearing DeepL context: {e}")
    
    def _build_deepl_context(self, context_size):
        """Build DeepL context string from previous source texts only.
        
        Args:
            context_size: Number of previous subtitles to include (0-3)
            
        Returns:
            Context string or None if no context available
        """
        # Validate context size
        if not isinstance(context_size, int):
            log_debug(f"Invalid DeepL context size type: {type(context_size)}, using 0")
            return None
        
        if context_size < 0 or context_size > 3:
            log_debug(f"Invalid DeepL context size: {context_size}, clamping to 0-3")
            context_size = max(0, min(3, context_size))
        
        if context_size == 0 or not self.deepl_context_window:
            return None
        
        # Get last N source texts
        context_texts = self.deepl_context_window[-context_size:]
        
        # Simple concatenation with period separation
        # DeepL expects natural text in source language
        context_string = ". ".join(context_texts)
        
        # Ensure proper ending
        if context_string and not context_string.endswith('.'):
            context_string += '.'
        
        return context_string
    
    def _update_deepl_context(self, source_text):
        """Update DeepL context window with new source text.
        
        Args:
            source_text: New source subtitle to add to context
        """
        # Check for duplicate (same as last subtitle)
        if self.deepl_context_window and self.deepl_context_window[-1] == source_text:
            log_debug(f"Skipping DeepL context update - duplicate source text")
            return
        
        # Add new source text
        self.deepl_context_window.append(source_text)
        
        # Keep only last 5 texts (more than max context setting for flexibility)
        self.deepl_context_window = self.deepl_context_window[-5:]
        log_debug(f"DeepL context updated. Window size: {len(self.deepl_context_window)}")
    
    # === DEEPL LOGGING SYSTEM ===
    
    def _initialize_deepl_log_file(self):
        """Initialize DeepL translation log file with header if it doesn't exist."""
        try:
            if not os.path.exists(self.deepl_log_file):
                with open(self.deepl_log_file, 'w', encoding='utf-8') as f:
                    f.write("=== DEEPL TRANSLATION API CALL LOG ===\n")
                    f.write(f"Log initialized: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 50 + "\n\n")
                log_debug(f"DeepL translation log file initialized: {self.deepl_log_file}")
        except Exception as e:
            log_debug(f"Error initializing DeepL log file: {e}")
    
    def _is_deepl_logging_enabled(self):
        """Check if DeepL API logging is enabled in settings."""
        # For now, always return True. You can add a setting later if needed.
        return True
    
    def _log_deepl_translation_call(self, original_text, source_lang, target_lang, 
                                   context_size, translated_text, model_type, 
                                   call_start_time, call_duration):
        """Log DeepL translation API call with context information."""
        if not self._is_deepl_logging_enabled():
            return
        
        try:
            with self.deepl_log_lock:
                # Format timestamps
                start_timestamp = call_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                end_time = call_start_time + timedelta(seconds=call_duration)
                end_timestamp = end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                
                # Convert model type to display name
                model_display = "Next-gen" if model_type == "quality_optimized" else "Classic"
                
                # Build the log entry
                log_entry = f"""=== DEEPL TRANSLATION API CALL ===
Timestamp: {start_timestamp}
Language Pair: {source_lang} -> {target_lang}
Original Text: {original_text}

MESSAGE SENT TO DEEPL:
"""
                
                # Add context section if context was used
                if context_size > 0 and self.deepl_context_window:
                    # Get the actual subtitles that were used as context
                    context_subtitles = self.deepl_context_window[-context_size:]
                    context_count = len(context_subtitles)
                    
                    log_entry += f"""
CONTEXT ({context_count} subtitle{'s' if context_count != 1 else ''}):
"""
                    # Add each subtitle on its own line
                    for subtitle in context_subtitles:
                        if subtitle.strip():
                            log_entry += f"{subtitle}\n"
                
                # Add text to translate
                log_entry += f"""
TEXT TO TRANSLATE:
{original_text}

RESPONSE RECEIVED:
Model: {model_display}
Timestamp: {end_timestamp}
Call Duration: {call_duration:.3f} seconds

---BEGIN RESPONSE---
{translated_text}
---END RESPONSE---

========================================

"""
                
                # Write to log file
                with open(self.deepl_log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
                
                log_debug(f"DeepL translation call logged: {source_lang}->{target_lang}, Duration={call_duration:.3f}s")
        
        except Exception as e:
            log_debug(f"Error logging DeepL translation call: {e}")

    # === UNIFIED TRANSLATE METHOD ===
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
        selected_model = self.app.translation_model_var.get()
        log_debug(f"Translate request for \"{cleaned_text_main}\" using {selected_model}")
        
        source_lang, target_lang, extra_params = None, None, {}
        
        # Setup provider-specific parameters
        if selected_model == 'marianmt':
            source_lang, target_lang = self.app.marian_source_lang, self.app.marian_target_lang
            extra_params = {"beam_size": self.app.num_beams_var.get()}
        elif selected_model == 'google_api':
            source_lang, target_lang = self.app.google_source_lang, self.app.google_target_lang
        elif selected_model == 'deepl_api':
            if not self.app.DEEPL_API_AVAILABLE: return "DeepL API libraries not available."
            if not self.app.deepl_api_key_var.get().strip(): return "DeepL API key missing."
            if self.app.deepl_api_client is None:
                try:
                    import deepl
                    self.app.deepl_api_client = deepl.Translator(self.app.deepl_api_key_var.get().strip())
                except Exception as e:
                    return f"DeepL Client init error: {e}"
            source_lang, target_lang = self.app.deepl_source_lang, self.app.deepl_target_lang
            extra_params = {"model_type": self.app.deepl_model_type_var.get()}
        elif selected_model == 'gemini_api':
            source_lang, target_lang = self.app.gemini_source_lang, self.app.gemini_target_lang
            provider = self.providers['gemini']
            extra_params = {"context_window": provider._get_context_window_size()}
        elif self.app.is_openai_model(selected_model):
            source_lang, target_lang = self.app.openai_source_lang, self.app.openai_target_lang
            provider = self.providers['openai']
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
            
            if selected_model == 'gemini_api' and self.app.gemini_file_cache_var.get():
                file_cache_enabled = True
                cache_key_for_file = f"gemini:{source_lang}:{target_lang}:{cleaned_text_main}"
            elif selected_model == 'google_api' and self.app.google_file_cache_var.get():
                file_cache_enabled = True
                cache_key_for_file = f"google:{source_lang}:{target_lang}:{cleaned_text_main}"
            elif selected_model == 'deepl_api' and self.app.deepl_file_cache_var.get():
                file_cache_enabled = True
                model_type = extra_params.get('model_type', 'latency_optimized')
                cache_key_for_file = f"deepl:{source_lang}:{target_lang}:{model_type}:{cleaned_text_main}"
            elif self.app.is_openai_model(selected_model) and self.app.openai_file_cache_var.get():
                file_cache_enabled = True
                cache_key_for_file = f"openai:{source_lang}:{target_lang}:{cleaned_text_main}"
            
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
                provider._update_sliding_window(cleaned_text_main, cached_result)
            return self._format_dialog_text(cached_result)

        # 2. Check File Cache
        file_cache_hit = None
        if selected_model == 'gemini_api' and self.app.gemini_file_cache_var.get():
            key = f"gemini:{source_lang}:{target_lang}:{cleaned_text_main}"
            file_cache_hit = self.app.cache_manager.check_file_cache('gemini', key)
        elif selected_model == 'google_api' and self.app.google_file_cache_var.get():
            key = f"google:{source_lang}:{target_lang}:{cleaned_text_main}"
            file_cache_hit = self.app.cache_manager.check_file_cache('google', key)
        elif selected_model == 'deepl_api' and self.app.deepl_file_cache_var.get():
            model_type = extra_params.get('model_type', 'latency_optimized')
            key = f"deepl:{source_lang}:{target_lang}:{model_type}:{cleaned_text_main}"
            file_cache_hit = self.app.cache_manager.check_file_cache('deepl', key)
        elif self.app.is_openai_model(selected_model) and self.app.openai_file_cache_var.get():
            key = f"openai:{source_lang}:{target_lang}:{cleaned_text_main}"
            file_cache_hit = self.app.cache_manager.check_file_cache('openai', key)
        
        if file_cache_hit:
            log_debug(f"Found \"{cleaned_text_main}\" in {selected_model} file cache.")
            self.unified_cache.store(cleaned_text_main, source_lang, target_lang, selected_model, file_cache_hit, **extra_params)
            
            provider = self._get_active_llm_provider()
            if provider and not self._is_error_message(file_cache_hit):
                provider._update_sliding_window(cleaned_text_main, file_cache_hit)
                
            return self._format_dialog_text(file_cache_hit)

        # 3. All Caches Miss - Perform API Call
        log_debug(f"All caches MISS for \"{cleaned_text_main}\". Calling API.")
        translated_api_text = None
        
        if selected_model == 'marianmt':
            translated_api_text = self._marian_translate(cleaned_text_main, source_lang, target_lang, extra_params['beam_size'])
        elif selected_model == 'google_api':
            translated_api_text = self._google_translate(cleaned_text_main, source_lang, target_lang)
        elif selected_model == 'deepl_api':
            translated_api_text = self._deepl_translate(cleaned_text_main, source_lang, target_lang)
        elif selected_model == 'gemini_api':
            provider = self.providers['gemini']
            translated_api_text = provider.translate(cleaned_text_main, source_lang, target_lang, ocr_batch_number)
        elif self.app.is_openai_model(selected_model):
            provider = self.providers['openai']
            translated_api_text = provider.translate(cleaned_text_main, source_lang, target_lang, ocr_batch_number)
        
        # 4. Store successful translation
        if translated_api_text and not self._is_error_message(translated_api_text):
            if selected_model == 'gemini_api' and self.app.gemini_file_cache_var.get():
                cache_key_to_save = f"gemini:{source_lang}:{target_lang}:{cleaned_text_main}"
                self.app.cache_manager.save_to_file_cache('gemini', cache_key_to_save, translated_api_text)
            elif selected_model == 'google_api' and self.app.google_file_cache_var.get():
                cache_key_to_save = f"google:{source_lang}:{target_lang}:{cleaned_text_main}"
                self.app.cache_manager.save_to_file_cache('google', cache_key_to_save, translated_api_text)
            elif selected_model == 'deepl_api' and self.app.deepl_file_cache_var.get():
                model_type = extra_params.get('model_type', 'latency_optimized')
                cache_key_to_save = f"deepl:{source_lang}:{target_lang}:{model_type}:{cleaned_text_main}"
                self.app.cache_manager.save_to_file_cache('deepl', cache_key_to_save, translated_api_text)
            elif self.app.is_openai_model(selected_model) and self.app.openai_file_cache_var.get():
                cache_key_to_save = f"openai:{source_lang}:{target_lang}:{cleaned_text_main}"
                self.app.cache_manager.save_to_file_cache('openai', cache_key_to_save, translated_api_text)

            self.unified_cache.store(cleaned_text_main, source_lang, target_lang, selected_model, translated_api_text, **extra_params)
        
        log_debug(f"Translation \"{cleaned_text_main}\" -> \"{str(translated_api_text)}\" took {time.monotonic() - translation_start_monotonic:.3f}s")
        return self._format_dialog_text(translated_api_text)


    # === NON-LLM PROVIDER METHODS (UNCHANGED) ===
    def _google_translate(self, text_to_translate_gt, source_lang_gt, target_lang_gt):
        log_debug(f"Google Translate API call for: {text_to_translate_gt}")
        api_key_google = self.app.google_api_key_var.get().strip()
        if not api_key_google: return "Google Translate API key missing"
        if not REQUESTS_AVAILABLE: return "Requests library not available for Google Translate"
        try:
            url = "https://translation.googleapis.com/language/translate/v2"
            params = {'key': api_key_google, 'q': text_to_translate_gt, 'target': target_lang_gt, 'format': 'text'}
            if source_lang_gt and source_lang_gt.lower() != 'auto': params['source'] = source_lang_gt
            response = requests.post(url, data=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            if result and 'data' in result and 'translations' in result['data']:
                return html.unescape(result['data']['translations'][0]['translatedText'])
            return f"Google Translate API returned unexpected result: {result}"
        except requests.exceptions.RequestException as e_req:
            return f"Google Translate API request error: {str(e_req)}"
        except Exception as e_cgt:
            return f"Google Translate API error: {type(e_cgt).__name__} - {str(e_cgt)}"

    def _deepl_translate(self, text_to_translate_dl, source_lang_dl, target_lang_dl):
        """Translate using DeepL API with context support and logging."""
        
        # Check for language change and clear context if needed
        if (self.deepl_current_source_lang is not None and 
            self.deepl_current_target_lang is not None and
            (self.deepl_current_source_lang != source_lang_dl or 
             self.deepl_current_target_lang != target_lang_dl)):
            log_debug(f"Language pair changed from {self.deepl_current_source_lang}->{self.deepl_current_target_lang} "
                     f"to {source_lang_dl}->{target_lang_dl}, clearing DeepL context")
            self._clear_deepl_context()
        
        # Track current language pair
        self.deepl_current_source_lang = source_lang_dl
        self.deepl_current_target_lang = target_lang_dl
        
        # Get context window size from settings
        context_size = getattr(self.app, 'deepl_context_window_var', None)
        context_size = context_size.get() if context_size else 0
        
        # Build context string (source language only)
        context_string = self._build_deepl_context(context_size)
        
        model_type = self.app.deepl_model_type_var.get()
        log_debug(f"DeepL API call for: {text_to_translate_dl} using model_type={model_type}")
        
        if context_string:
            log_debug(f"DeepL context ({len(context_string)} chars, {context_size} subtitles): {context_string[:100]}...")
        
        if not self.app.deepl_api_client:
            return "DeepL API client not initialized"
        
        try:
            deepl_source_param = source_lang_dl if source_lang_dl and source_lang_dl.lower() != 'auto' else None
            
            # Check if source or target language is a beta language
            is_beta_translation = False
            if source_lang_dl and source_lang_dl.upper() in DEEPL_BETA_LANGUAGES:
                is_beta_translation = True
            if target_lang_dl and target_lang_dl.upper() in DEEPL_BETA_LANGUAGES:
                is_beta_translation = True
            
            # Log beta language detection
            if is_beta_translation:
                log_debug(f"Beta language detected - source: {source_lang_dl}, target: {target_lang_dl}")
            
            # Prepare translation parameters
            translate_params = {
                'text': text_to_translate_dl,
                'target_lang': target_lang_dl,
                'model_type': model_type
            }
            
            # Add source language if not auto-detect
            if deepl_source_param:
                translate_params['source_lang'] = deepl_source_param
            
            # Enable beta languages flag if using beta languages
            # Must be passed via extra_body_parameters dictionary (note: plural)
            if is_beta_translation:
                translate_params['extra_body_parameters'] = {'enable_beta_languages': True}
                log_debug("enable_beta_languages=True added to API call via extra_body_parameters")
            
            # Add context if available (IMPORTANT: context not counted for billing!)
            if context_string and deepl_source_param:  # Only send context with explicit source language
                translate_params['context'] = context_string
            
            # Record start time for logging
            call_start_time = datetime.now()
            
            try:
                result_dl = self.app.deepl_api_client.translate_text(**translate_params)
                
                # Calculate call duration
                call_duration = (datetime.now() - call_start_time).total_seconds()
                
                if result_dl and hasattr(result_dl, 'text') and result_dl.text:
                    translated_text = result_dl.text
                    
                    # Log the API call
                    self._log_deepl_translation_call(
                        original_text=text_to_translate_dl,
                        source_lang=source_lang_dl,
                        target_lang=target_lang_dl,
                        context_size=context_size,
                        translated_text=translated_text,
                        model_type=model_type,
                        call_start_time=call_start_time,
                        call_duration=call_duration
                    )
                    
                    # Update context window with source text (not translation!)
                    self._update_deepl_context(text_to_translate_dl)
                    return translated_text
                return "DeepL API returned empty or invalid result"
            except Exception as quality_error:
                if (model_type == "quality_optimized" and 
                    ("language pair" in str(quality_error).lower() or 
                     "not supported" in str(quality_error).lower() or 
                     "unsupported" in str(quality_error).lower())):
                    log_debug(f"DeepL quality_optimized failed, falling back to latency_optimized: {quality_error}")
                    
                    # Prepare fallback parameters
                    fallback_params = {
                        'text': text_to_translate_dl,
                        'target_lang': target_lang_dl,
                        'model_type': "latency_optimized"
                    }
                    
                    # Add source language if available
                    if deepl_source_param:
                        fallback_params['source_lang'] = deepl_source_param
                    
                    # Enable beta languages flag if using beta languages
                    # Note: Beta languages cannot use latency_optimized, so this fallback might fail
                    # Must be passed via extra_body_parameters dictionary (note: plural)
                    if is_beta_translation:
                        fallback_params['extra_body_parameters'] = {'enable_beta_languages': True}
                        log_debug("Warning: Beta languages require quality_optimized model, fallback may fail")
                    
                    # Include context in fallback attempt as well
                    if context_string and deepl_source_param:
                        fallback_params['context'] = context_string
                    
                    # Record start time for fallback call
                    fallback_start_time = datetime.now()
                    
                    result_dl_fallback = self.app.deepl_api_client.translate_text(**fallback_params)
                    
                    # Calculate fallback call duration
                    fallback_duration = (datetime.now() - fallback_start_time).total_seconds()
                    
                    if result_dl_fallback and hasattr(result_dl_fallback, 'text') and result_dl_fallback.text:
                        translated_text = result_dl_fallback.text
                        
                        # Log the fallback API call (with latency_optimized model)
                        self._log_deepl_translation_call(
                            original_text=text_to_translate_dl,
                            source_lang=source_lang_dl,
                            target_lang=target_lang_dl,
                            context_size=context_size,
                            translated_text=translated_text,
                            model_type="latency_optimized",
                            call_start_time=fallback_start_time,
                            call_duration=fallback_duration
                        )
                        
                        # Update context window with source text (not translation!)
                        self._update_deepl_context(text_to_translate_dl)
                        return translated_text
                    return "DeepL API fallback returned empty or invalid result"
                else:
                    raise quality_error
        except Exception as e_cdl:
            log_debug(f"DeepL API error: {type(e_cdl).__name__} - {str(e_cdl)}")
            return f"DeepL API error: {type(e_cdl).__name__} - {str(e_cdl)}"

    def get_deepl_usage(self):
        """Get DeepL API usage statistics from the usage endpoint."""
        if not self.app.DEEPL_API_AVAILABLE:
            log_debug("DeepL API libraries not available for usage check")
            return None
            
        api_key = self.app.deepl_api_key_var.get().strip()
        if not api_key:
            log_debug("DeepL API key missing for usage check")
            return None
        
        if not REQUESTS_AVAILABLE:
            log_debug("Requests library not available for DeepL usage check")
            return None
        
        try:
            url = "https://api-free.deepl.com/v2/usage"
            headers = {
                "Authorization": f"DeepL-Auth-Key {api_key}",
                "User-Agent": "OCR-Translator/1.1.0"
            }
            
            log_debug("Checking DeepL API usage...")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                usage_data = response.json()
                log_debug(f"DeepL usage retrieved: {usage_data}")
                return usage_data
            elif response.status_code == 403:
                log_debug("DeepL API: Invalid API key or unauthorized access")
                return None
            elif response.status_code == 456:
                log_debug("DeepL API: Quota exceeded")
                return None
            else:
                log_debug(f"DeepL API error: HTTP {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            log_debug(f"DeepL usage API network error: {e}")
            return None
        except Exception as e:
            log_debug(f"DeepL usage API error: {e}")
            return None

    def _marian_translate(self, text_to_translate_mm, source_lang_mm, target_lang_mm, beam_value_mm):
        log_debug(f"MarianMT translation call for: {text_to_translate_mm} (beam={beam_value_mm})")
        if self.app.marian_translator is None: return "MarianMT translator not initialized"
        text_to_translate_cleaned = re.sub(r'\s+', ' ', text_to_translate_mm).strip()
        if not text_to_translate_cleaned: return ""
        try:
            self.app.marian_translator.num_beams = beam_value_mm
            result_mm = self.app.marian_translator.translate(text_to_translate_cleaned, source_lang_mm, target_lang_mm)
            return result_mm
        except Exception as e_cmm:
            return f"MarianMT translation error: {type(e_cmm).__name__} - {str(e_cmm)}"

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

    def update_marian_active_model(self, model_name_uam, source_lang_uam=None, target_lang_uam=None):
        if self.app.marian_translator is None:
            self.initialize_marian_translator()
            if self.app.marian_translator is None:
                log_debug("Cannot update MarianMT model - translator not initialized and init failed.")
                return False
        
        try:
            final_source_lang = source_lang_uam if source_lang_uam else self.app.marian_source_lang
            final_target_lang = target_lang_uam if target_lang_uam else self.app.marian_target_lang

            if not final_source_lang or not final_target_lang:
                log_debug(f"Cannot update MarianMT model '{model_name_uam}': source/target language not determined.")
                return False
            
            log_debug(f"Attempting to make MarianMT model active: {model_name_uam} for {final_source_lang}->{final_target_lang}")

            if hasattr(self.app.marian_translator, '_unload_current_model'):
                self.app.marian_translator._unload_current_model()
            
            if hasattr(self.app.marian_translator, 'direct_pairs'):
                self.app.marian_translator.direct_pairs[(final_source_lang, final_target_lang)] = model_name_uam
            
            self.unified_cache.clear_provider('marianmt')

            if hasattr(self.app.marian_translator, '_try_load_direct_model'):
                load_success = self.app.marian_translator._try_load_direct_model(final_source_lang, final_target_lang)
                if load_success:
                    log_debug(f"Successfully loaded MarianMT model for {final_source_lang}->{final_target_lang}")
                    return True
                else:
                    log_debug(f"Failed to load MarianMT model for {final_source_lang}->{final_target_lang}")
                    return False
            return False
        except Exception as e_umam:
            log_debug(f"Error updating MarianMT active model: {e_umam}")
            return False

    def update_marian_beam_value(self):
        if self.app.marian_translator is not None:
            try:
                beam_value_clamped = max(1, min(50, self.app.num_beams_var.get()))
                if beam_value_clamped != self.app.num_beams_var.get():
                    self.app.num_beams_var.set(beam_value_clamped)
                self.app.marian_translator.num_beams = beam_value_clamped
                log_debug(f"Updated MarianMT beam search value in translator to: {beam_value_clamped}")
            except Exception as e_umbv:
                log_debug(f"Error updating MarianMT beam value: {e_umbv}")

    def calculate_text_similarity(self, text1_sim, text2_sim):
        if not text1_sim or not text2_sim: return 0.0
        if len(text1_sim) < 10 or len(text2_sim) < 10: 
            return 1.0 if text1_sim == text2_sim else 0.0
        
        words1_set = set(text1_sim.lower().split())
        words2_set = set(text2_sim.lower().split())
        intersection_len = len(words1_set.intersection(words2_set))
        union_len = len(words1_set.union(words2_set))
        return intersection_len / union_len if union_len > 0 else 0.0

    def initialize_marian_translator(self):
        if self.app.marian_translator is not None: return
        if not hasattr(self.app, 'MARIANMT_AVAILABLE') or not self.app.MARIANMT_AVAILABLE: return
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_dir_name = "marian_models_cache"
            if getattr(sys, 'frozen', False):
                 executable_dir = os.path.dirname(sys.executable)
                 cache_dir = os.path.join(executable_dir, "_internal", cache_dir_name)
            else:
                 cache_dir = os.path.join(base_dir, cache_dir_name)
            os.makedirs(cache_dir, exist_ok=True)
            current_beam_value = self.app.num_beams_var.get()
            self.app.marian_translator = MarianMTTranslator(cache_dir=cache_dir, num_beams=current_beam_value)
            log_debug(f"MarianMT translator initialized (cache: {cache_dir}, beams: {current_beam_value})")
        except Exception as e:
            log_debug(f"Error initializing MarianMT translator: {e}\n{traceback.format_exc()}")
