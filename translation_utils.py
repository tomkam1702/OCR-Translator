import re
from logger import log_debug

# Note: This function is retained for backward compatibility but should be replaced 
# with the LanguageManager class for new code. Translation handlers should use
# language_manager.get_tesseract_code() instead.
def get_lang_code_for_translation_api(lang_code):
    """Converts various language codes to standard ISO 639-1 for translation APIs."""
    code_map = {
        'eng': 'en', 'pol': 'pl', 'fra': 'fr', 'deu': 'de', 'spa': 'es',
        'ita': 'it', 'jpn': 'ja', 'kor': 'ko', 'chi_sim': 'zh-cn',
        'chi_tra': 'zh-tw', 'rus': 'ru', 'por': 'pt', 'nld': 'nl',
        'ara': 'ar', 'hin': 'hi', 'ukr': 'uk', 'ces': 'cs', 'dan': 'da',
        'fin': 'fi', 'swe': 'sv', 'nor': 'no', 'auto': 'auto'
    }
    if isinstance(lang_code, str):
        lang_code_lower = lang_code.lower()
        result = code_map.get(lang_code_lower, lang_code_lower)
        # log_debug(f"Converting language code '{lang_code}' to API code '{result}'") # Can be verbose
        return result
    return lang_code # Should be a string

def post_process_translation_text(text):
    if not text: return text
    text = re.sub(r'\s+\?', '?', text)
    text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text
