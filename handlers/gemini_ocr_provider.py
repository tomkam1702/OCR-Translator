# handlers/gemini_ocr_provider.py
import re
import os
import sys
import time
from logger import log_debug
from .ocr_provider_base import AbstractOCRProvider

# Import Gemini dependencies
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    try:
        import google.generativeai as genai
        GENAI_AVAILABLE = True
    except ImportError:
        GENAI_AVAILABLE = False


class GeminiOCRProvider(AbstractOCRProvider):
    """Gemini-specific OCR provider implementation."""
    
    def __init__(self, app):
        super().__init__(app, "gemini_ocr")
        
        # OCR-specific cache for cumulative totals (performance optimization)
        self._ocr_cache_initialized = False
        self._cached_ocr_input_tokens = 0
        self._cached_ocr_output_tokens = 0
        self._cached_ocr_cost = 0.0
        
        log_debug("GeminiOCRProvider initialized")

    def _get_api_key(self):
        """Get the Gemini API key from the application."""
        return self.app.gemini_api_key_var.get().strip()

    def _check_provider_availability(self):
        """Check if Gemini libraries are available."""
        return GENAI_AVAILABLE

    def _initialize_client(self, api_key):
        """Initialize the Gemini API client.
        
        Args:
            api_key: The Gemini API key
        """
        if not GENAI_AVAILABLE:
            log_debug("Google Gen AI libraries not available for Gemini OCR session")
            self.client = None
            return

        if hasattr(self, 'client') and self._should_refresh_client():
            self._force_client_refresh()

        try:
            log_debug("Creating new Gemini client for OCR with default API version")
            self.client = genai.Client(api_key=api_key)
            
            self.session_api_key = api_key
            self.client_created_time = time.time()
            self.api_call_count = 0
            self._current_api_version = 'v1beta'
            return self.client is not None
        except Exception as e:
            log_debug(f"Failed to initialize Gemini OCR client: {e}")
            self.client = None
            return False

    def _make_api_call(self, image_data, source_lang):
        """Make the actual Gemini OCR API call."""
        if self.client is None:
            raise Exception("Gemini client not initialized")
        
        # Store source_lang for later use in logging
        self._current_source_lang = source_lang
        
        # Get the current OCR model
        ocr_model_api_name = self.app.get_current_gemini_model_for_ocr() or 'gemini-2.5-flash-lite'
        
        # Configure the OCR request
        ocr_model_lower = ocr_model_api_name.lower()
        
        # Get media resolution from model config
        # Use gemini_ocr_model_var which contains the full display name (e.g., "Gemini 3 Flash (Low)")
        # Note: ocr_model_var only contains the provider type ("gemini")
        ocr_model_display_name = self.app.gemini_ocr_model_var.get()
        media_resolution_str = self.app.gemini_models_manager.get_model_media_resolution(ocr_model_display_name)
        
        # Check if we need v1alpha API for per-Part media resolution (required for LOW resolution on Gemini 3)
        # needs_alpha_api = (media_resolution_str == 'LOW' and 'gemini-3' in ocr_model_lower)
        current_api_version = getattr(self, '_current_api_version', 'v1beta')
        
        log_debug(f"OCR Resolution check: display_name='{ocr_model_display_name}', resolution='{media_resolution_str}', model_lower='{ocr_model_lower}', current_api='{current_api_version}'")
        
        # We now use global media resolution for all models (including Gemini 3), so we stay on v1beta
        # Re-initialization logic for alpha API removed.
        
        # Store for logging
        self._current_media_resolution = media_resolution_str
        
        # Map string to enum value
        media_resolution_map = {
            'LOW': types.MediaResolution.MEDIA_RESOLUTION_LOW,
            'MEDIUM': types.MediaResolution.MEDIA_RESOLUTION_MEDIUM,
            'HIGH': types.MediaResolution.MEDIA_RESOLUTION_HIGH,
            'ULTRA_HIGH': types.MediaResolution.MEDIA_RESOLUTION_HIGH  # Fallback, no ULTRA_HIGH in base enum
        }
        media_resolution = media_resolution_map.get(media_resolution_str, types.MediaResolution.MEDIA_RESOLUTION_MEDIUM)
        
        # Base arguments
        config_args = {
            "temperature": 0.0,
            "max_output_tokens": 512,
            "media_resolution": media_resolution,
            "safety_settings": [
                types.SafetySetting(category=c, threshold='BLOCK_NONE') 
                for c in ['HARM_CATEGORY_HARASSMENT', 'HARM_CATEGORY_HATE_SPEECH', 
                         'HARM_CATEGORY_SEXUALLY_EXPLICIT', 'HARM_CATEGORY_DANGEROUS_CONTENT']
            ]
        }
        
        # Add model-specific thinking config
        try:
            if "gemini-3" in ocr_model_lower:
                # Gemini 3 requires thinking_level instead of defaulting (or strict budget)
                config_args["thinking_config"] = types.ThinkingConfig(thinking_level="MINIMAL")
            # For Gemini 2.5, we don't set thinking_budget for OCR to keep it standard/fast unless needed, 
            # but usually OCR doesn't trigger severe thinking unless requested. 
            # If we wanted to be strict for G2.5 OCR too, we could add thinking_budget=0 here, 
            # but let's stick to G3 requirement as per prompt.
        except Exception as e:
            log_debug(f"Error setting thinking config for OCR: {e}")

        ocr_config = types.GenerateContentConfig(**config_args)
        
        # OCR prompt optimized for text transcription
        if self.app.keep_linebreaks_var.get():
            prompt = """1. Transcribe the text from the image exactly as it appears. Do not correct, rephrase, or alter the words in any way. Provide a literal and verbatim transcription of all text in the image. Keep the linebreaks. Don't return anything else.
2. If there is no text in the image, return only: <EMPTY>."""
        else:
            prompt = """1. Transcribe the text from the image exactly as it appears. Do not correct, rephrase, or alter the words in any way. Provide a literal and verbatim transcription of all text in the image. Don't return anything else.
2. If there is no text in the image, return only: <EMPTY>."""
        
        # Make the API call
        api_call_start_time = time.time()
        
        # Use simple Part without per-part media_resolution (relies on global config)
        # This applies to all models now (Gemini 2.x and Gemini 3)
        image_part = types.Part.from_bytes(
            data=image_data, 
            mime_type='image/webp'
        )
        
        response = self.client.models.generate_content(
            model=ocr_model_api_name,
            contents=[image_part, prompt],
            config=ocr_config
        )
        call_duration = time.time() - api_call_start_time
        
        # This was the duplicate call. The base class handles this now.
        # self.circuit_breaker.record_call(call_duration, True)
        
        return response, call_duration, prompt, len(image_data)

    def _parse_response(self, response_data):
        """Parse the API response to extract text, tokens, and model info."""
        response, call_duration, prompt, image_size = response_data
        
        ocr_result = response.text.strip() if response.text else "<EMPTY>"
        
        # First, strip markdown code blocks if they exist
        parsed_text = ocr_result.replace('```text', '').replace('```', '').strip()

        if self.app.keep_linebreaks_var.get():
            # If keeping linebreaks, replace newlines with <br>
            parsed_text = parsed_text.replace('\n', '<br>').strip()
        else:
            # Otherwise, replace newlines with spaces
            parsed_text = parsed_text.replace('\n', ' ').strip()

        # Final check for emptiness
        if not parsed_text or "<EMPTY>" in parsed_text:
            parsed_text = "<EMPTY>"
        
        input_tokens, output_tokens = 0, 0
        # Get model name for costing from app config
        model_name_for_costing = self.app.get_current_gemini_model_for_ocr() or 'gemini-2.5-flash-lite'
        model_source = "api_request"
        
        try:
            if response.usage_metadata:
                input_tokens = response.usage_metadata.prompt_token_count or 0
                output_tokens = response.usage_metadata.candidates_token_count or 0
            
            # Get model name for logging from API response
            model_name_for_logging = "unknown"
            if hasattr(response, 'model_version') and response.model_version:
                model_name_for_logging = response.model_version
            else:
                model_name_for_logging = model_name_for_costing # Fallback
        except (AttributeError, KeyError):
            log_debug("Could not find usage_metadata in Gemini OCR response.")
            model_name_for_logging = model_name_for_costing # Fallback
        
        if self._is_logging_enabled():
            # Get stored values for logging
            api_version = getattr(self, '_current_api_version', 'v1beta')
            media_resolution = getattr(self, '_current_media_resolution', 'MEDIUM')
            
            self._log_complete_ocr_call(
                prompt, image_size, ocr_result, parsed_text, 
                call_duration, input_tokens, output_tokens, self._current_source_lang,
                model_name_for_costing, model_name_for_logging, model_source,
                api_version, media_resolution
            )
        
        log_debug(f"Gemini OCR result: '{parsed_text}' (took {call_duration:.3f}s)")
        # Return both model names
        return (parsed_text, input_tokens, output_tokens, model_name_for_costing, model_name_for_logging, model_source)

    def _get_model_costs(self, model_name):
        """Get the input/output costs for a given Gemini model."""
        return self.app.gemini_models_manager.get_model_costs(model_name)

    def _is_logging_enabled(self):
        """Check if Gemini API logging is enabled."""
        return self.app.gemini_api_log_enabled_var.get()

    def _log_complete_ocr_call(self, prompt, image_size, raw_response, parsed_response, 
                              call_duration, input_tokens, output_tokens, source_lang, 
                              model_name_for_costing, model_name_for_logging, model_source,
                              api_version='v1beta', media_resolution='MEDIUM'):
        """Log the complete OCR call with detailed information."""
        try:
            with self._log_lock:
                call_end_time = self._get_precise_timestamp()
                call_start_time = self._calculate_start_time(call_end_time, call_duration)
                
                # Get model costs
                model_costs = self._get_model_costs(model_name_for_costing)
                INPUT_COST_PER_MILLION = model_costs.get('input_cost', 0.1)
                OUTPUT_COST_PER_MILLION = model_costs.get('output_cost', 0.4)
                
                # Calculate costs
                call_input_cost = (input_tokens / 1_000_000) * INPUT_COST_PER_MILLION
                call_output_cost = (output_tokens / 1_000_000) * OUTPUT_COST_PER_MILLION
                total_call_cost = call_input_cost + call_output_cost
                
                # Get cumulative totals
                prev_total_input, prev_total_output, prev_total_cost = self._get_cumulative_totals_ocr()
                new_total_input = prev_total_input + input_tokens
                new_total_output = prev_total_output + output_tokens
                new_total_cost = prev_total_cost + total_call_cost
                
                # Update cache
                self._update_ocr_cache(input_tokens, output_tokens, total_call_cost)
                
                # Format cost strings
                input_cost_str = f"${INPUT_COST_PER_MILLION:.3f}" if (INPUT_COST_PER_MILLION * 1000) % 10 != 0 else f"${INPUT_COST_PER_MILLION:.2f}"
                output_cost_str = f"${OUTPUT_COST_PER_MILLION:.3f}" if (OUTPUT_COST_PER_MILLION * 1000) % 10 != 0 else f"${OUTPUT_COST_PER_MILLION:.2f}"
                
                # Create log entry
                log_entry = f"""
=== GEMINI OCR API CALL ===
Timestamp: {call_start_time}
Source Language: {source_lang}
Image Size: {image_size} bytes
Call Type: OCR Only

REQUEST PROMPT:
---BEGIN PROMPT---
{prompt}
---END PROMPT---

RESPONSE RECEIVED:
Model: {model_name_for_logging} ({model_source})
Requested version: {api_version}
Requested media resolution: {media_resolution}
Cost: input {input_cost_str}, output {output_cost_str} (per 1M)
Timestamp: {call_end_time}
Call Duration: {call_duration:.3f} seconds

---BEGIN RESPONSE---
{raw_response}
---END RESPONSE---

PERFORMANCE & COST ANALYSIS:
- Input Tokens: {input_tokens}
- Output Tokens: {output_tokens}
- Input Cost: ${call_input_cost:.8f}
- Output Cost: ${call_output_cost:.8f}
- Total Cost for this Call: ${total_call_cost:.8f}

CUMULATIVE TOTALS (INCLUDING THIS CALL, FROM LOG START):
- Total Input Tokens (OCR, so far): {new_total_input}
- Total Output Tokens (OCR, so far): {new_total_output}
- Total OCR Cost (so far): ${new_total_cost:.8f}

========================================

"""
                # Write to main log file
                with open(self.main_log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
                
                # Write to short log
                self._write_short_ocr_log(
                    call_start_time, call_end_time, call_duration, input_tokens, 
                    output_tokens, total_call_cost, new_total_input, new_total_output, 
                    new_total_cost, parsed_response, model_name_for_logging, model_source,
                    INPUT_COST_PER_MILLION, OUTPUT_COST_PER_MILLION
                )
                
        except Exception as e:
            log_debug(f"Error logging complete Gemini OCR call: {e}")

    def _write_short_ocr_log(self, call_start_time, call_end_time, call_duration, 
                            input_tokens, output_tokens, call_cost, cumulative_input, 
                            cumulative_output, cumulative_cost, parsed_result, 
                            model_name, model_source,
                            input_cost_per_million, output_cost_per_million):
        """Write a condensed log entry for OCR statistics."""
        try:
            cost_line = ""
            try:
                # Use the passed-in cost rates directly
                input_cost, output_cost = input_cost_per_million, output_cost_per_million
                input_str = f"${input_cost:.3f}" if (input_cost * 1000) % 10 != 0 else f"${input_cost:.2f}"
                output_str = f"${output_cost:.3f}" if (output_cost * 1000) % 10 != 0 else f"${output_cost:.2f}"
                cost_line = f"Cost: input {input_str}, output {output_str} (per 1M)\n"
            except Exception:
                pass
            
            log_entry = f"""========= OCR CALL ===========
Model: {model_name} ({model_source})
{cost_line}Start: {call_start_time}
End: {call_end_time}
Duration: {call_duration:.3f}s
Tokens: In={input_tokens}, Out={output_tokens} | Cost: ${call_cost:.8f}
Total (so far): In={cumulative_input}, Out={cumulative_output} | Cost: ${cumulative_cost:.8f}
Result:
--------------------------------------------------
{parsed_result}
--------------------------------------------------

"""
            with open(self.short_log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
                
        except Exception as e:
            log_debug(f"Error writing short OCR log: {e}")

    def _get_cumulative_totals_ocr(self):
        """Get cumulative totals for OCR usage from cache or log file."""
        if self._ocr_cache_initialized:
            return self._cached_ocr_input_tokens, self._cached_ocr_output_tokens, self._cached_ocr_cost
        
        total_input, total_output, total_cost = 0, 0, 0.0
        if not os.path.exists(self.main_log_file):
            self._ocr_cache_initialized = True
            return 0, 0, 0.0
        
        # Regular expressions to parse log file
        input_token_regex = re.compile(r"^\s*-\s*Total Input Tokens \(OCR, so far\):\s*(\d+)")
        output_token_regex = re.compile(r"^\s*-\s*Total Output Tokens \(OCR, so far\):\s*(\d+)")
        cost_regex = re.compile(r"^\s*-\s*Total OCR Cost \(so far\):\s*\$([0-9.]+)")
        
        try:
            with open(self.main_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if m := input_token_regex.match(line):
                        total_input = int(m.group(1))
                    if m := output_token_regex.match(line):
                        total_output = int(m.group(1))
                    if m := cost_regex.match(line):
                        total_cost = float(m.group(1))
            
            # Cache the results
            self._cached_ocr_input_tokens = total_input
            self._cached_ocr_output_tokens = total_output
            self._cached_ocr_cost = total_cost
            self._ocr_cache_initialized = True
            
            return total_input, total_output, total_cost
            
        except (IOError, ValueError) as e:
            log_debug(f"Error reading OCR cumulative totals: {e}")
            self._ocr_cache_initialized = True
            return 0, 0, 0.0

    def _update_ocr_cache(self, input_tokens, output_tokens, cost):
        """Update the cached OCR totals."""
        if not self._ocr_cache_initialized:
            self._get_cumulative_totals_ocr()
        
        self._cached_ocr_input_tokens += input_tokens
        self._cached_ocr_output_tokens += output_tokens
        self._cached_ocr_cost += cost

    def _get_next_ocr_image_number(self):
        """Get the next sequential number for OCR image saving."""
        try:
            # Get the base directory (same as where the script runs from)
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            ocr_images_dir = os.path.join(base_dir, "OCR_images")
            
            # Ensure the directory exists
            os.makedirs(ocr_images_dir, exist_ok=True)
            
            # Get all existing files in the directory
            if os.path.exists(ocr_images_dir):
                existing_files = os.listdir(ocr_images_dir)
                # Filter for .webp files and extract numbers
                numbers = []
                for filename in existing_files:
                    if filename.endswith('.webp'):
                        try:
                            # Extract number from filename like "0001.webp"
                            number_str = filename.split('.')[0]
                            if number_str.isdigit():
                                numbers.append(int(number_str))
                        except (ValueError, IndexError):
                            continue
                
                # Get the next number
                if numbers:
                    next_number = max(numbers) + 1
                else:
                    next_number = 1
            else:
                next_number = 1
            
            return next_number, ocr_images_dir
        except Exception as e:
            log_debug(f"Error getting next OCR image number: {e}")
            return 1, None
    
    def _save_ocr_image(self, webp_image_data):
        """Save the OCR image to the OCR_images folder with sequential numbering."""
        try:
            # Debug: Check what we received
            log_debug(f"_save_ocr_image called with data type: {type(webp_image_data)}")
            
            if webp_image_data is None:
                log_debug("webp_image_data is None, cannot save image")
                return
            
            if isinstance(webp_image_data, str):
                log_debug(f"webp_image_data is string with length: {len(webp_image_data)}")
                # If it's a string, it might be base64 encoded
                try:
                    import base64
                    webp_image_data = base64.b64decode(webp_image_data)
                    log_debug(f"Decoded base64 data, new length: {len(webp_image_data)}")
                except Exception as decode_error:
                    log_debug(f"Failed to decode base64 data: {decode_error}")
                    return
            elif isinstance(webp_image_data, bytes):
                log_debug(f"webp_image_data is bytes with length: {len(webp_image_data)}")
            else:
                log_debug(f"webp_image_data is unexpected type: {type(webp_image_data)}")
                return
            
            if len(webp_image_data) == 0:
                log_debug("webp_image_data is empty, cannot save image")
                return
            
            next_number, ocr_images_dir = self._get_next_ocr_image_number()
            
            if ocr_images_dir is None:
                log_debug("Could not determine OCR images directory, skipping image save")
                return
            
            # Format the filename with 4-digit zero-padding
            filename = f"{next_number:04d}.webp"
            filepath = os.path.join(ocr_images_dir, filename)
            
            # Save the image data
            with open(filepath, 'wb') as f:
                bytes_written = f.write(webp_image_data)
                log_debug(f"Wrote {bytes_written} bytes to {filepath}")
            
            # Verify the file was written correctly
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                log_debug(f"Successfully saved OCR image to: {filepath} (size: {file_size} bytes)")
            else:
                log_debug(f"File was not created: {filepath}")
            
        except Exception as e:
            log_debug(f"Error saving OCR image: {e}")
            import traceback
            log_debug(f"Full traceback: {traceback.format_exc()}")
            # Don't let image saving errors stop the OCR process
            pass
