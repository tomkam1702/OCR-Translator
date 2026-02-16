import base64
import time
import os
import re
from logger import log_debug
from .ocr_provider_base import AbstractOCRProvider
import json

# Import OpenAI dependencies
try:
    import openai
    OPENAI_AVAILABLE = True
    log_debug("OpenAI library available for OCR")
except ImportError:
    OPENAI_AVAILABLE = False
    log_debug("OpenAI library not available")


class OpenAIOCRProvider(AbstractOCRProvider):
    """OpenAI-specific OCR provider implementation using vision-capable models."""
    
    def __init__(self, app):
        super().__init__(app, "openai_ocr")
        
        # OCR-specific cache for cumulative totals (performance optimization)
        self._ocr_cache_initialized = False
        self._cached_ocr_input_tokens = 0
        self._cached_ocr_output_tokens = 0
        self._cached_ocr_cost = 0.0
        
        log_debug("OpenAIOCRProvider initialized")

    def _get_api_key(self):
        """Get the OpenAI API key from the application."""
        return self.app.openai_api_key_var.get().strip()

    def _check_provider_availability(self):
        """Check if OpenAI libraries are available."""
        return OPENAI_AVAILABLE

    def _initialize_client(self, api_key):
        """Initialize the OpenAI API client."""
        if not OPENAI_AVAILABLE:
            log_debug("OpenAI library not available for OCR session.")
            self.client = None
            return False

        if hasattr(self, 'client') and self._should_refresh_client():
            self._force_client_refresh()

        try:
            log_debug("Creating new OpenAI client for OCR")
            self.client = openai.OpenAI(api_key=api_key)
            self.session_api_key = api_key
            self.client_created_time = time.time()
            self.api_call_count = 0
            return self.client is not None
        except Exception as e:
            log_debug(f"Failed to initialize OpenAI OCR client: {e}")
            self.client = None
            return False

    def _make_api_call(self, image_data, source_lang):
        """Make the actual OpenAI OCR API call."""
        if self.client is None:
            raise Exception("OpenAI client not initialized")
        
        # Store source_lang for later use in logging
        self._current_source_lang = source_lang
        
        # Get the current OCR model
        ocr_model_api_name = self.app.get_current_openai_model_for_ocr() or 'gpt-4o'
        
        # Convert image data to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # OCR prompt optimized for text transcription
        if self.app.keep_linebreaks_var.get():
            prompt = """1. Transcribe the text from the image exactly as it appears. Do not correct, rephrase, or alter the words in any way. Provide a literal and verbatim transcription of all text in the image. Keep the linebreaks. Don't return anything else.
2. If there is no text in the image, return only: <EMPTY>."""
        else:
            prompt = """1. Transcribe the text from the image exactly as it appears. Do not correct, rephrase, or alter the words in any way. Provide a literal and verbatim transcription of all text in the image. Don't return anything else.
2. If there is no text in the image, return only: <EMPTY>."""
        
        # Create different message structures for different APIs
        if ocr_model_api_name.startswith('gpt-5'):
            # GPT-5 models use Responses API with specific message format
            input_data = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/webp;base64,{base64_image}"
                        }
                    ]
                }
            ]
        else:
            # Other models use Chat Completions API with standard content types
            input_data = [
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url", 
                            "image_url": {
                                "url": f"data:image/webp;base64,{base64_image}",
                                "detail": "low"
                            }
                        }
                    ]
                }
            ]

        # Make the API call
        api_call_start_time = time.time()
        
        if ocr_model_api_name.startswith('gpt-5'):
            log_debug(f"Using GPT 5 model {ocr_model_api_name} for OCR with minimal effort and low verbosity")
            # GPT 5 models use the Responses API
            response = self.client.responses.create(
                model=ocr_model_api_name,
                input=input_data,
                reasoning={'effort': 'minimal'},
                text={'verbosity': 'low'}
            )
        else:
            # Other models use the default Chat Completions API
            response = self.client.chat.completions.create(
                model=ocr_model_api_name,
                messages=input_data,
                temperature=0.0
            )
            
        call_duration = time.time() - api_call_start_time
        
        return response, call_duration, prompt, len(image_data)

    def _parse_response(self, response_data):
        """Parse the API response to extract text, tokens, and model info."""
        response, call_duration, prompt, image_size = response_data
        
        # Get model name for costing from app config
        model_name_for_costing = self.app.get_current_openai_model_for_ocr() or 'gpt-4o'

        ocr_result = ""
        input_tokens = 0
        output_tokens = 0

        if model_name_for_costing.startswith('gpt-5'):
            # GPT 5 models use Responses API
            ocr_result = response.output_text.strip() if hasattr(response, 'output_text') else response.text.strip()
            
            # Check for usage in different locations
            if hasattr(response, 'usage') and response.usage:
                input_tokens = getattr(response.usage, 'prompt_tokens', 0) or getattr(response.usage, 'input_tokens', 0)
                output_tokens = getattr(response.usage, 'completion_tokens', 0) or getattr(response.usage, 'output_tokens', 0)
            elif hasattr(response, 'input_tokens') and hasattr(response, 'output_tokens'):
                input_tokens = response.input_tokens
                output_tokens = response.output_tokens
            log_debug(f"OpenAI GPT-5 OCR usage metadata: In={input_tokens}, Out={output_tokens}")
            
            # Estimate tokens if not available in response
            if input_tokens == 0 or output_tokens == 0:
                input_tokens = max(input_tokens, int(len(str(response).split()) * 1.3))  # Rough estimate
                output_tokens = max(output_tokens, int(len(ocr_result.split()) * 1.3))  # Rough estimate
                log_debug(f"OpenAI GPT-5 OCR estimated tokens: In={input_tokens}, Out={output_tokens}")
        else:
            # Other models use Chat Completions API
            ocr_result = response.choices[0].message.content.strip() if response.choices and response.choices[0].message.content else "<EMPTY>"
            if hasattr(response, 'usage') and response.usage:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
            log_debug(f"OpenAI Chat Completions OCR usage metadata: In={input_tokens}, Out={output_tokens}")

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
        
        # Get model name for logging from API response
        model_name_for_logging = response.model if hasattr(response, 'model') else model_name_for_costing
        model_source = "api_response"
        
        if self._is_logging_enabled():
            self._log_complete_ocr_call(
                prompt, image_size, ocr_result, parsed_text, 
                call_duration, input_tokens, output_tokens, self._current_source_lang,
                model_name_for_costing, model_name_for_logging, model_source
            )
        
        log_debug(f"OpenAI OCR result: '{parsed_text}' (took {call_duration:.3f}s)")
        return (parsed_text, input_tokens, output_tokens, model_name_for_costing, model_name_for_logging, model_source)

    def _get_model_costs(self, model_name):
        """Get the input/output costs for a given OpenAI model."""
        return self.app.openai_models_manager.get_model_costs(model_name)

    def _is_logging_enabled(self):
        """Check if OpenAI API logging is enabled."""
        return self.app.openai_api_log_enabled_var.get()

    def _log_complete_ocr_call(self, prompt, image_size, raw_response, parsed_response, 
                              call_duration, input_tokens, output_tokens, source_lang,
                              model_name_for_costing, model_name_for_logging, model_source):
        """Log the complete OCR call with detailed information."""
        try:
            with self._log_lock:
                call_end_time = self._get_precise_timestamp()
                call_start_time = self._calculate_start_time(call_end_time, call_duration)
                
                # Get model costs
                model_costs = self._get_model_costs(model_name_for_costing)
                INPUT_COST_PER_MILLION = model_costs.get('input_cost', 5.0)  # Default to GPT-4o pricing
                OUTPUT_COST_PER_MILLION = model_costs.get('output_cost', 15.0)  # Default to GPT-4o pricing
                
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
=== OPENAI OCR API CALL ===
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
                with open(self.main_log_file, 'a', encoding='utf-8-sig') as f:
                    f.write(log_entry)
                
                # Write to short log
                self._write_short_ocr_log(
                    call_start_time, call_end_time, call_duration, input_tokens, 
                    output_tokens, total_call_cost, new_total_input, new_total_output, 
                    new_total_cost, parsed_response, model_name_for_logging, model_source,
                    INPUT_COST_PER_MILLION, OUTPUT_COST_PER_MILLION
                )
                
        except Exception as e:
            log_debug(f"Error logging complete OpenAI OCR call: {e}")

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
            with open(self.short_log_file, 'a', encoding='utf-8-sig') as f:
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
            with open(self.main_log_file, 'r', encoding='utf-8-sig') as f:
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