# handlers/llm_provider_base.py

import re
import os
import time
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from logger import log_debug


class NetworkCircuitBreaker:
    """Circuit breaker to detect and handle network degradation."""
    
    def __init__(self):
        self.failure_count = 0
        self.slow_call_count = 0
        self.last_reset = time.time()
        self.is_open = False
        self.total_calls = 0
    
    def record_call(self, duration, success):
        """Record API call result and determine if circuit should open."""
        self.total_calls += 1
        
        # Reset counters every 5 minutes
        current_time = time.time()
        if current_time - self.last_reset > 300:  # 5 minutes
            log_debug(f"Circuit breaker stats reset. Previous period: {self.failure_count} failures, {self.slow_call_count} slow calls, {self.total_calls} total")
            self.failure_count = 0
            self.slow_call_count = 0
            self.total_calls = 0
            self.is_open = False
            self.last_reset = current_time
        
        if not success:
            self.failure_count += 1
            log_debug(f"Circuit breaker: API failure recorded ({self.failure_count}/5)")
        elif duration > 3.0:  # Slow call threshold
            self.slow_call_count += 1
            log_debug(f"Circuit breaker: Slow call recorded ({duration:.2f}s, {self.slow_call_count}/10)")
        
        # Open circuit if too many failures or slow calls
        if self.failure_count >= 5:
            self.is_open = True
            log_debug("Circuit breaker OPEN due to failure threshold - forcing client refresh")
            return True
        elif self.slow_call_count >= 10:
            self.is_open = True
            log_debug("Circuit breaker OPEN due to slow call threshold - forcing client refresh")
            return True
        
        return False
    
    def should_force_refresh(self):
        """Check if circuit is open and client should be refreshed."""
        return self.is_open


class AbstractLLMProvider(ABC):
    """Abstract base class for LLM-based translation providers."""
    
    def __init__(self, app, provider_name):
        self.app = app
        self.provider_name = provider_name
        
        # Initialize common components
        self._initialize_common_components()
    
    def _initialize_common_components(self):
        """Initialize all common functionality shared across providers."""
        # Thread safety
        self._log_lock = threading.Lock()
        self._api_calls_lock = threading.Lock()
        
        # Circuit breaker for network issues
        self.circuit_breaker = NetworkCircuitBreaker()
        
        # Session management
        self.translation_session_counter = 1
        self.current_translation_session_active = False
        self._pending_translation_calls = 0
        self._translation_session_should_end = False
        
        # Client management
        self.client = None
        self.session_api_key = None
        self.client_created_time = 0
        self.api_call_count = 0
        
        # Context window
        self.context_window = []
        self.current_source_lang = None
        self.current_target_lang = None
        
        # Logging paths
        self._initialize_logging_paths()
        
        # Initialize log files
        self._initialize_log_files()
        
        # Initialize session counters by reading existing logs (like backup version)
        self._initialize_session_counters()
        
        # Cache for cumulative totals (performance optimization)
        self._translation_cache_initialized = False
        self._cached_translation_words = 0
        self._cached_translation_input_tokens = 0
        self._cached_translation_output_tokens = 0
        self._cached_input_cost = 0.0
        self._cached_output_cost = 0.0
    
    def _initialize_logging_paths(self):
        """Initialize provider-specific logging file paths."""
        import sys
        
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        provider_title = self.provider_name.title()
        if self.provider_name == "openai":
            provider_title = "OpenAI"
        
        self.main_log_file = os.path.join(base_dir, f"{provider_title}_Translation_Long_Log.txt")
        self.short_log_file = os.path.join(base_dir, f"{provider_title}_Translation_Short_Log.txt")
    
    def _initialize_log_files(self):
        """Initialize log files with headers if they're new."""
        try:
            # Ensure the directory exists
            log_dir = os.path.dirname(self.main_log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

            timestamp = self._get_precise_timestamp()

            # Initialize main log file
            if not os.path.exists(self.main_log_file):
                # Calculate proper centering for provider name in header
                border_width = 55  # Total width of the border
                api_call_text = f"{self.provider_name.upper()} API CALL LOG"
                padding_needed = border_width - len(api_call_text) - 2  # -2 for the # symbols on each side
                left_padding = padding_needed // 2
                right_padding = padding_needed - left_padding
                centered_api_line = f"#{' ' * left_padding}{api_call_text}{' ' * right_padding}#"
                
                header = f"""
#######################################################
{centered_api_line}
#      Game-Changing Translator - Token Analysis      #
#######################################################

Logging Started: {timestamp}
Purpose: Track input/output token usage for {self.provider_name.title()} API calls, along with exact costs.
Format: Each entry shows complete message content sent to and received from {self.provider_name.title()},
        plus exact token counts and costs for the individual call and the session.

"""
                with open(self.main_log_file, 'w', encoding='utf-8-sig') as f:
                    f.write(header)
                log_debug(f"{self.provider_name.title()} API logging initialized: {self.main_log_file}")
            else:
                # Append a session start separator to existing log
                session_start_msg = f"\n\n--- NEW LOGGING SESSION STARTED: {timestamp} ---\n"
                with open(self.main_log_file, 'a', encoding='utf-8-sig') as f:
                    f.write(session_start_msg)
                log_debug(f"{self.provider_name.title()} API logging continues in existing file: {self.main_log_file}")

            # Initialize short translation log file
            if not os.path.exists(self.short_log_file):
                # Calculate proper centering for provider name in header
                border_width = 55  # Total width of the border
                translation_text = f"{self.provider_name.upper()} TRANSLATION - SHORT LOG"
                padding_needed = border_width - len(translation_text) - 2  # -2 for the # symbols on each side
                left_padding = padding_needed // 2
                right_padding = padding_needed - left_padding
                centered_translation_line = f"#{' ' * left_padding}{translation_text}{' ' * right_padding}#"
                
                tra_header = f"""
#######################################################
{centered_translation_line}
#######################################################

Session Started: {timestamp}
Purpose: Concise {self.provider_name} translation call results and statistics

"""
                with open(self.short_log_file, 'w', encoding='utf-8-sig') as f:
                    f.write(tra_header)
                log_debug(f"{self.provider_name.title()} translation short log initialized: {self.short_log_file}")
            else:
                # Append session separator
                with open(self.short_log_file, 'a', encoding='utf-8-sig') as f:
                    f.write(f"\n--- SESSION: {timestamp} ---\n")

        except Exception as e:
            log_debug(f"Error initializing {self.provider_name} API logs: {e}")
    
    def _initialize_session_counters(self):
        """Initialize session counters by reading existing logs to find the highest session number."""
        try:
            # Read Translation log to find highest translation session number
            highest_translation_session = 0
            if os.path.exists(self.short_log_file):
                with open(self.short_log_file, 'r', encoding='utf-8-sig') as f:
                    for line in f:
                        if line.startswith("SESSION ") and " STARTED " in line:
                            try:
                                # Extract session number from "SESSION X STARTED"
                                session_num = int(line.split()[1])
                                highest_translation_session = max(highest_translation_session, session_num)
                            except (IndexError, ValueError):
                                continue
            
            # Set counter to highest found + 1 (for next session)
            self.translation_session_counter = highest_translation_session + 1
            
            log_debug(f"Initialized {self.provider_name} session counter: Translation={self.translation_session_counter}")
            
        except Exception as e:
            log_debug(f"Error initializing {self.provider_name} session counters: {e}, using defaults")
            # Fall back to 1 if there's any error
            self.translation_session_counter = 1
    
    # === SESSION MANAGEMENT (IDENTICAL ACROSS PROVIDERS) ===
    
    def start_translation_session(self):
        """Start a new translation session with numbered identifier."""
        if not self.current_translation_session_active:
            timestamp = self._get_precise_timestamp()
            try:
                with open(self.short_log_file, 'a', encoding='utf-8-sig') as f:
                    f.write(f"\nSESSION {self.translation_session_counter} STARTED {timestamp}\n")
                self.current_translation_session_active = True
                log_debug(f"{self.provider_name.title()} Translation Session {self.translation_session_counter} started")
            except Exception as e:
                log_debug(f"Error starting {self.provider_name} translation session: {e}")

    def request_end_translation_session(self):
        """Request to end translation session - will end when no pending calls remain."""
        if self.current_translation_session_active:
            if self._pending_translation_calls == 0:
                # Can end immediately
                return self.end_translation_session()
            else:
                # Mark for ending when calls complete (session will end automatically)
                self._translation_session_should_end = True
                log_debug(f"{self.provider_name.title()} session end requested, waiting for {self._pending_translation_calls} pending calls")
                return False
        return True
    
    def end_translation_session(self, force=False):
        """End the current translation session only if no pending translation calls."""
        if self.current_translation_session_active:
            # Wait for any pending translation calls to complete before ending session
            if self._pending_translation_calls > 0 and not force:
                log_debug(f"{self.provider_name.title()} session end delayed: {self._pending_translation_calls} pending calls")
                return False  # Session not ended yet
            
            timestamp = self._get_precise_timestamp()
            try:
                end_reason = "(FORCED - APP CLOSING)" if force else ""
                with open(self.short_log_file, 'a', encoding='utf-8-sig') as f:
                    f.write(f"SESSION {self.translation_session_counter} ENDED {timestamp} {end_reason}\n".strip() + "\n")
                
                # Clear context AFTER session end is logged to ensure clean start for next session
                self._clear_context()
                
                self.current_translation_session_active = False
                self._translation_session_should_end = False
                self.translation_session_counter += 1
                log_debug(f"{self.provider_name.title()} Translation Session {self.translation_session_counter - 1} ended")
                return True  # Session ended successfully
            except Exception as e:
                log_debug(f"Error ending {self.provider_name} translation session: {e}")
                return False
        return True  # Already inactive
    
    def _increment_pending_translation_calls(self):
        """Increment the count of pending translation calls."""
        with self._api_calls_lock:
            self._pending_translation_calls += 1

    def _decrement_pending_translation_calls(self):
        """Decrement the count of pending translation calls."""
        with self._api_calls_lock:
            self._pending_translation_calls = max(0, self._pending_translation_calls - 1)
            if self._pending_translation_calls == 0 and self._translation_session_should_end:
                self.end_translation_session()
    
    # === CONTEXT WINDOW MANAGEMENT (IDENTICAL ACROSS PROVIDERS) ===
    
    def _build_context_string(self, text, source_lang, target_lang):
        """Build context string with identical format for all providers (Gemini's format)."""
        # Get display names for source and target languages
        source_lang_name = self._get_language_display_name(source_lang)
        target_lang_name = self._get_language_display_name(target_lang)
        
        # Get context window size
        context_size = self._get_context_window_size()
        
        # Add linebreak instruction conditionally
        # linebreak_instruction = "Use <br> as in the source text. " if self.app.keep_linebreaks_var.get() else ""
        linebreak_instruction = "Keep <br> linebreaks from the source text in the translation. " if self.app.keep_linebreaks_var.get() else ""
        
        # Build instruction line based on actual context window content
        if context_size == 0:
            instruction_line = f"<Translate idiomatically from {source_lang_name} to {target_lang_name}. {linebreak_instruction}Return translation only.>"
        else:
            # Check actual number of stored context pairs
            actual_context_count = len(self.context_window)
            
            if actual_context_count == 0:
                instruction_line = f"<Translate idiomatically from {source_lang_name} to {target_lang_name}. {linebreak_instruction}Return translation only.>"
            elif context_size == 1:
                instruction_line = f"<Translate idiomatically the second subtitle from {source_lang_name} to {target_lang_name}. {linebreak_instruction}Return translation only.>"
            elif context_size == 2:
                if actual_context_count == 1:
                    instruction_line = f"<Translate idiomatically the second subtitle from {source_lang_name} to {target_lang_name}. {linebreak_instruction}Return translation only.>"
                else:
                    instruction_line = f"<Translate idiomatically the third subtitle from {source_lang_name} to {target_lang_name}. {linebreak_instruction}Return translation only.>"
            else:
                target_position = min(actual_context_count + 1, context_size + 1)
                ordinal = self._get_ordinal_number(target_position)
                instruction_line = f"<Translate idiomatically the {ordinal} subtitle from {source_lang_name} to {target_lang_name}. {linebreak_instruction}Return translation only.>"
        
        # Build context window with new text integrated in grouped format
        if context_size == 0:
            # No context, use simple format 
            message_content = f"{instruction_line}\n\n{source_lang_name.upper()}: {text}\n\n{target_lang_name.upper()}:"
        else:
            # Build context window for multi-line format
            context_with_new_text = self._build_context_window_content(text, source_lang, target_lang)
            message_content = f"{instruction_line}\n\n{context_with_new_text}\n{target_lang_name.upper()}:"
        
        return message_content
    
    def _build_context_window_content(self, new_source_text, source_lang_code, target_lang_code):
        """Build context window from previous translations with grouped format."""
        context_size = self._get_context_window_size()
        if context_size == 0:
            return ""
        
        source_lines = []
        target_lines = []
        
        # Add context pairs if available
        if context_size > 0 and self.context_window:
            # Get last N context pairs
            context_pairs = self.context_window[-context_size:]
            
            # Collect all source lines first, then all target lines
            for source_text, target_text, source_lang, target_lang in context_pairs:
                # Get display names and convert to uppercase
                source_display = self._get_language_display_name(source_lang).upper()
                target_display = self._get_language_display_name(target_lang).upper()
                source_lines.append(f"{source_display}: {source_text}")
                target_lines.append(f"{target_display}: {target_text}")
        
        # Add new source text if provided
        if new_source_text and source_lang_code:
            source_display = self._get_language_display_name(source_lang_code).upper()
            source_lines.append(f"{source_display}: {new_source_text}")
        
        # Combine: all sources first, blank line, then all targets (no new target)
        if source_lines and target_lines:
            all_lines = source_lines + [""] + target_lines
        elif source_lines:
            all_lines = source_lines
        else:
            all_lines = []
        return "\n".join(all_lines) if all_lines else ""
    
    def _update_sliding_window(self, source_text, target_text):
        """Update sliding window with new translation pair including language codes."""
        # Get current language codes
        source_lang = getattr(self, 'current_source_lang', 'en')
        target_lang = getattr(self, 'current_target_lang', 'pl')
        
        # Check for duplicates according to specific rules:
        # Rule 2: If translation is identical to previous translation, cache but don't add to context
        # Rule 3: Only check last vs current (penultimate vs current)
        if self.context_window:
            last_source, last_target, _, _ = self.context_window[-1]
            
            # Rule 2: If translation is identical to previous, skip context update (but keep in cache)
            if target_text == last_target:
                log_debug(f"Skipping {self.provider_name} context window update - duplicate target text: '{target_text}'")
                return
            
            # Additional check: if source is also identical, skip (though this should be caught at OCR level)
            if source_text == last_source:
                log_debug(f"Skipping {self.provider_name} context window update - duplicate source text: '{source_text}'")
                return
        
        # Add new pair with language codes
        self.context_window.append((source_text, target_text, source_lang, target_lang))
        
        # Keep only last 5 pairs (more than the max context window setting)
        self.context_window = self.context_window[-5:]
    
    def _clear_context(self):
        """Clear context window after language changes."""
        try:
            self.context_window = []
            log_debug(f"{self.provider_name.title()} context cleared")
        except Exception as e:
            log_debug(f"Error clearing {self.provider_name} context: {e}")
    
    # === LOGGING SYSTEM (IDENTICAL ACROSS PROVIDERS) ===
    
    def _log_complete_translation_call(self, message_content, response_text, call_duration, 
                                     input_tokens, output_tokens, original_text, 
                                     source_lang, target_lang, model_name_for_costing, model_name_for_logging, model_source):
        """Log complete translation API call with atomic writing (identical format for all providers)."""
        # Check if API logging is enabled
        if not self._is_logging_enabled():
            return
            
        try:
            with self._log_lock:  # Ensure atomic logging to prevent interleaved logs
                # Calculate correct start and end times based on call duration
                call_end_time = self._get_precise_timestamp()
                call_start_time = self._calculate_start_time(call_end_time, call_duration)
                
                # --- 1. Calculate current call translated word count from original text ---
                current_translated_words = len(original_text.split())
                
                # --- 2. Get cumulative totals BEFORE this call ---
                prev_total_translated_words, prev_total_input, prev_total_output = self._get_cumulative_totals()

                # --- 3. Get model-specific costs and calculate for current call ---
                input_cost_per_million, output_cost_per_million = self._get_model_costs(model_name_for_costing)
                
                call_input_cost = (input_tokens / 1_000_000) * input_cost_per_million
                call_output_cost = (output_tokens / 1_000_000) * output_cost_per_million
                total_call_cost = call_input_cost + call_output_cost
                
                # --- 4. Calculate new cumulative totals using simple addition ---
                new_total_translated_words = prev_total_translated_words + current_translated_words
                new_total_input = prev_total_input + input_tokens
                new_total_output = prev_total_output + output_tokens
                
                # Update translation cache with new values for performance
                self._update_translation_cache(current_translated_words, input_tokens, output_tokens)
                
                # Get previous cumulative costs and use simple addition
                prev_total_input_cost, prev_total_output_cost = self._get_cumulative_costs()
                total_input_cost = prev_total_input_cost + call_input_cost
                total_output_cost = prev_total_output_cost + call_output_cost
                
                # Update costs cache with new values for performance
                self._update_costs_cache(call_input_cost, call_output_cost)
                
                # --- 5. Calculate detailed message stats ---
                words_in_message = len(message_content.split())
                chars_in_message = len(message_content)
                lines_in_message = len(message_content.split('\n'))
                
                # Format cost display with smart decimal precision
                input_cost_str = f"${input_cost_per_million:.3f}" if (input_cost_per_million * 1000) % 10 != 0 else f"${input_cost_per_million:.2f}"
                output_cost_str = f"${output_cost_per_million:.3f}" if (output_cost_per_million * 1000) % 10 != 0 else f"${output_cost_per_million:.2f}"
                
                # --- 6. Format the complete log entry with IDENTICAL header format ---
                log_entry = f"""
=== {self.provider_name.upper()} TRANSLATION API CALL ===
Timestamp: {call_start_time}
Language Pair: {source_lang} -> {target_lang}
Original Text: {original_text}

CALL DETAILS:
- Message Length: {chars_in_message} characters
- Word Count: {words_in_message} words
- Line Count: {lines_in_message} lines

COMPLETE MESSAGE CONTENT SENT TO {self.provider_name.upper()}:
---BEGIN MESSAGE---
{message_content}
---END MESSAGE---


RESPONSE RECEIVED:
Model: {model_name_for_logging} ({model_source})
Cost: input {input_cost_str}, output {output_cost_str} (per 1M)
Timestamp: {call_end_time}
Call Duration: {call_duration:.3f} seconds

---BEGIN RESPONSE---
{response_text}
---END RESPONSE---

TOKEN & COST ANALYSIS (CURRENT CALL):
- Translated Words: {current_translated_words}
- Exact Input Tokens: {input_tokens}
- Exact Output Tokens: {output_tokens}
- Input Cost: ${call_input_cost:.8f}
- Output Cost: ${call_output_cost:.8f}
- Total Cost for this Call: ${total_call_cost:.8f}

CUMULATIVE TOTALS (INCLUDING THIS CALL, FROM LOG START):
- Total Translated Words (so far): {new_total_translated_words}
- Total Input Tokens (so far): {new_total_input}
- Total Output Tokens (so far): {new_total_output}
- Total Input Cost (so far): ${total_input_cost:.8f}
- Total Output Cost (so far): ${total_output_cost:.8f}
- Cumulative Log Cost: ${(total_input_cost + total_output_cost):.8f}

========================================

"""
                
                # --- 7. Write to main log file ---
                with open(self.main_log_file, 'a', encoding='utf-8-sig') as f:
                    f.write(log_entry)
                
                # --- 8. Write to short translation log ---
                self._write_short_translation_log(call_start_time, call_end_time, call_duration, 
                                                input_tokens, output_tokens, total_call_cost,
                                                new_total_input, new_total_output, 
                                                total_input_cost + total_output_cost, 
                                                original_text, response_text, source_lang, target_lang, 
                                                model_name_for_logging, model_source,
                                                input_cost_per_million, output_cost_per_million)
                
                log_debug(f"Complete {self.provider_name} translation call logged: In={input_tokens}, Out={output_tokens}, Duration={call_duration:.3f}s")
                    
        except Exception as e:
            log_debug(f"Error logging complete {self.provider_name} translation call: {e}")
    
    def _write_short_translation_log(self, call_start_time, call_end_time, call_duration,
                                   input_tokens, output_tokens, call_cost, cumulative_input,
                                   cumulative_output, cumulative_cost, original_text,
                                   translated_text, source_lang, target_lang, model_name, model_source,
                                   input_cost_per_million, output_cost_per_million):
        """Write concise translation call log entry with IDENTICAL format."""
        if not self._is_logging_enabled():
            return
            
        try:
            # Get language display names
            source_lang_name = self._get_language_display_name(source_lang).upper()
            target_lang_name = self._get_language_display_name(target_lang).upper()
            
            # Get model costs from CSV for display
            cost_line = ""
            try:
                # Use the passed-in cost rates directly
                input_cost, output_cost = input_cost_per_million, output_cost_per_million
                
                # Format with 3 decimals if third decimal is non-zero, otherwise 2 decimals
                input_str = f"${input_cost:.3f}" if (input_cost * 1000) % 10 != 0 else f"${input_cost:.2f}"
                output_str = f"${output_cost:.3f}" if (output_cost * 1000) % 10 != 0 else f"${output_cost:.2f}"
                
                cost_line = f"Cost: input {input_str}, output {output_str} (per 1M)\n"
            except Exception:
                pass
            
            log_entry = f"""===== TRANSLATION CALL =======
Model: {model_name} ({model_source})
{cost_line}Start: {call_start_time}
End: {call_end_time}
Duration: {call_duration:.3f}s
Tokens: In={input_tokens}, Out={output_tokens} | Cost: ${call_cost:.8f}
Total (so far): In={cumulative_input}, Out={cumulative_output} | Cost: ${cumulative_cost:.8f}
Result:
--------------------------------------------------
{source_lang_name}: {original_text}
{target_lang_name}: {translated_text}
--------------------------------------------------

"""
            with open(self.short_log_file, 'a', encoding='utf-8-sig') as f:
                f.write(log_entry)
        except Exception as e:
            log_debug(f"Error writing short {self.provider_name} translation log: {e}")
    
    # === CLIENT MANAGEMENT (IDENTICAL ACROSS PROVIDERS) ===
    
    def _should_refresh_client(self):
        """Check if client should be refreshed to prevent stale connections."""
        if not hasattr(self, 'client_created_time'):
            self.client_created_time = time.time()
            return False
        
        current_time = time.time()
        
        # Refresh client every 30 minutes to prevent stale connections
        if current_time - self.client_created_time > 1800:  # 30 minutes
            log_debug(f"Refreshing {self.provider_name} client due to age (30 minutes)")
            return True
        
        # Refresh after every 100 API calls to prevent connection accumulation
        if not hasattr(self, 'api_call_count'):
            self.api_call_count = 0
        
        if self.api_call_count > 100:
            log_debug(f"Refreshing {self.provider_name} client after 100 API calls")
            return True
        
        return False

    def _force_client_refresh(self):
        """Force refresh of client and reset counters."""
        self.client = None
        self.client_created_time = time.time()
        self.api_call_count = 0
        log_debug(f"{self.provider_name.title()} client forcefully refreshed")
    
    def _should_reset_session(self, api_key):
        """Check if session needs to be reset due to API key change."""
        if not hasattr(self, 'client'):
            return True
        return self.session_api_key != api_key
    
    # === UTILITY METHODS (IDENTICAL ACROSS PROVIDERS) ===
    
    def _get_precise_timestamp(self):
        """Get timestamp with millisecond precision."""
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Remove last 3 digits for milliseconds

    def _calculate_start_time(self, end_time_str, duration_seconds):
        """Calculate start time based on end time and duration."""
        try:
            # Parse the end time string
            end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S.%f")
            # Subtract the duration to get start time
            start_time = end_time - timedelta(seconds=duration_seconds)
            # Format back to string
            return start_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        except Exception as e:
            log_debug(f"Error calculating start time: {e}")
            # Fallback to end time if calculation fails
            return end_time_str
    
    def _get_ordinal_number(self, number):
        """Convert number to ordinal string (1->first, 2->second, etc.)."""
        ordinals = {
            1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
            6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth"
        }
        return ordinals.get(number, f"{number}th")
    
    def _get_language_display_name(self, lang_code):
        """Get display name for language code using the language manager."""
        if lang_code is None:
            return 'Unknown'
        try:
            # Use the language manager's existing functionality
            display_name = self.app.language_manager.get_localized_language_name(lang_code, self.provider_name, 'english')
            
            # If not found, try fallback logic
            if display_name == lang_code:
                # Special case for 'auto'
                if lang_code.lower() == 'auto':
                    return 'Auto'
                # Fallback to title case
                return lang_code.title()
            
            return display_name
        except Exception as e:
            log_debug(f"Error getting language display name for {lang_code}/{self.provider_name}: {e}")
            # Special case for 'auto'
            if lang_code.lower() == 'auto':
                return 'Auto'
            return lang_code.title()
    
    # === CACHE MANAGEMENT (IDENTICAL ACROSS PROVIDERS) ===
    
    def _get_cumulative_totals(self):
        """Get cumulative translation totals using efficient memory cache."""
        # Use cache if initialized
        if self._translation_cache_initialized:
            return self._cached_translation_words, self._cached_translation_input_tokens, self._cached_translation_output_tokens
        
        # Initialize cache by reading log file once
        total_translated_words = 0
        total_input = 0
        total_output = 0
        
        if not os.path.exists(self.main_log_file):
            # Initialize cache with zeros
            self._cached_translation_words = 0
            self._cached_translation_input_tokens = 0
            self._cached_translation_output_tokens = 0
            self._translation_cache_initialized = True
            log_debug(f"{self.provider_name} translation cache initialized with zeros (no log file)")
            return 0, 0, 0
        
        # Define regex to find the exact counts
        translated_words_regex = re.compile(r"^\s*-\s*Total Translated Words \(so far\):\s*(\d+)")
        input_token_regex = re.compile(r"^\s*-\s*Total Input Tokens \(so far\):\s*(\d+)")
        output_token_regex = re.compile(r"^\s*-\s*Total Output Tokens \(so far\):\s*(\d+)")
        
        try:
            with open(self.main_log_file, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    translated_words_match = translated_words_regex.match(line)
                    if translated_words_match:
                        total_translated_words = int(translated_words_match.group(1))
                        continue
                    
                    input_match = input_token_regex.match(line)
                    if input_match:
                        total_input = int(input_match.group(1))
                        continue
                    
                    output_match = output_token_regex.match(line)
                    if output_match:
                        total_output = int(output_match.group(1))
            
            # Initialize cache with values from file
            self._cached_translation_words = total_translated_words
            self._cached_translation_input_tokens = total_input
            self._cached_translation_output_tokens = total_output
            self._translation_cache_initialized = True
            
            log_debug(f"{self.provider_name} translation cache initialized: {total_translated_words} words, {total_input} input, {total_output} output")
                        
        except (IOError, ValueError) as e:
            log_debug(f"Error reading {self.provider_name} cumulative totals from log file: {e}")
            # Initialize cache with zeros on error
            self._cached_translation_words = 0
            self._cached_translation_input_tokens = 0
            self._cached_translation_output_tokens = 0
            self._translation_cache_initialized = True
            return 0, 0, 0
            
        return total_translated_words, total_input, total_output

    def _get_cumulative_costs(self):
        """Get cumulative translation costs using efficient memory cache."""
        # Use cache if initialized
        if hasattr(self, '_costs_cache_initialized') and self._costs_cache_initialized:
            return self._cached_input_cost, self._cached_output_cost
        
        # Initialize cache by reading log file once
        total_input_cost = 0.0
        total_output_cost = 0.0
        
        if not os.path.exists(self.main_log_file):
            # Initialize cache with zeros
            self._cached_input_cost = 0.0
            self._cached_output_cost = 0.0
            self._costs_cache_initialized = True
            log_debug(f"{self.provider_name} costs cache initialized with zeros (no log file)")
            return 0.0, 0.0
        
        # Define regex to find cumulative cost totals
        input_cost_regex = re.compile(r"^\s*-\s*Total Input Cost \(so far\):\s*\$([0-9]*\.?[0-9]+)")
        output_cost_regex = re.compile(r"^\s*-\s*Total Output Cost \(so far\):\s*\$([0-9]*\.?[0-9]+)")
        
        try:
            with open(self.main_log_file, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    input_cost_match = input_cost_regex.match(line)
                    if input_cost_match:
                        total_input_cost = float(input_cost_match.group(1))
                        continue
                    
                    output_cost_match = output_cost_regex.match(line)
                    if output_cost_match:
                        total_output_cost = float(output_cost_match.group(1))
            
            # Initialize cache with values from file
            self._cached_input_cost = total_input_cost
            self._cached_output_cost = total_output_cost
            self._costs_cache_initialized = True
            
            log_debug(f"{self.provider_name} costs cache initialized: ${total_input_cost:.8f} input, ${total_output_cost:.8f} output")
                        
        except (IOError, ValueError) as e:
            log_debug(f"Error reading {self.provider_name} cumulative costs from log file: {e}")
            # Initialize cache with zeros on error
            self._cached_input_cost = 0.0
            self._cached_output_cost = 0.0
            self._costs_cache_initialized = True
            return 0.0, 0.0
            
        return total_input_cost, total_output_cost

    def _update_translation_cache(self, words, input_tokens, output_tokens):
        """Update translation cache with new values for performance."""
        if not self._translation_cache_initialized:
            # If cache not initialized, initialize it first
            self._get_cumulative_totals()
        
        # Increment cached values
        self._cached_translation_words += words
        self._cached_translation_input_tokens += input_tokens
        self._cached_translation_output_tokens += output_tokens

    def _update_costs_cache(self, input_cost, output_cost):
        """Update costs cache with new values for performance."""
        if not hasattr(self, '_costs_cache_initialized') or not self._costs_cache_initialized:
            # If cache not initialized, initialize it first
            self._get_cumulative_costs()
        
        # Increment cached values
        self._cached_input_cost += input_cost
        self._cached_output_cost += output_cost
    
    # === TRANSLATION INTERFACE (UNIFIED) ===
    
    def translate(self, text_to_translate, source_lang, target_lang, ocr_batch_number=None):
        """Main translation method - handles all common logic."""
        log_debug(f"{self.provider_name.title()} translate request for: {text_to_translate}")
        
        # Check circuit breaker and force refresh if needed
        if self.circuit_breaker.should_force_refresh():
            log_debug(f"{self.provider_name.title()} circuit breaker forcing client refresh due to network issues")
            self._force_client_refresh()
            self.circuit_breaker = NetworkCircuitBreaker()  # Reset circuit breaker
        
        # Track pending call
        self._increment_pending_translation_calls()
        
        try:
            # Check API key
            api_key = self._get_api_key()
            if not api_key:
                return f"{self.provider_name.title()} API key missing"
            
            # Check if provider libraries are available
            if not self._check_provider_availability():
                return f"{self.provider_name.title()} libraries not available"
            
            # Check if we need to create a new client
            needs_new_session = (
                not hasattr(self, 'client') or 
                self.client is None or
                self._should_reset_session(api_key)  # API key changed
            )
            
            if needs_new_session:
                if hasattr(self, 'session_api_key') and self.session_api_key != api_key:
                    log_debug(f"Creating new {self.provider_name} client (API key changed)")
                else:
                    log_debug(f"Creating new {self.provider_name} client (no existing client)")
                self._initialize_client(api_key, source_lang, target_lang)
            else:
                # Check if language pair changed - clear context
                if (hasattr(self, 'current_source_lang') and hasattr(self, 'current_target_lang') and
                    (self.current_source_lang != source_lang or self.current_target_lang != target_lang)):
                    log_debug(f"Language pair changed from {self.current_source_lang}->{self.current_target_lang} to {source_lang}->{target_lang}, clearing context")
                    self._clear_context()
            
            # Track current language pair for context clearing
            self.current_source_lang = source_lang
            self.current_target_lang = target_lang
            
            if self.client is None:
                return f"{self.provider_name.title()} client initialization failed"
            
            # Build context string (identical format for all providers)
            message_content = self._build_context_string(text_to_translate, source_lang, target_lang)
            
            log_debug(f"Sending to {self.provider_name.title()} {source_lang}->{target_lang}: [{text_to_translate}]")
            log_debug(f"Making {self.provider_name.title()} API call for: {text_to_translate}")
            
            api_call_start_time = time.time()
            
            # Make the provider-specific API call
            model_config = self._get_model_config()
            response = self._make_api_call(message_content, model_config)
            
            call_duration = time.time() - api_call_start_time
            log_debug(f"{self.provider_name.title()} API call took {call_duration:.3f}s")
            
            # Record successful call with circuit breaker
            needs_refresh = self.circuit_breaker.record_call(call_duration, True)
            if needs_refresh:
                # Schedule client refresh for next call
                self.client = None
            
            # Increment API call counter for periodic refresh
            if hasattr(self, 'api_call_count'):
                self.api_call_count += 1

            # Parse the response (provider-specific)
            translation_result, input_tokens, output_tokens, model_name_for_costing, model_name_for_logging, model_source = self._parse_response(response)
            
            log_debug(f"{self.provider_name.title()} response: {translation_result}")
            
            # Log complete API call atomically (request + response + stats together)
            self._log_complete_translation_call(message_content, translation_result, call_duration, 
                                              input_tokens, output_tokens, text_to_translate, 
                                              source_lang, target_lang, model_name_for_costing, model_name_for_logging, model_source)
            
            # Update context window
            if translation_result and not self._is_error_message(translation_result):
                self._update_sliding_window(text_to_translate, translation_result)
            
            return translation_result
            
        except Exception as e:
            # Record failed call with circuit breaker
            self.circuit_breaker.record_call(0, False)
            error_str = str(e)
            log_debug(f"{self.provider_name.title()} API error: {type(e).__name__} - {error_str}")
            
            # Suppress certain errors from being displayed
            if self._should_suppress_error(error_str):
                log_debug(f"{self.provider_name.title()} error suppressed from translation display")
                return None  # Don't display suppressed errors
            else:
                return f"{self.provider_name.title()} API error: {error_str}"
        finally:
            # Always decrement pending call counter
            self._decrement_pending_translation_calls()
    
    def _is_error_message(self, text):
        """Check if a translation result is an error message."""
        if not isinstance(text, str):
            return True
        error_indicators = [
            "error:", "api error", "not initialized", "missing", "failed",
            "not available", "not supported", "invalid result", "empty result"
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in error_indicators)
    
    # === ABSTRACT METHODS (MUST BE IMPLEMENTED BY SUBCLASSES) ===
    
    @abstractmethod
    def _get_api_key(self):
        """Get API key for this provider."""
        pass
    
    @abstractmethod
    def _check_provider_availability(self):
        """Check if provider libraries are available."""
        pass
    
    @abstractmethod
    def _get_context_window_size(self):
        """Get context window size setting for this provider."""
        pass
    
    @abstractmethod
    def _initialize_client(self, api_key, source_lang, target_lang):
        """Initialize provider-specific client."""
        pass
    
    @abstractmethod
    def _get_model_config(self):
        """Get model configuration for API calls."""
        pass
    
    @abstractmethod
    def _make_api_call(self, message_content, model_config):
        """Make provider-specific API call."""
        pass
    
    @abstractmethod
    def _parse_response(self, response):
        """Parse provider-specific response and return (result, input_tokens, output_tokens, model_name_for_costing, model_name_for_logging, model_source)."""
        pass
    
    @abstractmethod
    def _get_model_costs(self, model_name):
        """Get model-specific costs (input_cost_per_million, output_cost_per_million)."""
        pass
    
    @abstractmethod
    def _is_logging_enabled(self):
        """Check if logging is enabled for this provider."""
        pass
    
    @abstractmethod
    def _should_suppress_error(self, error_str):
        """Check if error should be suppressed from display."""
        pass
