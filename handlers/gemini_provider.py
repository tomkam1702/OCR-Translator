# handlers/gemini_provider.py

import time
import sys

from logger import log_debug
from .llm_provider_base import AbstractLLMProvider

# Pre-load heavy libraries at module level for compiled version performance
try:
    # NEW: Google Gen AI library (migrated from google.generativeai)
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
    log_debug("Pre-loaded Google Gen AI libraries (new library)")
except ImportError:
    # Fallback to old library if new one not available
    try:
        import google.generativeai as genai
        from google.generativeai.types import HarmCategory, HarmBlockThreshold
        GENAI_AVAILABLE = True
        log_debug("Pre-loaded Google Generative AI libraries (legacy fallback)")
    except ImportError:
        GENAI_AVAILABLE = False
        log_debug("Google Generative AI libraries not available")


class GeminiProvider(AbstractLLMProvider):
    """Gemini-specific implementation of LLM translation provider."""
    
    def __init__(self, app):
        super().__init__(app, "gemini")
        
        # Gemini-specific attributes
        self.generation_config = None
        
        log_debug("Gemini provider initialized")
    
    # === ABSTRACT METHOD IMPLEMENTATIONS ===
    
    def _get_api_key(self):
        """Get Gemini API key."""
        return self.app.gemini_api_key_var.get().strip()
    
    def _check_provider_availability(self):
        """Check if Gemini libraries are available."""
        return GENAI_AVAILABLE
    
    def _get_context_window_size(self):
        """Get Gemini context window size setting."""
        return self.app.gemini_context_window_var.get()
    
    def _initialize_client(self, api_key, source_lang, target_lang):
        """Initialize Gemini client session."""
        if not GENAI_AVAILABLE:
            log_debug("Google Gen AI libraries not available for Gemini session")
            self.client = None
            return
            
        # Force refresh if needed
        if hasattr(self, 'client') and self._should_refresh_client():
            self._force_client_refresh()
            
        try:
            # NEW: Client-based approach
            self.client = genai.Client(api_key=api_key)
            
            # Store session creation time for tracking
            self.client_created_time = time.time()
            self.api_call_count = 0
            
            # Get configuration values
            model_temperature = float(self.app.config['Settings'].get('gemini_model_temp', '0.0'))
            
            # Store config for later use in API calls
            try:
                # Try to use thinking_config for models that support it (Gemini 2.5 series)
                self.generation_config = types.GenerateContentConfig(
                    temperature=model_temperature,
                    max_output_tokens=1024,
                    candidate_count=1,
                    top_p=0.95,
                    top_k=40,
                    response_mime_type="text/plain",
                    thinking_config=types.ThinkingConfig(thinking_budget=0),  # Use non-thinking mode for speed/cost
                    safety_settings=[
                        types.SafetySetting(
                            category='HARM_CATEGORY_HARASSMENT',
                            threshold='BLOCK_NONE'
                        ),
                        types.SafetySetting(
                            category='HARM_CATEGORY_HATE_SPEECH', 
                            threshold='BLOCK_NONE'
                        ),
                        types.SafetySetting(
                            category='HARM_CATEGORY_SEXUALLY_EXPLICIT',
                            threshold='BLOCK_NONE'
                        ),
                        types.SafetySetting(
                            category='HARM_CATEGORY_DANGEROUS_CONTENT',
                            threshold='BLOCK_NONE'
                        )
                    ]
                )
                log_debug("Gemini session initialized with thinking_budget=0 for non-thinking mode")
            except (AttributeError, TypeError) as e:
                # Fallback for models that don't support thinking_config
                log_debug(f"Model doesn't support thinking_config, using fallback config: {e}")
                self.generation_config = types.GenerateContentConfig(
                    temperature=model_temperature,
                    max_output_tokens=1024,
                    candidate_count=1,
                    top_p=0.95,
                    top_k=40,
                    response_mime_type="text/plain",
                    safety_settings=[
                        types.SafetySetting(
                            category='HARM_CATEGORY_HARASSMENT',
                            threshold='BLOCK_NONE'
                        ),
                        types.SafetySetting(
                            category='HARM_CATEGORY_HATE_SPEECH', 
                            threshold='BLOCK_NONE'
                        ),
                        types.SafetySetting(
                            category='HARM_CATEGORY_SEXUALLY_EXPLICIT',
                            threshold='BLOCK_NONE'
                        ),
                        types.SafetySetting(
                            category='HARM_CATEGORY_DANGEROUS_CONTENT',
                            threshold='BLOCK_NONE'
                        )
                    ]
                )
            
            # Store session tracking
            self.session_api_key = api_key
            
            log_debug(f"Gemini client initialized for stateless calls (no chat session)")
            
        except Exception as e:
            log_debug(f"Failed to initialize Gemini client: {e}")
            self.client = None
    
    def _get_model_config(self):
        """Get Gemini model configuration for API calls."""
        # Get the appropriate model for translation
        translation_model_api_name = self.app.get_current_gemini_model_for_translation()
        if not translation_model_api_name:
            # Fallback to config if no specific model selected
            translation_model_api_name = self.app.config['Settings'].get('gemini_model_name', 'gemini-2.5-flash-lite')
        
        # Determine strictness/thought configuration based on model version
        # Gemini 3.0 uses 'thinking_level', Gemini 2.5 uses 'thinking_budget'
        current_config = self.generation_config
        
        try:
            if "gemini-3" in translation_model_api_name.lower():
                # Gemini 3 specific config: Temperature 0, Minimal Thinking
                if GENAI_AVAILABLE:
                    from google.genai import types
                    current_config = types.GenerateContentConfig(
                        temperature=0.0,  # Strict temperature for Gemini 3
                        max_output_tokens=1024,
                        candidate_count=1,
                        top_p=0.95,
                        top_k=40,
                        response_mime_type="text/plain",
                        thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"), # Use MINIMAL for Gemini 3
                        safety_settings=[
                            types.SafetySetting(category=c, threshold='BLOCK_NONE')
                            for c in ['HARM_CATEGORY_HARASSMENT', 'HARM_CATEGORY_HATE_SPEECH', 
                                     'HARM_CATEGORY_SEXUALLY_EXPLICIT', 'HARM_CATEGORY_DANGEROUS_CONTENT']
                        ]
                    )
            else:
                 # Default config (already set in __init__ with thinking_budget=0 if supported)
                 pass
        except Exception as e:
            log_debug(f"Error configuring specific settings for model {translation_model_api_name}: {e}")
            # Fallback to default self.generation_config
        
        return {
            'api_name': translation_model_api_name,
            'config': current_config
        }
    
    def _make_api_call(self, message_content, model_config):
        """Make Gemini-specific API call."""
        if not hasattr(self, 'client') or self.client is None:
            raise Exception("Gemini client not initialized")
        
        response = self.client.models.generate_content(
            model=model_config['api_name'],
            contents=message_content,
            config=model_config['config']
        )
        
        return response
    
    def _parse_response(self, response):
        """Parse Gemini response and extract relevant information."""
        # Get the model name for costing from the app configuration (the one we requested)
        model_name_for_costing = self.app.get_current_gemini_model_for_translation() or 'gemini-2.5-flash-lite'
        
        input_tokens, output_tokens = 0, 0
        model_source = "api_request"
        
        try:
            if response.usage_metadata:
                input_tokens = response.usage_metadata.prompt_token_count or 0
                output_tokens = response.usage_metadata.candidates_token_count or 0
            
            # Get the model name for logging from the actual API response
            model_name_for_logging = "unknown"
            if hasattr(response, 'model_version') and response.model_version:
                model_name_for_logging = response.model_version
            elif hasattr(response, '_response') and hasattr(response._response, 'model_version'):
                model_name_for_logging = response._response.model_version
            else:
                model_name_for_logging = model_name_for_costing # Fallback
            log_debug(f"Gemini model used (for logging): {model_name_for_logging} (source: {model_source})")

        except (AttributeError, KeyError):
            log_debug("Could not find usage_metadata or model info in Gemini response.")
            model_name_for_logging = model_name_for_costing # Fallback

        translation_result = response.text.strip()
        
        # Handle multiple lines based on keep_linebreaks setting
        if self.app.keep_linebreaks_var.get():
            # Keep linebreaks by replacing them with <br>
            translation_result = translation_result.replace('\n', '<br>')
        else:
            # Original behavior: collapse newlines and take the last line of output
            if '\n' in translation_result:
                lines = translation_result.split('\n')
                # Filter out empty lines and take the last non-empty line
                non_empty_lines = [line.strip() for line in lines if line.strip()]
                if non_empty_lines:
                    translation_result = non_empty_lines[-1]
                else:
                    translation_result = lines[-1].strip() if lines else ""
        
        # Strip language prefixes from the result
        translation_result = self._clean_language_prefixes(translation_result)
        
        # Return both model names
        return translation_result, input_tokens, output_tokens, model_name_for_costing, model_name_for_logging, model_source
    
    def _clean_language_prefixes(self, text):
        """Remove language prefixes from Gemini response."""
        # Get target language display name
        if hasattr(self, 'current_target_lang'):
            target_lang_name = self._get_language_display_name(self.current_target_lang)
            target_lang_upper = target_lang_name.upper()
            target_lang_code = self.current_target_lang
            
            # Check for uppercase language name with colon and space
            if text.startswith(f"{target_lang_upper}: "):
                return text[len(f"{target_lang_upper}: "):].strip()
            # Check for uppercase language name with colon only
            elif text.startswith(f"{target_lang_upper}:"):
                return text[len(f"{target_lang_upper}:"):].strip()
            # Also check for the old format (lowercase language code) just in case
            elif text.startswith(f"{target_lang_code}: "):
                return text[len(f"{target_lang_code}: "):].strip()
            elif text.startswith(f"{target_lang_code}:"):
                return text[len(f"{target_lang_code}:"):].strip()
        
        return text
    
    def _get_model_costs(self, model_name):
        """Get Gemini model-specific costs."""
        try:
            if hasattr(self.app, 'gemini_models_manager') and self.app.gemini_models_manager:
                model_costs = self.app.gemini_models_manager.get_model_costs(model_name)
                return model_costs['input_cost'], model_costs['output_cost']
        except Exception as e:
            log_debug(f"Error getting Gemini model costs for {model_name}: {e}")
        
        # Fallback to default Gemini 2.5 Flash-Lite costs
        return 0.1, 0.4
    
    def _is_logging_enabled(self):
        """Check if Gemini logging is enabled."""
        return self.app.gemini_api_log_enabled_var.get()
    
    def _should_suppress_error(self, error_str):
        """Check if Gemini error should be suppressed from display."""
        # Suppress 503 errors from being displayed in translation window
        return "503 UNAVAILABLE" in error_str
