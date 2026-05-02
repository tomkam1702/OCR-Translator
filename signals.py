"""
WorkerSignals — Central hub for Qt signals used for thread-to-UI communication.
Replaces legacy event loop polling with native Qt signal/slot mechanism.
"""

from PySide6.QtCore import QObject, Signal


class WorkerSignals(QObject):
    """
    Defines available signals for worker threads.
    """
    # OCR signals
    ocr_response = Signal(object, int, str, str, bool) # (ocr_result, sequence_number, source_lang, provider_name, is_auto_detect)
    
    # Translation signals
    translation_response = Signal(str, int, str, int) # (translated_text, translation_sequence, original_text, ocr_sequence_number)
    
    # Hotkeys signals
    hotkey_toggle_translation = Signal()
    hotkey_toggle_source = Signal()
    hotkey_toggle_target = Signal()
    hotkey_save_settings = Signal()
    hotkey_clear_cache = Signal()
    hotkey_clear_debug_log = Signal()
