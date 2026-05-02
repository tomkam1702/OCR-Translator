# config_manager.py
import configparser
import os
import sys
from logger import log_debug
from resource_handler import get_resource_path

DEFAULT_CONFIG_SETTINGS = {
    'scan_interval': '300', 
    'clear_translation_timeout': '3',
    'source_area_x1': '427',
    'source_area_y1': '859',
    'source_area_x2': '1538',
    'source_area_y2': '1006',
    'source_area_visible': '0',
    'target_area_x1': '427',
    'target_area_y1': '42',
    'target_area_x2': '1538',
    'target_area_y2': '201',
    'source_area_colour': '#ffff99',
    'target_area_colour': '#162c43',
    'target_text_colour': '#ffffff',
    'target_font_size': '20',
    'target_font_type': 'Arial',
    'target_opacity': '0.85',
    'target_text_opacity': '1.0',    
    'deepl_api_key': '',
    'translation_model': 'gemini_api',
    'deepl_file_cache': 'True',
    'deepl_context_window': '2',
    'debug_logging_enabled': 'False',
    # Model-specific language defaults
    'gemini_source_lang': 'ja',
    'gemini_target_lang': 'en',
    'deepl_source_lang': 'DE',
    'deepl_target_lang': 'EN-GB',
    'gui_language':'English',
    # OCR Model Selection (Gemini OCR only)
    'ocr_model': 'gemini',
    # Gemini API settings
    'gemini_model_temp': '0.0',
    # Separate Gemini model selection for OCR and Translation
    'gemini_translation_model': 'Gemini 3.1 Flash-Lite',
    'gemini_ocr_model': 'Gemini 3.1 Flash-Lite (Low)',
    'gemini_context_window': '3',    
    'keep_linebreaks': 'False',
    # Auto-update settings
    'check_for_updates_on_startup': 'yes',
    # Auto-detection settings
    'auto_detect_enabled': 'False',
    'target_on_source_enabled': 'False',
    'capture_padding_enabled': 'False',
    'capture_padding': '100',
    'discovery_timeout': '120',
    'custom_prompt_enabled': 'False',
    'custom_ocr_prompt_enabled': 'False',
    'config_mode': 'Simple',
    'ui_visibility_mode': 'Hide',
    'top_visibility_mode': 'Show',
    'window_x': '-1',
    'window_y': '-1',
    'window_width': '-1',
    'window_height_show': '-1',
}

# Hardcoded settings for Simple configuration mode.
# When config_mode is 'Simple', these values override the corresponding
# keys from ocr_translator_config.ini. Keys NOT listed here are always
# read from the ini file regardless of mode.
SIMPLE_CONFIG_SETTINGS = {
    'scan_interval': '500',
    'clear_translation_timeout': '3',
    'source_area_colour': '#ffff99',
    'target_area_colour': '#162c43',
    'target_text_colour': '#ffffff',
    'target_font_size': '20',
    'target_font_type': 'Arial',
    'translation_model': 'gemini_api',
    'ocr_model': 'gemini',
    'gemini_model_temp': '0.0',
    'gemini_translation_model': 'Gemini 3.1 Flash-Lite',
    'gemini_ocr_model': 'Gemini 3.1 Flash-Lite (Low)',
    'keep_linebreaks': 'False',
    'auto_detect_enabled': 'False',
    'target_on_source_enabled': 'False',
    'capture_padding_enabled': 'False',
    'capture_padding': '100',
    'target_opacity': '0.85',
    'target_text_opacity': '1.0',
    'gemini_context_window': '3',
    'deepl_file_cache': 'True',
    'gemini_file_cache': 'True',
    'debug_logging_enabled': 'False',
    'gemini_api_log_enabled': 'True',
    'custom_prompt_enabled': 'False',
    'custom_ocr_prompt_enabled': 'False',
    'gemini_source_lang': 'auto',
    'deepl_source_lang': 'auto',
}


def load_app_config():
    """Loads configuration from INI file or creates default values."""
    config_path = 'ocr_translator_config.ini'
    config = configparser.ConfigParser()

    dynamic_defaults = DEFAULT_CONFIG_SETTINGS.copy()

    if os.path.exists(config_path):
        try:
            config.read(config_path, encoding='utf-8')
            if 'Settings' not in config:
                log_debug("Config file loaded but missing [Settings] section. Adding.")
                config['Settings'] = {}
        except Exception as e:
            log_debug(f"Error reading config file {config_path}: {e}. Using defaults.")
            config['Settings'] = {} 
    else:
         log_debug(f"Config file {config_path} not found. Creating with defaults.")
         config['Settings'] = {}

    settings_changed = False
    config_settings = config['Settings']

    # Obsolete keys check (add 'source_lang', 'target_lang', 'ocr_lang' if you are sure to remove them)
    obsolete_keys = ['api_key', 'gpu_enabled', 'spell_check_enabled', 'word_segmentation_enabled',
                    'spell_check_language', 'subtitle_mode', 'parallel_processing', 'target_text_bg_color',
                    'nllb_beam_size', 'source_lang', 'target_lang', 'ocr_lang', 'gemini_fuzzy_detection',
                    'input_token_cost', 'output_token_cost',
                    # Removed providers (Tesseract, MarianMT, Google Translate, OpenAI)
                    'tesseract_path', 'stability_threshold', 'image_preprocessing_mode',
                    'ocr_debugging', 'confidence_threshold', 'remove_trailing_garbage',
                    'adaptive_block_size', 'adaptive_c', 'num_beams',
                    'ocr_preview_geometry', 'ocr_preview_width', 'ocr_preview_height',
                    'ocr_preview_x', 'ocr_preview_y',
                    'google_translate_api_key', 'google_file_cache',
                    'google_source_lang', 'google_target_lang',
                    'marian_models_file', 'marian_model',
                    'openai_api_key', 'openai_context_window', 'openai_file_cache',
                    'openai_api_log_enabled', 'openai_translation_model', 'openai_ocr_model',
                    'openai_source_lang', 'openai_target_lang',
                    'deepl_model_type',
                    'main_window_geometry', 'main_window_width', 'main_window_height',
                    'main_window_x', 'main_window_y']
    for key in obsolete_keys:
        if key in config_settings:
            del config_settings[key]
            settings_changed = True
            log_debug(f"Config: Removed obsolete '{key}' setting.")

    # Migrate old model selections to Gemini
    current_translation_model = config_settings.get('translation_model', 'gemini_api')
    if current_translation_model in ('marianmt', 'google_api', 'openai_api') or current_translation_model.startswith('openai_'):
        config_settings['translation_model'] = 'gemini_api'
        settings_changed = True
        log_debug(f"Config: Migrated obsolete translation_model '{current_translation_model}' to 'gemini_api'")

    current_ocr_model = config_settings.get('ocr_model', 'gemini')
    if current_ocr_model == 'tesseract' or current_ocr_model.startswith('openai'):
        config_settings['ocr_model'] = 'gemini'
        settings_changed = True
        log_debug(f"Config: Migrated obsolete ocr_model '{current_ocr_model}' to 'gemini'")

    for key, value in dynamic_defaults.items():
        if key not in config_settings:
            # Only add discovery_timeout from defaults if the file is being created from scratch
            if key == 'discovery_timeout' and os.path.exists(config_path):
                continue
            config_settings[key] = value
            settings_changed = True
            log_debug(f"Config: Added missing key '{key}' with default value '{value}'.")



    if settings_changed or not os.path.exists(config_path):
         try:
            with open(config_path, 'w', encoding='utf-8') as f:
                config.write(f)
            log_debug("Config file saved/updated with defaults.")
         except Exception as e:
             log_debug(f"Error writing config file {config_path}: {e}")
    return config

def save_app_config(config_object):
    config_path = 'ocr_translator_config.ini'
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            config_object.write(f)
        log_debug(f"Settings saved successfully to {config_path}")
        return True
    except Exception as file_err:
        log_debug(f"Error writing settings to file: {file_err}")
        return False



