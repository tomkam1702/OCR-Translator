from PySide6.QtCore import QTimer, QMetaObject, Qt
from PySide6.QtWidgets import QApplication, QWidget, QFrame, QLabel
import qt_dialogs as messagebox
import qt_dialogs as filedialog
# --- Configuration ---

import numpy as np
import cv2
import threading
import time
import queue
import sys
from PIL import Image
import os
import nuitka_compat
import re
import gc
import traceback
import io
import base64
import concurrent.futures
import webbrowser

from logger import log_debug, set_debug_logging_enabled, is_debug_logging_enabled
from resource_handler import get_resource_path
from config_manager import load_app_config, save_app_config, SIMPLE_CONFIG_SETTINGS
from overlay_manager import (
    create_source_overlay_om, create_target_overlay_om,
    toggle_source_visibility_om, toggle_target_visibility_om, load_areas_from_config_om
)
from worker_threads import run_capture_thread, run_ocr_thread, run_translation_thread
from language_manager import LanguageManager
from language_ui import UILanguageManager

from constants import APP_VERSION, APP_RELEASE_DATE, APP_RELEASE_DATE_POLISH
from handlers import (
    CacheManager, 
    ConfigurationHandler, 
    DisplayManager, 
    HotkeyHandler, 
    StatisticsHandler,
    TranslationHandler, 
    UIInteractionHandler
)
from handlers.gemini_models_manager import GeminiModelsManager

KEYBOARD_AVAILABLE = False
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    pass 

DEEPL_API_AVAILABLE = False  # DeepL disabled in open-source edition

GEMINI_API_AVAILABLE = False
try:
    from google import genai
    GEMINI_API_AVAILABLE = True
except ImportError as e:
    log_debug(f"Gemini API libraries not available: {e}")
except Exception as e:
    log_debug(f"Unexpected error importing Gemini API libraries: {e}")



class GameChangingTranslator:
    def __init__(self, root=None):
        self.root = root
        
         
        
        
        
        self._fully_initialized = False # Flag for settings save callback
        self.toggle_in_progress = False

        self.KEYBOARD_AVAILABLE = KEYBOARD_AVAILABLE
        self.DEEPL_API_AVAILABLE = DEEPL_API_AVAILABLE
        self.GEMINI_API_AVAILABLE = GEMINI_API_AVAILABLE
        
        # Debug: Log execution environment information
        import sys
        is_compiled = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
        log_debug(f"Application execution environment:")
        log_debug(f"  Compiled/Frozen: {is_compiled}")
        if is_compiled:
            log_debug(f"  Executable path: {sys.executable}")
            log_debug(f"  Bundle dir: {getattr(sys, '_MEIPASS', 'Unknown')}")
        else:
            log_debug(f"  Python script mode")
            log_debug(f"  Script path: {__file__}")
        
        log_debug(f"Library availability check:")
        if not KEYBOARD_AVAILABLE: log_debug("  Keyboard library not available. Hotkeys disabled.")
        else: log_debug("  Keyboard library: available")
        if not DEEPL_API_AVAILABLE: log_debug("  DeepL API libraries not available.")
        else: log_debug("  DeepL API libraries: available")
        if not GEMINI_API_AVAILABLE: log_debug("  Gemini API libraries not available.")
        else: log_debug("  Gemini API libraries: available")

        self.source_area = None 
        self.target_area = None 
        self.is_running = False 
        self.is_photo_mode_active = False  # Screenshot freeze flag for capture thread
        self.threads = [] 
        self.last_image_hash = None 
        self.source_overlay = None
        self.target_overlay = None
        self.translation_text = None
        self.text_stability_counter = 0 
        self.previous_text = "" 
        self.last_screenshot = None 
        self.last_processed_image = None 
        self.raw_image_for_gemini = None  # WebP bytes ready for Gemini API 
        
        # Gemini OCR Batch Infrastructure (Phase 1)
        self.last_processed_subtitle = None  # Store last processed subtitle for successive comparison
        self.batch_sequence_counter = 0  # Track batch sequence numbers
        self.clear_timeout_timer_start = None  # Timer for clear translation timeout
        self.active_ocr_calls = set()  # Track active async OCR calls
        self.max_concurrent_ocr_calls = 3 # 3 is plenty for Regional mode
        
        # Gemini OCR Simple Management (No Queue for Gemini)
        self.last_displayed_batch_sequence = 0  # Track chronological order
        
        # Translation Async Processing Infrastructure (Phase 2)
        self.translation_sequence_counter = 0  # Track translation sequence numbers
        self.last_displayed_translation_sequence = 0  # Track chronological order for translations
        self.active_translation_calls = set()  # Track active async translation calls
        self.max_concurrent_translation_calls = 6  # Limit concurrent translation API calls
        
        # Initialize thread pools for optimized performance (especially for compiled version)
        self.ocr_thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=8, 
            thread_name_prefix="ApiOCR"
        )
        self.translation_thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=6, 
            thread_name_prefix="Translation"
        )
        log_debug("Initialized thread pools for OCR and translation processing")
        
        # Adaptive Scan Interval Infrastructure
        self.base_scan_interval = 500  # User's preferred setting (will be updated from config)
        self.current_scan_interval = 500  # Dynamic value used by capture thread
        self.load_check_timer = 0
        self.overload_detected = False
        log_debug("Initialized adaptive scan interval infrastructure")
        
        # OCR Preview window
        self.ocr_preview_window = None

        self.config = load_app_config()
        self.language_manager = LanguageManager()
        
        # Initialize UI language manager with the saved language if available
        saved_language_display = self.config['Settings'].get('gui_language', 'English')
        self.ui_lang = UILanguageManager()
        if saved_language_display != 'English':
            lang_code = self.ui_lang.get_language_code_from_name(saved_language_display)
            if lang_code:
                self.ui_lang.load_language(lang_code)
                log_debug(f"Loaded UI language from config: {lang_code}")

        self._save_timer = None
        self._save_settings_timer = None

        # Initialize Variables FIRST ---
        self.source_colour = self.config['Settings'].get('source_area_colour', '#FFFF99')
        self.target_colour = self.config['Settings'].get('target_area_colour', '#663399')
        self.target_text_colour = self.config['Settings'].get('target_text_colour', '#FFFFFF')
        self.gui_language = self.config['Settings'].get('gui_language', 'English')
        self.check_for_updates_on_startup = self.config['Settings'].get('check_for_updates_on_startup', 'yes') == 'yes'
        self.keep_linebreaks = self.config.getboolean('Settings', 'keep_linebreaks', fallback=False)
        self.auto_detect_enabled = self.config.getboolean('Settings', 'auto_detect_enabled', fallback=False)
        self.target_on_source_enabled = self.config.getboolean('Settings', 'target_on_source_enabled', fallback=False)
        self.capture_padding_enabled = self.config.getboolean('Settings', 'capture_padding_enabled', fallback=True)
        self.capture_padding = self.config.getint('Settings', 'capture_padding', fallback=100)
        self.discovery_timeout = self.config.getint('Settings', 'discovery_timeout', fallback=120)
        self.debug_logging_enabled = self.config.getboolean('Settings', 'debug_logging_enabled', fallback=False)
        self.config_mode = self.config['Settings'].get('config_mode', 'Advanced')
        self.ui_visibility_mode = self.config['Settings'].get('ui_visibility_mode', 'Show')
        self.top_visibility_mode = self.config['Settings'].get('top_visibility_mode', 'Show')
        
        # Detection results and stabilization
        self.detected_source_area_x1 = 0
        self.detected_source_area_y1 = 0
        self.detected_source_area_x2 = 0
        self.detected_source_area_y2 = 0
        self.detection_samples = [] # List of [x1, y1, x2, y2] normalized samples
        self.discovery_start_time = 0
        self.is_finishing_discovery = False
        self.restart_after_shutdown = False
        
        # OCR Model Selection (Phase 1 - Gemini OCR)
        self.ocr_model = self.config['Settings'].get('ocr_model', 'gemini')
        
        self.deepl_api_key = self.config['Settings'].get('deepl_api_key', '')
        self.deepl_api_client = None
        self.gemini_api_key = self.config['Settings'].get('gemini_api_key', '')
        self.deepl_usage = "Loading..."
        
        translation_model_val = self.config['Settings'].get('translation_model', 'gemini_api')
        # Fallback logic if configured model's library is not available




        self.translation_model = translation_model_val

        # Define translation model names and values earlier
        # Initialize with default values, will be updated with localized versions
        self.translation_model_names = {
            'gemini_api': 'Gemini 2.5 Flash-Lite',
            'deepl_api': 'DeepL API',
        }
        
        # Initialize Gemini Models Manager before updating model names
        self.gemini_models_manager = GeminiModelsManager()
        

        
        # Update with localized names after UI language is loaded
        self.update_translation_model_names()
        self.translation_model_values = {v: k for k, v in self.translation_model_names.items()}

        self.deepl_cache_enabled = self.config.getboolean('Settings', 'deepl_file_cache', fallback=True)
        self.deepl_context_window = int(self.config['Settings'].get('deepl_context_window', '2'))
        self.gemini_cache_enabled = self.config.getboolean('Settings', 'gemini_file_cache', fallback=True)
        self.gemini_context_window = int(self.config['Settings'].get('gemini_context_window', '1'))
        self.gemini_api_log_enabled = self.config.getboolean('Settings', 'gemini_api_log_enabled', fallback=True)
        self.custom_prompt_enabled = self.config.getboolean('Settings', 'custom_prompt_enabled', fallback=True)
        self.custom_ocr_prompt_enabled = self.config.getboolean('Settings', 'custom_ocr_prompt_enabled', fallback=True)
        
        # Separate Gemini model selection for OCR and Translation
        self.gemini_translation_model = self.config['Settings'].get('gemini_translation_model', 'Gemini 2.5 Flash-Lite')
        self.gemini_ocr_model = self.config['Settings'].get('gemini_ocr_model', 'Gemini 2.5 Flash-Lite')
        
        # Gemini statistics variables (initialized by GUI builder)
        self.gemini_total_words = ""
        self.gemini_total_cost = ""

        self.scan_interval = int(self.config['Settings'].get('scan_interval', '100'))
        
        # Initialize adaptive scan interval values from user configuration
        initial_scan_interval = self.scan_interval
        self.base_scan_interval = initial_scan_interval  # Update with user's actual setting
        self.current_scan_interval = initial_scan_interval  # Start with user's setting
        log_debug(f"Initialized adaptive scan interval: base={self.base_scan_interval}ms, current={self.current_scan_interval}ms")
        
        self.clear_translation_timeout = int(float(self.config['Settings'].get('clear_translation_timeout', '3')))
        
        self.target_font_size = int(float(self.config['Settings'].get('target_font_size', '12')))
        self.target_font_type = self.config['Settings'].get('target_font_type', 'Arial')
        self.target_opacity = float(self.config['Settings'].get('target_opacity', '0.15'))
        self.target_text_opacity = float(self.config['Settings'].get('target_text_opacity', '1.0'))

        self.deepl_source_lang = self.config['Settings'].get('deepl_source_lang', 'auto')
        self.deepl_target_lang = self.config['Settings'].get('deepl_target_lang', 'EN-GB')
        self.gemini_source_lang = self.config['Settings'].get('gemini_source_lang', 'en')
        self.gemini_target_lang = self.config['Settings'].get('gemini_target_lang', 'pl')

        # Apply Simple mode overrides if applicable (after all ini values are loaded)
        self.apply_simple_overrides()
        self.apply_pro_overrides()

        # Initialize OCR model display variable here to ensure it persists across UI rebuilds
        self.ocr_model_display = ""
        initial_ocr_model_code = self.ocr_model
        initial_ocr_display_name = ""
        if self.is_gemini_model(initial_ocr_model_code):
            saved_gemini_ocr_model = self.config['Settings'].get('gemini_ocr_model', '')
            if saved_gemini_ocr_model and self.GEMINI_API_AVAILABLE and saved_gemini_ocr_model in self.gemini_models_manager.get_ocr_model_names():
                initial_ocr_display_name = saved_gemini_ocr_model

        
        # Fallback if no specific display name was found
        if not initial_ocr_display_name:
            initial_ocr_display_name = "Gemini 2.5 Flash-Lite"

        self.ocr_model_display = initial_ocr_display_name
        
        # Initialize Handlers
        # self.cache_manager = CacheManager(self)
        self.configuration_handler = ConfigurationHandler(self)
        self.display_manager = DisplayManager(self)
        self.hotkey_handler = HotkeyHandler(self)
        self.statistics_handler = StatisticsHandler(self)
        self.translation_handler = TranslationHandler(self)
        self.ui_interaction_handler = UIInteractionHandler(self) # Needs self.translation_model_names
        
        # Bind window configuration after handlers are initialized to avoid AttributeErrors

        # Pre-initialize Gemini model for optimal performance (especially for compiled version)
        self._pre_initialize_gemini_model()

        # Initialize trace suppression mechanism and UI update detection
        
        
        def _settings_changed_callback_internal(*args, **kwargs):
            if self._fully_initialized and not self._suppress_traces and not self._ui_update_in_progress:
                self.save_settings()
            elif self._suppress_traces:
                log_debug("UI setting change trace suppressed during update")
            elif self._ui_update_in_progress:
                log_debug("UI setting change trace suppressed during update operation")

        

        # Scan interval validation callback for Gemini OCR minimum
        def _scan_interval_changed_callback(*args, **kwargs):
            if self._fully_initialized and not self._suppress_traces and not self._ui_update_in_progress:
                # Validate minimum scan interval for Gemini OCR
                if self.get_ocr_model_setting() == 'gemini':
                    current_value = self.scan_interval
                    if current_value < 500:
                        log_debug(f"Scan interval {current_value}ms too low for Gemini OCR, setting to 500ms minimum")
                        self.scan_interval = 500
                        return  # Skip save_settings since we just changed the value
                
                # Update adaptive scan interval when user changes scan interval
                new_scan_interval = self.scan_interval
                if hasattr(self, 'base_scan_interval') and new_scan_interval != self.base_scan_interval:
                    self.base_scan_interval = new_scan_interval
                    # Reset to new base if not currently overloaded, or update overloaded value
                    if not self.overload_detected:
                        self.current_scan_interval = new_scan_interval
                        log_debug(f"Adaptive scan interval updated: base={self.base_scan_interval}ms, current={self.current_scan_interval}ms")
                    else:
                        self.current_scan_interval = int(new_scan_interval * 1.5)  # Maintain 150% overload ratio
                        log_debug(f"Adaptive scan interval updated during overload: base={self.base_scan_interval}ms, current={self.current_scan_interval}ms")
                
                self.save_settings()
            elif self._suppress_traces:
                log_debug("Scan interval trace suppressed during update")
            elif self._ui_update_in_progress:
                log_debug("Scan interval trace suppressed during update operation")

        

        # Add traces
                                  # Special validation callback
                                                                                                                                
        # Other instance variables
        # Increased queue sizes from 4/3 to 8/6 to reduce queue management overhead
        self.ocr_queue = queue.Queue(maxsize=8)  # Increased from 4 for better buffering
        self.translation_queue = queue.Queue(maxsize=6)  # Increased from 3 for better buffering
        self.last_successful_translation_time = 0.0
        self.min_translation_interval = 0.3
        self.last_translation_time = time.monotonic()
        self.deepl_api_key_visible = False
        self.gemini_api_key_visible = False
        

        base_dir = nuitka_compat.get_base_dir()
        
        self.deepl_cache_file = os.path.join(base_dir, "deepl_cache.txt")
        self.gemini_cache_file = os.path.join(base_dir, "gemini_cache.txt")
        self.custom_prompt_file = os.path.join(base_dir, "custom_prompt.txt")
        self.custom_ocr_prompt_file = os.path.join(base_dir, "custom_ocr_prompt.txt")
        log_debug(f"Cache file paths: DeepL: {self.deepl_cache_file}, Gemini: {self.gemini_cache_file}")
        
        self.custom_prompt_text = ""
        self.custom_ocr_prompt_text = ""
        self.load_custom_prompt()
        
        self.deepl_cache_dict = {}
        self.gemini_cache_dict = {}
        self.translation_cache = {}
        
        self.cache_manager = CacheManager(self)
        
        # Initialize Update Checker
        



        self.clear_translation_timeout = self.clear_translation_timeout

        if not self.deepl_source_lang: self.deepl_source_lang = 'auto'
        if not self.deepl_target_lang: self.deepl_target_lang = 'EN-GB'

        self.cache_manager.load_file_caches()
        
        # Initialize debug logging state
        set_debug_logging_enabled(self.debug_logging_enabled)

        # Initialize UI display strings here so they exist before create_settings_tab
        self.source_display = "" 
        self.target_display = ""
        
        # This uses self.translation_model_names, so it must be after its definition
        initial_model_code_for_display = self.translation_model
        initial_display_name_for_model_combo = ""
        
        if initial_model_code_for_display == 'gemini_api':
            initial_display_name_for_model_combo = self.gemini_translation_model
        else:
            initial_display_name_for_model_combo = self.translation_model_names.get(initial_model_code_for_display, 'DeepL API')
            
        self.translation_model_display = initial_display_name_for_model_combo
        
        active_model_for_init = self.translation_model
        initial_source_val, initial_target_val = 'auto', 'en' 

        if active_model_for_init == 'deepl_api':
            initial_source_val = self.deepl_source_lang if hasattr(self, 'deepl_source_lang') else 'auto'
            initial_target_val = self.deepl_target_lang if hasattr(self, 'deepl_target_lang') else 'en'
        elif active_model_for_init == 'gemini_api':
            initial_source_val = self.gemini_source_lang if hasattr(self, 'gemini_source_lang') else 'auto'
            initial_target_val = self.gemini_target_lang if hasattr(self, 'gemini_target_lang') else 'en'
        else:
            # Fallback to Gemini if nothing else works or unknown model
            initial_source_val = 'auto'
            initial_target_val = 'en'
            self.translation_model = 'gemini_api'


        self.source_lang = initial_source_val 
        self.target_lang = initial_target_val
        
        self.lang_code_to_name = self.language_manager 

        # Create the main tabs (Handled by PySide GUI)
        
        
        
        # Initialize localized dropdowns after everything is set up
        QTimer.singleShot(50, self.ui_interaction_handler.update_all_dropdowns_for_language_change)

        QTimer.singleShot(100, self.load_initial_overlay_areas)
        QTimer.singleShot(200, self.ensure_window_visible)
        self.hotkey_handler.setup_hotkeys()
        
        # Add periodic network cleanup
        self.setup_network_cleanup()
        
        log_debug("Application initialized sequence complete.")
        self._fully_initialized = True
        log_debug("GameChangingTranslator fully initialized.")
        
        # Start overlay movement polling for PySide6 (save to INI)
        self._start_pyside_move_polling()
        
        # Initialise and connect Qt signals (replaces legacy root.after polling)
        try:
            from signals import WorkerSignals
            import worker_threads
            self.signals = WorkerSignals()
            
            # Connect signals, passing 'self' as the first argument (app)
            self.signals.ocr_response.connect(
                lambda *args: worker_threads.process_api_ocr_response(self, *args)
            )
            self.signals.translation_response.connect(
                lambda *args: worker_threads.process_translation_response(self, *args)
            )
            
            log_debug("WorkerSignals initialized and connected successfully.")
        except Exception as e_sig:
            log_debug(f"Failed to initialize WorkerSignals: {e_sig}")


        
        # Open-source version: no auto-updates on startup
        log_debug("App started (Open-Source Edition)")
        
        # Ensure OCR model UI is correctly set up on initial load
        if hasattr(self, 'ui_interaction_handler'):
            self.ui_interaction_handler.update_ocr_model_ui()
        
        # Update usage statistics for selected models - use after_idle to ensure GUI is ready
        if hasattr(self, 'translation_model'):
            selected_model = self.translation_model
            if selected_model == 'gemini_api':
                QTimer.singleShot(0, lambda: self._delayed_gemini_stats_update())
            elif selected_model == 'deepl_api':
                QTimer.singleShot(0, lambda: self._delayed_deepl_usage_update())
        
        # Always update DeepL usage since it's now always visible in API Usage tab
        QTimer.singleShot(0, lambda: self._delayed_deepl_usage_update())
        
        # Refresh API statistics for the new API Usage tab
        QTimer.singleShot(0, lambda: self._delayed_api_stats_refresh())

    def _delayed_api_stats_refresh(self):
        """Delayed API statistics refresh to ensure GUI is fully ready."""
        try:
            self.refresh_api_statistics()
        except Exception as e:
            log_debug(f"Error in delayed API statistics refresh: {e}")

    def ensure_window_visible(self):
        """Ensure the main window is visible after all initialization is complete."""
        # Suppress during discovery transition to prevent taskbar popup
        if getattr(self, 'is_finishing_discovery', False):
            log_debug("Discovery transition in progress, skipping main window liftoff")
            return

        try:
            if self.root != None:
                self.deiconify()
                self.lift()
                log_debug("Main window visibility ensured after initialization")
        except Exception as e:
            log_debug(f"Error ensuring window visibility: {e}")

    def on_ocr_parameter_change(self, *args):
        """Called when OCR parameters change to refresh preview if it's open."""
        if self.ocr_preview_window is not None:
            try:
                if self.ocr_preview_window != None:
                    # Delay the refresh slightly to avoid too frequent updates
                    if hasattr(self, '_preview_refresh_timer'):
                        pass
                    self._preview_refresh_timer = QTimer.singleShot(200, self.refresh_ocr_preview)
                else:
                    # Window was destroyed but reference wasn't cleared
                    self.ocr_preview_window = None
            except Exception:
                # Window was destroyed
                self.ocr_preview_window = None

    def on_ocr_model_change(self, *args):
        """Called when OCR model selection changes to update UI visibility."""
        try:
            # End OCR session if switching away from Gemini and translation is running
            if (hasattr(self, 'translation_handler') and self.is_running and 
                self.get_ocr_model_setting() != 'gemini'):
                self.translation_handler.request_end_ocr_session()
            
            # Start OCR session if switching to Gemini and translation is running
            if (hasattr(self, 'translation_handler') and self.is_running and 
                self.get_ocr_model_setting() == 'gemini'):
                self.translation_handler.start_ocr_session()
            

            if hasattr(self, 'ui_interaction_handler'):
                self.ui_interaction_handler.update_ocr_model_ui()
            
            # Validate scan interval when switching to Gemini OCR
            if self.get_ocr_model_setting() == 'gemini':
                current_value = self.scan_interval
                if current_value < 500:
                    log_debug(f"OCR model changed to Gemini: updating scan interval from {current_value}ms to 500ms minimum")
                    self.scan_interval = 500
            
            # Refresh OCR preview if it's open to use the new OCR model
            if self.ocr_preview_window is not None:
                try:
                    if self.ocr_preview_window != None:
                        if hasattr(self, '_preview_refresh_timer'):
                            pass
                        self._preview_refresh_timer = QTimer.singleShot(200, self.refresh_ocr_preview)
                    else:
                        self.ocr_preview_window = None
                except Exception:
                    self.ocr_preview_window = None
                    
            log_debug(f"OCR model changed to: {self.ocr_model}")
        except Exception as e:
            log_debug(f"Error in OCR model change callback: {e}")

    def save_settings(self):
        if self._fully_initialized:
            return self.ui_interaction_handler.save_settings()
        log_debug("Attempted to save settings before full initialization.")
        return False

    def perform_marketing_screenshot(self):
        """Phase 1: Freeze overlays and yield to Qt event loop for DWM re-composition."""
        log_debug("Screenshot: Starting freeze sequence...")

        # 1. Pause the capture thread immediately
        self.is_photo_mode_active = True

        # 2. Freeze both overlays (block text updates + reveal to system capture)
        if self.target_overlay:
            self.target_overlay.freeze_for_screenshot()
        if self.source_overlay and self.source_overlay.isVisible():
            self.source_overlay.freeze_for_screenshot()

        # 3. Yield to the Qt event loop for ~150ms so DWM can re-composite
        #    the revealed windows into the screen buffer.
        #    NEVER use time.sleep() on the main thread — it blocks Qt's event processing.
        from PySide6.QtCore import QTimer
        QTimer.singleShot(150, self._execute_screenshot_capture)

    def _execute_screenshot_capture(self):
        """Phase 2: Capture the screen, save PNG, unfreeze, and notify user."""
        import mss
        import nuitka_compat
        from datetime import datetime
        from PIL import Image

        saved_filename = None
        try:
            # 4. Prepare output directory (next to the application executable)
            screenshots_dir = os.path.join(nuitka_compat.get_base_dir(), "Screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)

            # 5. Capture the PRIMARY monitor (index [1] in mss; [0] is all monitors combined)
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # Primary monitor only
                sct_img = sct.grab(monitor)

                # Convert to PIL using the same pattern as worker_threads.py (line 104)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

                saved_filename = f"GCT_screenshot_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
                filepath = os.path.join(screenshots_dir, saved_filename)
                img.save(filepath, "PNG")

                log_debug(f"Screenshot saved: {filepath}")

        except Exception as e:
            log_debug(f"Screenshot ERROR: {type(e).__name__} - {e}")

        finally:
            # 6. Unfreeze target overlay and replay any deferred text
            if self.target_overlay:
                self.target_overlay.unfreeze_after_screenshot()
                if self.target_overlay.pending_text_update is not None:
                    deferred = self.target_overlay.pending_text_update
                    self.target_overlay.pending_text_update = None
                    log_debug(f"Screenshot: Replaying deferred text update ({len(deferred)} chars)")
                    self.update_translation_text(deferred)

            # 7. Unfreeze source overlay (if it was frozen)
            if self.source_overlay and getattr(self.source_overlay, 'is_frozen', False):
                self.source_overlay.unfreeze_after_screenshot()

            # 8. Resume capture thread
            self.is_photo_mode_active = False
            log_debug("Screenshot: Sequence complete.")

            # 9. Show toast notification to user
            if saved_filename and hasattr(self, 'gui') and self.gui:
                self.gui.show_screenshot_toast(saved_filename)

    def apply_simple_overrides(self):
        """Override instance attributes with SIMPLE_CONFIG_SETTINGS values.
        
        Called on startup (if config_mode is 'Simple') and when switching
        from Advanced to Simple mode. Does NOT write to the ini file.
        """
        if self.config_mode != 'Simple':
            return
        
        log_debug("Applying Simple mode overrides to instance attributes")
        
        self.scan_interval = int(SIMPLE_CONFIG_SETTINGS['scan_interval'])
        self.clear_translation_timeout = int(SIMPLE_CONFIG_SETTINGS['clear_translation_timeout'])
        self.source_colour = SIMPLE_CONFIG_SETTINGS['source_area_colour']
        self.target_colour = SIMPLE_CONFIG_SETTINGS['target_area_colour']
        self.target_text_colour = SIMPLE_CONFIG_SETTINGS['target_text_colour']
        self.target_font_size = int(SIMPLE_CONFIG_SETTINGS['target_font_size'])
        self.target_font_type = SIMPLE_CONFIG_SETTINGS['target_font_type']
        self.translation_model = SIMPLE_CONFIG_SETTINGS['translation_model']
        self.ocr_model = SIMPLE_CONFIG_SETTINGS['ocr_model']
        self.gemini_translation_model = SIMPLE_CONFIG_SETTINGS['gemini_translation_model']
        self.gemini_ocr_model = SIMPLE_CONFIG_SETTINGS['gemini_ocr_model']
        self.keep_linebreaks = SIMPLE_CONFIG_SETTINGS['keep_linebreaks'] == 'True'
        self.auto_detect_enabled = SIMPLE_CONFIG_SETTINGS['auto_detect_enabled'] == 'True'
        self.target_on_source_enabled = SIMPLE_CONFIG_SETTINGS['target_on_source_enabled'] == 'True'
        self.capture_padding_enabled = SIMPLE_CONFIG_SETTINGS['capture_padding_enabled'] == 'True'
        self.capture_padding = int(SIMPLE_CONFIG_SETTINGS['capture_padding'])
        self.target_opacity = float(SIMPLE_CONFIG_SETTINGS['target_opacity'])
        self.target_text_opacity = float(SIMPLE_CONFIG_SETTINGS['target_text_opacity'])
        self.gemini_context_window = int(SIMPLE_CONFIG_SETTINGS['gemini_context_window'])
        self.deepl_cache_enabled = SIMPLE_CONFIG_SETTINGS['deepl_file_cache'] == 'True'
        self.gemini_cache_enabled = SIMPLE_CONFIG_SETTINGS['gemini_file_cache'] == 'True'
        self.debug_logging_enabled = SIMPLE_CONFIG_SETTINGS['debug_logging_enabled'] == 'True'
        self.gemini_api_log_enabled = SIMPLE_CONFIG_SETTINGS['gemini_api_log_enabled'] == 'True'
        self.custom_prompt_enabled = SIMPLE_CONFIG_SETTINGS['custom_prompt_enabled'] == 'True'
        self.custom_ocr_prompt_enabled = SIMPLE_CONFIG_SETTINGS['custom_ocr_prompt_enabled'] == 'True'
        
        # New: lock source language to auto
        self.gemini_source_lang = SIMPLE_CONFIG_SETTINGS['gemini_source_lang']
        self.deepl_source_lang = SIMPLE_CONFIG_SETTINGS['deepl_source_lang']
        
        # Update adaptive scan interval
        self.base_scan_interval = self.scan_interval
        self.current_scan_interval = self.scan_interval
        
        log_debug("Simple mode overrides applied successfully")

    def apply_pro_overrides(self):
        """Apply PRO overrides — open-source edition always locks PRO features.

        Keys locked:
        - source_area_colour, target_area_colour, target_text_colour
        - translation_model (forced to gemini_api, blocks DeepL)
        - auto_detect_enabled (Find Subtitles)
        - target_on_source_enabled (Target on Source)
        - capture_padding_enabled (Scan Wider)
        - custom_ocr_prompt_enabled (OCR Prompt)
        """
        log_debug("Applying PRO overrides (open-source edition) to instance attributes")

        self.source_colour = SIMPLE_CONFIG_SETTINGS['source_area_colour']
        self.target_colour = SIMPLE_CONFIG_SETTINGS['target_area_colour']
        self.target_text_colour = SIMPLE_CONFIG_SETTINGS['target_text_colour']
        self.translation_model = SIMPLE_CONFIG_SETTINGS['translation_model']
        self.auto_detect_enabled = SIMPLE_CONFIG_SETTINGS['auto_detect_enabled'] == 'True'
        self.target_on_source_enabled = SIMPLE_CONFIG_SETTINGS['target_on_source_enabled'] == 'True'
        self.capture_padding_enabled = SIMPLE_CONFIG_SETTINGS['capture_padding_enabled'] == 'True'
        self.custom_ocr_prompt_enabled = SIMPLE_CONFIG_SETTINGS['custom_ocr_prompt_enabled'] == 'True'

        log_debug("PRO overrides applied - PRO features locked to defaults")

    def reload_from_ini(self):
        """Reload user settings from ini file (restores 'Advanced' mode state)."""
        log_debug("Reloading user settings from INI (Advanced mode)")
        cfg = self.config['Settings']
        
        # In Advanced mode, we restore to Show visibility by default
        self.ui_visibility_mode = 'Show'
        
        self.scan_interval = int(cfg.get('scan_interval', '100'))
        self.clear_translation_timeout = int(float(cfg.get('clear_translation_timeout', '3')))
        self.source_colour = cfg.get('source_area_colour', '#FFFF99')
        self.target_colour = cfg.get('target_area_colour', '#162c43')
        self.target_text_colour = cfg.get('target_text_colour', '#FFFFFF')
        self.target_font_size = int(float(cfg.get('target_font_size', '18')))
        self.target_font_type = cfg.get('target_font_type', 'Arial')
        self.translation_model = cfg.get('translation_model', 'gemini_api')
        self.ocr_model = cfg.get('ocr_model', 'gemini')
        self.gemini_translation_model = cfg.get('gemini_translation_model', 'Gemini 2.5 Flash-Lite')
        self.gemini_ocr_model = cfg.get('gemini_ocr_model', 'Gemini 2.5 Flash-Lite')
        
        self.deepl_source_lang = cfg.get('deepl_source_lang', 'auto')
        self.deepl_target_lang = cfg.get('deepl_target_lang', 'EN-GB')
        self.gemini_source_lang = cfg.get('gemini_source_lang', 'auto')
        self.gemini_target_lang = cfg.get('gemini_target_lang', 'pl')
        
        self.keep_linebreaks = cfg.get('keep_linebreaks', 'False') == 'True'
        self.auto_detect_enabled = cfg.get('auto_detect_enabled', 'False') == 'True'
        self.target_on_source_enabled = cfg.get('target_on_source_enabled', 'False') == 'True'
        self.capture_padding_enabled = cfg.get('capture_padding_enabled', 'True') == 'True'
        self.capture_padding = int(cfg.get('capture_padding', '100'))
        self.target_opacity = float(cfg.get('target_opacity', '0.85'))
        self.target_text_opacity = float(cfg.get('target_text_opacity', '1.0'))
        self.gemini_context_window = int(cfg.get('gemini_context_window', '1'))
        self.deepl_cache_enabled = cfg.get('deepl_file_cache', 'True') == 'True'
        self.gemini_cache_enabled = cfg.get('gemini_file_cache', 'True') == 'True'
        self.debug_logging_enabled = cfg.get('debug_logging_enabled', 'False') == 'True'
        self.gemini_api_log_enabled = cfg.get('gemini_api_log_enabled', 'True') == 'True'
        self.custom_prompt_enabled = cfg.get('custom_prompt_enabled', 'True') == 'True'
        self.custom_ocr_prompt_enabled = cfg.get('custom_ocr_prompt_enabled', 'True') == 'True'
        
        # Update adaptive scan interval
        self.base_scan_interval = self.scan_interval
        self.current_scan_interval = self.scan_interval
        
        self.apply_pro_overrides()
        log_debug("Advanced settings reloaded from ini")



    def update_translation_text(self, text_to_display):
        self.display_manager.update_translation_text(text_to_display)

    def update_debug_display(self, original_img_pil, processed_img_cv, ocr_text_content):
        self.display_manager.update_debug_display(original_img_pil, processed_img_cv, ocr_text_content)

    def _widget_exists_safely(self, widget):
        """Safely check if a PySide widget exists and is accessible."""
        if not widget:
            return False
        try:
            # Check if the reference is valid and the widget has not been destroyed.
            return widget is not None
        except Exception:
            return False

    def convert_to_webp_for_api(self, pil_image):
        """Convert PIL image to optimized WebP bytes for API calls.
        
        Performance optimizations (v4):
        - Downscales images wider than 960px before encoding (Gemini uses media_resolution:LOW = 280 tokens, 
          so high-res input is wasted CPU and bandwidth)
        - Uses lossy compression (quality=65) instead of lossless for ~10x faster encoding
        - Preserves aspect ratio during downscaling
        """
        try:
            # Optimize image for OCR if needed
            if pil_image.mode in ('RGBA', 'LA'):
                rgb_img = Image.new('RGB', pil_image.size, (255, 255, 255))
                if pil_image.mode == 'RGBA':
                    rgb_img.paste(pil_image, mask=pil_image.split()[-1])
                else:
                    rgb_img.paste(pil_image)
                pil_image = rgb_img
            
            # Downscale large images to max 960px width (preserving aspect ratio)
            # This drastically reduces WebP encoding time and upload size
            # while maintaining sufficient quality for OCR (Gemini at LOW = 280 tokens)
            MAX_WIDTH_FOR_API = 1920
            original_width, original_height = pil_image.size
            if original_width > MAX_WIDTH_FOR_API:
                scale_factor = MAX_WIDTH_FOR_API / original_width
                new_height = int(original_height * scale_factor)
                pil_image = pil_image.resize((MAX_WIDTH_FOR_API, new_height), Image.LANCZOS)
                log_debug(f"Downscaled image for API: {original_width}x{original_height} -> {MAX_WIDTH_FOR_API}x{new_height}")
            
            # Create memory buffer
            buffer = io.BytesIO()
            
            # Save as WebP with lossy compression for fast encoding and small file size
            # quality=65 is optimal for OCR: readable text with minimal encoding overhead
            pil_image.save(
                buffer, 
                format='WebP', 
                quality=65,
                method=0,
            )
            
            # Get bytes
            webp_bytes = buffer.getvalue()
            
            log_debug(f"Converted PIL image to WebP for API: {len(webp_bytes)} bytes")
            return webp_bytes
            
        except Exception as e:
            log_debug(f"Error converting image to WebP for API: {e}")
            return None


    def _pre_initialize_gemini_model(self):
        """Pre-configure Gemini API at startup to avoid thread initialization delays."""
        try:
            if not self.GEMINI_API_AVAILABLE:
                return
            
            gemini_api_key = self.gemini_api_key.strip()
            if not gemini_api_key:
                return
            
            # The client and key configuration is now handled by individual providers
            # during initialization.
            log_debug("Gemini API configured (per-provider)")
                    
        except Exception as e:
            log_debug(f"Error in Gemini model pre-configuration: {e}")
    
    # Gemini OCR Batch Processing Methods (Phase 1)
    def get_ocr_model_setting(self):
        """Get the current OCR model setting."""
        return self.ocr_model
    
    def update_adaptive_scan_interval(self):
        """Adjust scan interval based on current OCR API load to prevent bottlenecks."""
        now = time.monotonic()
        
        # Check load every 2 seconds
        if now - self.load_check_timer < 2.0:
            return
            
        self.load_check_timer = now
        
        # Measure current OCR load
        active_ocr_count = len(self.active_ocr_calls)
        max_ocr_calls = self.max_concurrent_ocr_calls
        
        # DEBUG: Always log the current state
        log_debug(f"ADAPTIVE: Checking OCR load - Active calls: {active_ocr_count}/{max_ocr_calls}, Current interval: {self.current_scan_interval}ms, Overload detected: {self.overload_detected}")
        
        # Get user's preferred base interval
        base_interval = self.scan_interval  # User's setting in milliseconds
        
        # Update base_scan_interval to track user changes
        self.base_scan_interval = base_interval
        
        # Apply the user's specific requirements:
        # If active OCR API calls > 5, increase scan interval to 150% of current value
        # If active OCR API calls fall below 5, restore original scan interval
        if active_ocr_count > 5:
            if not self.overload_detected:
                # First detection of overload
                self.current_scan_interval = int(base_interval * 1.5)  # 150%
                self.overload_detected = True
                log_debug(f"ADAPTIVE: OCR overload detected ({active_ocr_count} active calls), increasing scan interval to {self.current_scan_interval}ms")
            else:
                # Already in overload state, maintain increased interval
                log_debug(f"ADAPTIVE: OCR still overloaded ({active_ocr_count} active calls), maintaining scan interval at {self.current_scan_interval}ms")
            # Stay at increased interval while overloaded
            
        elif active_ocr_count < 5:
            if self.overload_detected:
                # Load has decreased, return to normal
                self.current_scan_interval = base_interval
                self.overload_detected = False
                log_debug(f"ADAPTIVE: OCR load normalized ({active_ocr_count} active calls), returning scan interval to {self.current_scan_interval}ms")
            else:
                # Normal state, no change needed
                log_debug(f"ADAPTIVE: OCR load normal ({active_ocr_count} active calls), scan interval remains at {self.current_scan_interval}ms")
        else:
            # At exactly 5 calls, maintain current state
            log_debug(f"ADAPTIVE: OCR load moderate ({active_ocr_count} active calls), scan interval unchanged at {self.current_scan_interval}ms")
    
    def handle_empty_ocr_result(self):
        """Handle <EMPTY> OCR result and manage clear translation timeout."""
        current_time = time.monotonic()
        
        # Only start timeout if we have a timeout value configured
        if self.clear_translation_timeout <= 0:
            return  # Timeout disabled, do nothing
        
        if self.clear_timeout_timer_start is None:
            # First EMPTY result - start timer
            self.clear_timeout_timer_start = current_time
            log_debug("Clear timeout timer started for <EMPTY> OCR result")
        else:
            # Check if timeout period exceeded
            elapsed = current_time - self.clear_timeout_timer_start
            timeout_seconds = self.clear_translation_timeout
            
            if elapsed >= timeout_seconds:
                # Clear the translation display
                self.update_translation_text("")
                self.reset_clear_timeout()
                log_debug(f"Translation cleared after {elapsed:.1f}s timeout")
    
    def handle_successive_identical_subtitle(self, reason):
        """Handle identical subtitles that are the SAME as the immediately previous one."""
        # 1. Do NOT update caches (LRU, file cache) - no new content
        # 2. Do NOT update context window - successive identical subtitle
        # 3. Keep displaying last translation (no API call needed)
        # 4. Reset clear timeout (text is still present)
        
        self.reset_clear_timeout()  # Text still present
        # Display remains unchanged (last translation stays)
        # self.last_processed_subtitle stays the same (no change)
        log_debug(f"Successive identical subtitle detected ({reason}), maintaining current translation")
        # No context window update - subtitle hasn't changed
    
    def reset_clear_timeout(self):
        """Reset clear translation timeout timer."""
        self.clear_timeout_timer_start = None
        log_debug("Clear timeout timer reset - text detected")
    
    def _get_physical_screen_resolution(self):
        """Returns the physical screen resolution (width, height) in pixels.
        Uses Windows API for accuracy, falls back to PySide6 primary screen.
        """
        try:
            if sys.platform == "win32":
                import ctypes
                user32 = ctypes.windll.user32
                hdc = user32.GetDC(0)
                sw = ctypes.windll.gdi32.GetDeviceCaps(hdc, 118)  # HORZRES
                sh = ctypes.windll.gdi32.GetDeviceCaps(hdc, 117)  # VERTRES
                user32.ReleaseDC(0, hdc)
                if sw > 0 and sh > 0:
                    return sw, sh
        except Exception:
            pass
        # Fallback to PySide6 (may return logical pixels on some configs)
        try:
            return QApplication.primaryScreen().geometry().width(), QApplication.primaryScreen().geometry().height()
        except Exception:
            return 2560, 1440  # Last resort fallback

    def handle_auto_detection_result(self, ocr_result):
        """No-op in open-source edition (Find Subtitles is PRO)."""
        pass

    def _check_discovery_timer(self):
        """No-op in open-source edition."""
        pass

    def apply_discovery_to_target_overlay(self):
        """No-op in open-source edition."""
        pass

    def update_auto_detect_btn_text(self):
        """Syncs the Auto Detection checkbox state across the UI."""
        if hasattr(self, 'gui') and self.gui:
            try:
                # Use thread-safe way or direct access if in main thread
                if hasattr(self.gui, 'auto_detect_check') and self.gui.auto_detect_check:
                    # Block signals to prevent recursion
                    self.gui.auto_detect_check.blockSignals(True)
                    self.gui.auto_detect_check.setChecked(self.auto_detect_enabled)
                    self.gui.auto_detect_check.blockSignals(False)
                    
                    # Update the accompanying text label (ON/OFF)
                    if hasattr(self.gui, 'update_auto_detect_label'):
                        self.gui.update_auto_detect_label()
            except Exception as e:
                log_debug(f"Error updating auto-detect checkbox in GUI: {e}")

    def update_target_on_source_btn_text(self):
        """Syncs the Target on Source checkbox state across the UI."""
        if hasattr(self, 'gui') and self.gui:
            try:
                if hasattr(self.gui, 'target_on_source_check') and self.gui.target_on_source_check:
                    # Block signals to prevent recursion
                    self.gui.target_on_source_check.blockSignals(True)
                    self.gui.target_on_source_check.setChecked(self.target_on_source_enabled)
                    self.gui.target_on_source_check.blockSignals(False)
                    
                    # Update label text (ON/OFF)
                    if hasattr(self.gui, 'update_target_on_source_label'):
                        self.gui.update_target_on_source_label()
            except Exception as e:
                log_debug(f"Error updating target-on-source checkbox in GUI: {e}")

    def finish_discovery_phase(self):
        """No-op in open-source edition (Find Subtitles is PRO)."""
        pass

    def _align_target_to_source(self):
        """No-op in open-source edition (Target on Source is PRO)."""
        pass

    def handle_source_manual_move(self):
        """Called from main thread context — saves source overlay position to .ini."""
        if self.source_overlay:
            # 1. Normalized coordinates for config saving
            src_geom = self.source_overlay.get_geometry()
            if src_geom and len(src_geom) == 4:
                self.source_area_x1, self.source_area_y1, self.source_area_x2, self.source_area_y2 = src_geom
                self.source_area = src_geom
                
                # 2. Physical pixels for internal AI state synchronization
                # (Prevents North-West jump when Auto-Detection is ON)
                phys_area = self.source_overlay.get_physical_pixels()
                self.detected_source_area_x1, self.detected_source_area_y1, \
                self.detected_source_area_x2, self.detected_source_area_y2 = phys_area
                    
        self.save_settings()
        log_debug(f"MANUAL: Source overlay manually moved/resized. Saved to .ini: {getattr(self, 'source_area', 'None')}")

    def _start_pyside_move_polling(self):
        """Starts a polling loop that checks PySide overlay's _user_moved_flag.
        This is a safe way to bridge PySide native events to the backend,
        ensuring thread safety for file operations."""
        if getattr(self, '_pyside_polling_active', False):
            return  # Already polling
        self._pyside_polling_active = True
        self._poll_pyside_overlay_move()

    def _poll_pyside_overlay_move(self):
        """Polls PySide target overlay for the manual move flag every 300ms."""
        try:
            if (self.target_overlay and
                hasattr(self.target_overlay, '_user_moved_flag') and
                self.target_overlay._user_moved_flag):
                self.target_overlay._user_moved_flag = False
                self._process_target_manual_move()
                
            if (self.source_overlay and
                hasattr(self.source_overlay, '_user_moved_flag') and
                self.source_overlay._user_moved_flag):
                self.source_overlay._user_moved_flag = False
                self._process_source_manual_move()
        except Exception:
            pass
        # Continue polling as long as the app is alive
        if hasattr(self, '_fully_initialized') and self._fully_initialized:
            try:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(300, self._poll_pyside_overlay_move)
            except Exception:
                self._pyside_polling_active = False

    def _process_source_manual_move(self):
        """Processes a detected manual move of the source overlay (runs in main thread context)."""
        if self.source_overlay:
            # 1. Normalized coordinates for config saving
            src_geom = self.source_overlay.get_geometry()
            if src_geom and len(src_geom) == 4:
                self.source_area_x1, self.source_area_y1, self.source_area_x2, self.source_area_y2 = src_geom
                self.source_area = src_geom
                
                # 2. Physical pixels for internal AI state synchronization 
                # (Prevents North-West jump when Auto-Detection is ON)
                phys_area = self.source_overlay.get_physical_pixels()
                self.detected_source_area_x1, self.detected_source_area_y1, \
                self.detected_source_area_x2, self.detected_source_area_y2 = phys_area
                    
        self.save_settings()
        log_debug(f"MANUAL: Source overlay manually moved/resized. Saved to .ini: {getattr(self, 'source_area', 'None')}")

    def _process_target_manual_move(self):
        """Processes a detected manual move of the target overlay (runs in main thread context)."""
        if self.target_overlay:
            tgt_geom = self.target_overlay.get_geometry()
            if tgt_geom and len(tgt_geom) == 4:
                self.target_area_x1, self.target_area_y1, self.target_area_x2, self.target_area_y2 = tgt_geom
                self.target_area = tgt_geom
        
        # Target on Source disabled in open-source edition
        pass
                
        self.save_settings()
        log_debug(f"MANUAL: Target overlay manually moved/resized. Saved to .ini: {getattr(self, 'target_area', 'None')}")

    def show_discovery_notification(self):
        """No-op in open-source edition."""
        pass

    def _parse_discovery_coordinates(self, result_str):
        """No-op in open-source edition."""
        return None

    def initialize_async_translation_infrastructure(self):
        """Initialize async translation infrastructure if not already present."""
        if not hasattr(self, 'translation_sequence_counter'):
            self.translation_sequence_counter = 0
            log_debug("Initialized translation_sequence_counter")
        
        if not hasattr(self, 'last_displayed_translation_sequence'):
            self.last_displayed_translation_sequence = 0
            log_debug("Initialized last_displayed_translation_sequence")
        
        if not hasattr(self, 'active_translation_calls'):
            self.active_translation_calls = set()
            log_debug("Initialized active_translation_calls")
        
        if not hasattr(self, 'max_concurrent_translation_calls'):
            self.max_concurrent_translation_calls = 6
            log_debug("Initialized max_concurrent_translation_calls")
    
    def check_clear_timeout(self):
        """Check if clear timeout should be triggered and return True if timeout exceeded."""
        if self.clear_timeout_timer_start is None:
            return False
            
        if self.clear_translation_timeout <= 0:
            return False  # Timeout disabled
            
        current_time = time.monotonic()
        elapsed = current_time - self.clear_timeout_timer_start
        timeout_seconds = self.clear_translation_timeout
        
        return elapsed >= timeout_seconds

    def translate_text(self, text_content):
        return self.translation_handler.translate_text(text_content)

    def is_placeholder_text(self, text_content):
        return self.translation_handler.is_placeholder_text(text_content)

    def calculate_text_similarity(self, text1, text2):
        return self.translation_handler.calculate_text_similarity(text1, text2)



    def choose_color_for_settings(self, color_type):
        self.ui_interaction_handler.choose_color_for_settings(color_type)

    def update_target_font_size(self):
        self.ui_interaction_handler.update_target_font_size()

    def update_target_font_type(self):
        self.ui_interaction_handler.update_target_font_type()

    def update_target_opacity(self):
        self.ui_interaction_handler.update_target_opacity()

    def update_target_text_opacity(self):
        self.ui_interaction_handler.update_target_text_opacity()

    def refresh_debug_log(self):
        self.ui_interaction_handler.refresh_debug_log()

    def save_debug_images(self):
        self.ui_interaction_handler.save_debug_images()

    def toggle_api_key_visibility(self, api_type):
        self.ui_interaction_handler.toggle_api_key_visibility(api_type)

    def update_translation_model_ui(self): 
        self.ui_interaction_handler.update_translation_model_ui()

    def on_translation_model_selection_changed(self, event=None, initial_setup=False):
        # Handle session management for translation method changes
        if (hasattr(self, 'translation_handler') and self.is_running and not initial_setup):
            current_model = self.translation_model
            
            # End translation session if switching away from Gemini
            if current_model != 'gemini_api':
                self.translation_handler.request_end_translation_session()
            
            # Start translation session if switching to Gemini
            if current_model == 'gemini_api':
                self.translation_handler.request_start_translation_session()
                self.translation_handler.start_translation_session()
            

        
        self.ui_interaction_handler.on_translation_model_selection_changed(event, initial_setup)
        if not initial_setup and self._fully_initialized: 
            self.save_settings()

    def clear_debug_log(self):
        self.ui_interaction_handler.clear_debug_log()

    def reset_gemini_api_log(self):
        """Reset/clear the Gemini API call log file."""
        try:
            if hasattr(self.translation_handler, 'gemini_log_file'):
                log_file_path = self.translation_handler.gemini_log_file
                
                # Clear the file by truncating it
                if os.path.exists(log_file_path):
                    with open(log_file_path, 'w', encoding='utf-8') as f:
                        f.write('')  # Clear the file
                    log_debug(f"Gemini API log file cleared: {log_file_path}")
                    
                    # Reinitialize the log with header
                    if hasattr(self.translation_handler, '_initialize_gemini_log'):
                        self.translation_handler._initialize_gemini_log()
                    
                    # Update the GUI fields
                    self.update_gemini_stats()
                    
                    messagebox.showinfo(
                        self.ui_lang.get_label("gemini_reset_success_title", "Success"), 
                        self.ui_lang.get_label("gemini_reset_success_msg", "Gemini API log has been reset.")
                    )
                else:
                    log_debug(f"Gemini API log file does not exist: {log_file_path}")
                    messagebox.showwarning(
                        self.ui_lang.get_label("gemini_reset_warning_title", "Warning"), 
                        self.ui_lang.get_label("gemini_reset_warning_msg", "Gemini API log file does not exist.")
                    )
            else:
                log_debug("Gemini log file path not available")
                messagebox.showerror(
                    self.ui_lang.get_label("gemini_reset_error_title", "Error"), 
                    self.ui_lang.get_label("gemini_reset_error_msg", "Could not access Gemini log file.")
                )
        except Exception as e:
            log_debug(f"Error resetting Gemini API log: {e}")
            messagebox.showerror(
                self.ui_lang.get_label("gemini_reset_error_title", "Error"), 
                f"{self.ui_lang.get_label('gemini_reset_error_failed', 'Failed to reset Gemini API log:')} {str(e)}"
            )



    def format_currency_for_display(self, amount, unit_suffix=""):
        """Format currency amount according to current UI language."""
        try:
            if self.ui_lang.current_lang == 'pol':
                # Polish format: "0,04941340 USD/min" 
                amount_str = f"{amount:.8f}"
                amount_str = amount_str.replace('.', ',')  # Replace decimal point with comma
                
                # Add thousand separators (space) for large numbers
                parts = amount_str.split(',')
                integer_part = parts[0]
                decimal_part = parts[1] if len(parts) > 1 else ""
                
                # Add space thousand separators to integer part
                if len(integer_part) > 3:
                    formatted_integer = ""
                    for i, digit in enumerate(reversed(integer_part)):
                        if i > 0 and i % 3 == 0:
                            formatted_integer = " " + formatted_integer
                        formatted_integer = digit + formatted_integer
                    integer_part = formatted_integer
                
                if decimal_part:
                    amount_str = f"{integer_part},{decimal_part}"
                else:
                    amount_str = integer_part
                
                # Translate unit suffixes for Polish
                if unit_suffix == "/min":
                    unit_suffix = " USD/min"
                elif unit_suffix == "/hr":
                    unit_suffix = " USD/godz."
                elif unit_suffix == "":
                    unit_suffix = " USD"
                
                return f"{amount_str}{unit_suffix}"
            else:
                # English format: "$0.04941340/min"
                prefix = "$" 
                # Add thousand separators to integer part for English too
                int_part = int(amount)
                decimal_part = f"{amount - int_part:.8f}"[2:] # Get 8 decimal places
                return f"{prefix}{int_part:,}.{decimal_part}{unit_suffix}"

        except Exception as e:
            log_debug(f"Error formatting currency: {e}")
            return f"${amount:.8f}{unit_suffix}"  # Fallback to English format

    def format_cost_for_display(self, cost_value):
        """Format cost value according to current UI language (legacy method)."""
        return self.format_currency_for_display(cost_value, " USD" if self.ui_lang.current_lang == 'pol' else "")

    def format_number_with_separators(self, number):
        """Format integer numbers with thousand separators according to current UI language."""
        try:
            # Convert to integer to avoid decimal formatting issues
            num = int(number)
            
            if self.ui_lang.current_lang == 'pol':
                # Polish format: use space as thousand separator
                num_str = str(num)
                if len(num_str) > 3:
                    formatted = ""
                    for i, digit in enumerate(reversed(num_str)):
                        if i > 0 and i % 3 == 0:
                            formatted = " " + formatted
                        formatted = digit + formatted
                    return formatted
                else:
                    return num_str
            else:
                # English format: use comma as thousand separator
                return f"{num:,}"
        except Exception as e:
            log_debug(f"Error formatting number with separators: {e}")
            return str(number)  # Fallback to string representation

    def update_gemini_stats(self):
        """Update the Gemini statistics fields by reading the log file."""
        try:

            # Check if all required components are available
            if not hasattr(self.translation_handler, '_get_cumulative_totals'):
                log_debug("TranslationHandler._get_cumulative_totals method not available")
                return
                
            if not (hasattr(self, 'gemini_total_words') and 
                    hasattr(self, 'gemini_total_cost') and
                    self.gemini_total_words_var is not None and 
                    self.gemini_total_cost_var is not None):
                log_debug("Gemini stats variables not initialized yet")
                return
                
            total_words, total_input, total_output = self.translation_handler._get_cumulative_totals()
            
            # Read the already-calculated cumulative cost from the log file
            # (costs are calculated per-operation using the correct model costs)
            total_cost = self._get_cumulative_cost_from_log()
            
            # Update GUI fields
            self.gemini_total_words = self.format_number_with_separators(total_words)
            self.gemini_total_cost = self.format_cost_for_display(total_cost)
            
            log_debug(f"Updated Gemini stats: {total_words} words, ${total_cost:.8f}")
        except Exception as e:
            log_debug(f"Error updating Gemini stats: {e}")
            # Set default values if there's an error
            if hasattr(self, 'gemini_total_words') and self.gemini_total_words_var is not None:
                self.gemini_total_words = self.format_number_with_separators(0)
            if hasattr(self, 'gemini_total_cost') and self.gemini_total_cost_var is not None:
                self.gemini_total_cost = self.format_cost_for_display(0.0)

    def _get_cumulative_cost_from_log(self):
        """Read the cumulative cost from the Gemini API log file."""
        try:

            # Get the log file path
            base_dir = nuitka_compat.get_base_dir()
            
            gemini_log_file = os.path.join(base_dir, "Gemini_API_call_logs.txt")
            
            if not os.path.exists(gemini_log_file):
                log_debug(f"Gemini log file does not exist: {gemini_log_file}")
                return 0.0
            
            # Read the most recent cumulative cost from the log
            cumulative_cost = 0.0
            cumulative_cost_regex = re.compile(r"^\s*-\s*Cumulative Log Cost:\s*\$([0-9]*\.?[0-9]+)")
            
            with open(gemini_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    cost_match = cumulative_cost_regex.match(line)
                    if cost_match:
                        cumulative_cost = float(cost_match.group(1))
            
            return cumulative_cost
        except Exception as e:
            log_debug(f"Error reading cumulative cost from log: {e}")
            return 0.0

    def _delayed_gemini_stats_update(self):
        """Delayed stats update to ensure GUI is fully ready."""
        try:
            self.update_gemini_stats()
        except Exception as e:
            log_debug(f"Error in delayed Gemini stats update: {e}")

    def update_deepl_usage(self):
        """Update the DeepL usage display by calling the usage API."""
        try:
            if not hasattr(self, 'deepl_usage'): self.deepl_usage = ""
            
            # Only check usage if DeepL is available and we have translation handler
            if not hasattr(self, 'translation_handler') or not hasattr(self.translation_handler, 'get_deepl_usage'):
                log_debug("DeepL usage checking not available")
                self.deepl_usage = "N/A"
            else:
                usage_data = self.translation_handler.get_deepl_usage()
                
                if usage_data and isinstance(usage_data, dict):
                    character_count = usage_data.get('character_count', 0)
                    character_limit = usage_data.get('character_limit', 0)
                    
                    # Calculate usage percentage
                    if character_limit > 0:
                        usage_percentage = (character_count / character_limit) * 100
                    else:
                        usage_percentage = 0
                    
                    # Format according to UI language
                    if getattr(self.ui_lang, 'current_lang', 'eng') == 'pol':
                        used_formatted = f"{character_count:,}".replace(',', ' ')
                        limit_formatted = f"{character_limit:,}".replace(',', ' ')
                        percentage_formatted = f"{usage_percentage:.1f}".replace('.', ',')
                        usage_text = f"{used_formatted} / {limit_formatted} znaków ({percentage_formatted}%)"
                    else:
                        usage_text = f"{character_count:,} / {character_limit:,} characters ({usage_percentage:.1f}%)"
                    
                    self.deepl_usage = usage_text
                    log_debug(f"Updated DeepL usage: {character_count}/{character_limit} characters ({usage_percentage:.1f}%)")
                else:
                    # Set fallback message if API call failed
                    self.deepl_usage = self.ui_lang.get_label("deepl_usage_unavailable", "Unable to retrieve usage data")
                    log_debug("DeepL usage API call failed or returned invalid data")
            
            if hasattr(self, 'gui') and self.gui and hasattr(self.gui, 'gui_deepl_usage_lbl'):
                self.gui.gui_deepl_usage_lbl.setText(self.deepl_usage)
        except Exception as e:
            log_debug(f"Error updating DeepL usage: {e}")
            self.deepl_usage = "Error"
            if hasattr(self, 'gui') and self.gui and hasattr(self.gui, 'gui_deepl_usage_lbl'):
                self.gui.gui_deepl_usage_lbl.setText("Error")


    def _delayed_deepl_usage_update(self):
        """Delayed DeepL usage update to ensure GUI is fully ready."""
        try:
            self.update_deepl_usage()
        except Exception as e:
            log_debug(f"Error in delayed DeepL usage update: {e}")

    def refresh_api_statistics(self):
        """Refresh API stats and set GUI strings."""
        try:
            if not hasattr(self, 'statistics_handler'): return
            
            # Update DeepL usage from API
            self.update_deepl_usage()
            
            # Trigger statistics refresh from handler
            stats = self.statistics_handler.get_statistics()
            
            # Compatibility with any remaining legacy code
            lng = self.ui_lang
            g_ocr = stats['gemini_ocr']
            self.gui_gemini_ocr_stats = f"{lng.get_label('stats_total_calls', 'Total Calls')}: {g_ocr['total_calls']} | {lng.get_label('stats_cost', 'Cost')}: {self.format_currency_for_display(g_ocr['total_cost'])}"
            
            g_trans = stats['gemini_translation']
            self.gui_gemini_trans_stats = f"{lng.get_label('stats_words', 'Words')}: {g_trans['total_words']} | {lng.get_label('stats_cost', 'Cost')}: {self.format_currency_for_display(g_trans['total_cost'])}"
            
            self.gui_deepl_stats = f"Monitor DeepL: {getattr(self, 'deepl_usage', 'N/A')}"
            
        except Exception as e:
            log_debug(f"Error refreshing API statistics: {e}")


    def copy_statistics_to_clipboard(self):
        """Generate a full detailed report and copy it to the system clipboard."""
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            cb = QApplication.clipboard()
            
            # Use the detailed report generator from StatisticsHandler
            deepl_usage = getattr(self, 'deepl_usage', 'N/A')
            report = self.statistics_handler._generate_text_report(self.ui_lang, deepl_usage)
            cb.setText(report)
            
            # Show confirmation localized
            QMessageBox.information(None, 
                                  self.ui_lang.get_label("stats_copied_title", "Copied"), 
                                  self.ui_lang.get_label("stats_copied_msg", "Statistics copied to clipboard."))
        except Exception as e:
            log_debug(f"Error copying statistics to clipboard: {e}")


    def export_statistics_csv(self):
        """Export API usage statistics to CSV file using Qt dialogs."""
        try:
            from PySide6.QtWidgets import QFileDialog, QMessageBox
            
            # Get the current DeepL usage value
            deepl_usage = getattr(self, 'deepl_usage', None)
            
            # Ask user for file location using QFileDialog
            title = self.ui_lang.get_label("export_csv_dialog_title", "Export Statistics to CSV")
            filter_str = f"{self.ui_lang.get_label('file_type_csv', 'CSV files')} (*.csv);;{self.ui_lang.get_label('file_type_all', 'All files')} (*.*)"
            
            file_path, _ = QFileDialog.getSaveFileName(None, title, "", filter_str)
            
            if file_path:
                # Ensure .csv extension
                if not file_path.lower().endswith('.csv'):
                    file_path += '.csv'
                    
                success = self.statistics_handler.export_statistics_csv(file_path, self.ui_lang, deepl_usage)
                if success:
                    QMessageBox.information(None, 
                                          self.ui_lang.get_label("export_success_title", "Export Successful"), 
                                          f"{self.ui_lang.get_label('export_success_msg', 'Statistics exported to:')}\n{file_path}")
                else:
                    QMessageBox.critical(None, 
                                       self.ui_lang.get_label("export_failed_title", "Export Failed"), 
                                       self.ui_lang.get_label("export_csv_failed_msg", "Failed to export statistics to CSV."))
            
        except Exception as e:
            log_debug(f"Error exporting statistics to CSV: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, self.ui_lang.get_label("export_error_title", "Export Error"), 
                               f"{self.ui_lang.get_label('export_error_msg', 'Error exporting statistics:')}\n{str(e)}")

    
    def export_statistics_text(self):
        """Export API usage statistics to text file using Qt dialogs."""
        try:
            from PySide6.QtWidgets import QFileDialog, QMessageBox
            
            # Get the current DeepL usage value
            deepl_usage = getattr(self, 'deepl_usage', None)
            
            # Ask user for file location using QFileDialog
            title = self.ui_lang.get_label("export_text_dialog_title", "Export Statistics to Text")
            filter_str = f"{self.ui_lang.get_label('file_type_text', 'Text files')} (*.txt);;{self.ui_lang.get_label('file_type_all', 'All files')} (*.*)"
            
            file_path, _ = QFileDialog.getSaveFileName(None, title, "", filter_str)
            
            if file_path:
                # Ensure .txt extension
                if not file_path.lower().endswith('.txt'):
                    file_path += '.txt'
                    
                success = self.statistics_handler.export_statistics_text(file_path, self.ui_lang, deepl_usage)
                if success:
                    QMessageBox.information(None, 
                                          self.ui_lang.get_label("export_success_title", "Export Successful"), 
                                          f"{self.ui_lang.get_label('export_success_msg', 'Statistics exported to:')}\n{file_path}")
                else:
                    QMessageBox.critical(None, 
                                       self.ui_lang.get_label("export_failed_title", "Export Failed"), 
                                       self.ui_lang.get_label("export_text_failed_msg", "Failed to export statistics to text."))
            
        except Exception as e:
            log_debug(f"Error exporting statistics to text: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, self.ui_lang.get_label("export_error_title", "Export Error"), 
                               f"{self.ui_lang.get_label('export_error_msg', 'Error exporting statistics:')}\n{str(e)}")

    
    # =============================================================================
    # AUTO-UPDATE SYSTEM (removed in open-source edition)
    # =============================================================================
    
    def check_for_updates(self, auto_check=False):
        """Open GitHub releases page (open-source edition)."""
        if not auto_check:
            import webbrowser
            webbrowser.open("https://github.com/tomkam1702/OCR-Translator/releases")


    def toggle_debug_logging(self):
        """Toggle debug logging on/off and update button text."""
        current_state = self.debug_logging_enabled
        new_state = not current_state
        
        # Log state change before changing the state
        if current_state:
            log_debug("Debug logging disabled by user")
        
        # Update the state
        self.debug_logging_enabled = new_state
        set_debug_logging_enabled(new_state)
        
        # Log state change after enabling (if we're enabling)
        if new_state:
            log_debug("Debug logging enabled by user")
        
        # Save settings
        if self._fully_initialized:
            self.save_settings()

    def load_initial_overlay_areas(self):
        load_areas_from_config_om(self)

    def create_source_overlay(self):
        create_source_overlay_om(self)

    def create_target_overlay(self):
        create_target_overlay_om(self)  # System recreation, preserve position

    def toggle_source_visibility(self):
        toggle_source_visibility_om(self)
        self.save_settings() 

    def toggle_target_visibility(self):
        toggle_target_visibility_om(self)
        self.save_settings()

    def clear_file_caches(self):
        self.cache_manager.clear_file_caches()

    def clear_cache(self):
        """Clear unified translation cache."""
        try:
            log_debug("Clearing unified translation cache...")
            
            # Clear unified cache (thread-safe, no need to pause translation)
            if hasattr(self, 'translation_handler') and self.translation_handler:
                self.translation_handler.clear_cache()
            
            # Clear in-memory file cache representations (Level 2 persistence remains)
            if hasattr(self, 'deepl_cache_dict'): self.deepl_cache_dict.clear()
            log_debug("Cleared in-memory representations of file caches.")

            # Clear queues
            if hasattr(self, 'ocr_queue'): self._clear_queue(self.ocr_queue)
            if hasattr(self, 'translation_queue'): self._clear_queue(self.translation_queue)
            log_debug("Cleared OCR and translation queues.")

            # Reset text processing state
            self.text_stability_counter = 0
            self.previous_text = ""
            if hasattr(self, 'translation_cache'): self.translation_cache.clear()
            log_debug("Unified translation cache and related states cleared successfully.")
                    
        except Exception as e_cc:
            log_debug(f"Error clearing unified cache: {e_cc}")

    def _clear_queue(self, q_to_clear):
        items_cleared_count = 0
        while not q_to_clear.empty():
            try:
                q_to_clear.get_nowait()
                items_cleared_count += 1
            except queue.Empty:
                break 
            except Exception as e_cq:
                log_debug(f"Error clearing queue {type(q_to_clear).__name__}: {e_cq}")
                break 
        if items_cleared_count > 0:
            log_debug(f"Cleared {items_cleared_count} items from {type(q_to_clear).__name__}.")

    def _reset_gemini_batch_state(self):
        """Reset Gemini OCR batch management state for clean start."""
        self.batch_sequence_counter = 0
        self.last_displayed_batch_sequence = 0
        self.active_ocr_calls = set()
        self.last_processed_subtitle = None
        self.clear_timeout_timer_start = None
        log_debug("Gemini OCR batch state reset")

    def _graceful_shutdown_poll(self):
        """
        Non-blocking poll to check if all async API calls have finished.
        This allows the Qt event loop to process callbacks that decrement pending call counters.
        """
        # Calculate pending calls from all providers
        pending_ocr = 0
        if hasattr(self.translation_handler, 'ocr_providers'):
            for provider in self.translation_handler.ocr_providers.values():
                pending_ocr += provider._pending_ocr_calls
        
        pending_translation = 0
        if hasattr(self.translation_handler, 'providers'):
            for provider in self.translation_handler.providers.values():
                pending_translation += provider._pending_translation_calls

        # Check if timeout is reached or all calls are done
        elapsed = time.monotonic() - self._shutdown_start_time
        if (pending_ocr == 0 and pending_translation == 0) or elapsed > 20.0:
            if elapsed > 20.0:
                log_debug(f"Warning: Shutdown timeout of 20.0s reached. Some API calls may not have completed.")
            else:
                log_debug("All pending API calls have completed.")
            
            log_debug(f"Graceful shutdown for thread pools completed in {elapsed:.2f}s.")
            self._finalize_shutdown() # Proceed to the final steps
            return

        # If not done, poll again shortly
        log_debug(f"Waiting for pending API calls to complete... OCR: {pending_ocr}, Translation: {pending_translation}")
        QTimer.singleShot(100, self._graceful_shutdown_poll)

    def _finalize_shutdown(self):
        """Contains the final steps of the shutdown process after graceful polling."""
        # End the sessions HERE, after all pending calls are confirmed to be finished.
        if hasattr(self, 'translation_handler'):
            self.translation_handler.request_end_ocr_session()
            self.translation_handler.request_end_translation_session()

        self._clear_queue(self.ocr_queue)
        self._clear_queue(self.translation_queue)

        # Clear translation text display
        if self.translation_text and self.translation_text != None:
            try:
                # Handle PySide6 widget
                if hasattr(self.translation_text, 'set_rtl_text'):
                    self.translation_text.set_rtl_text("", "")
                # Handle Qt text display methods
                elif hasattr(self.translation_text, 'clear'):
                    self.translation_text.clear()
            except Exception as e_ctt:
                log_debug(f"Error clearing translation text on stop: {e_ctt}")
        
        if self.source_overlay and self.source_overlay != None and self.source_overlay.isVisible():
            try: self.source_overlay.hide()
            except Exception: log_debug("Error hiding source overlay on stop.")
        
        if self.target_overlay and self.target_overlay != None and self.target_overlay.isVisible():
            try: self.target_overlay.hide()
            except Exception: log_debug("Error hiding target overlay on stop.")
        
        
        status_text_stopped = "Status: " + self.ui_lang.get_label("status_stopped", "Stopped (Press ~ to Start)")
        
        log_debug("Translation process stopped.")
        
        self.toggle_in_progress = False # Release the lock here

        # If we were in the middle of a discovery-to-regional restart, trigger start now
        if hasattr(self, 'restart_after_shutdown') and self.restart_after_shutdown:
            self.restart_after_shutdown = False
            log_debug("SHUTDOWN: Triggering scheduled restart after discovery...")
            QTimer.singleShot(500, self.toggle_translation) # Re-start in regional mode

    def toggle_translation(self):
        # Add re-entrancy lock
        if self.toggle_in_progress:
            log_debug("Toggle translation already in progress, ignoring call.")
            return
        
        self.toggle_in_progress = True

        if self.is_running:
            log_debug("Stopping translation process requested by user.")
            self.is_running = False
            
            # DO NOT request session ends here. This will be done in _finalize_shutdown.
            # Context clearing is now handled automatically after session end logging in llm_provider_base.py
            
            # Update usage statistics when translation stops
            if hasattr(self, 'update_gemini_stats'):
                self.update_gemini_stats()
            if hasattr(self, 'update_deepl_usage'):
                self.update_deepl_usage()
            
            
            
            QApplication.processEvents()

            active_threads_copy = self.threads[:]
            self.threads.clear()

            thread_stop_start_time = time.monotonic()
            log_debug(f"Waiting for main worker threads to join: {[t.name for t in active_threads_copy if t.is_alive()]}")

            for thread_obj in active_threads_copy:
                if thread_obj.is_alive():
                    try:
                        thread_obj.join(timeout=1.0) # Short timeout for main threads
                    except Exception as join_err_tt:
                        log_debug(f"Error joining thread {thread_obj.name}: {join_err_tt}")

            log_debug(f"Main worker threads joined in {time.monotonic() - thread_stop_start_time:.2f}s.")

            # Use non-blocking poll for graceful shutdown
            log_debug("Starting graceful shutdown poll for API call thread pools...")
            self._shutdown_start_time = time.monotonic()
            QTimer.singleShot(0, self._graceful_shutdown_poll)
            # The rest of the shutdown logic is now in _finalize_shutdown()
            # The lock will be released in _finalize_shutdown()

        else: 
            try:
                log_debug("Starting translation process requested by user...")
                 
                
                QApplication.processEvents()

                valid_start_flag = True 
                
                if not self.source_overlay or not self._widget_exists_safely(self.source_overlay):
                    raise ValueError("Source area overlay missing. Select source area.")
                if valid_start_flag and (not self.target_overlay or not self._widget_exists_safely(self.target_overlay)):
                    raise ValueError("Target area overlay missing. Select target area.")
                if valid_start_flag and (not self.translation_text or not self._widget_exists_safely(self.translation_text)):
                    raise ValueError("Target text display widget missing. Reselect target area.")
                

                
                if valid_start_flag:
                     try:
                         # Instead of forcing old variables onto the overlay from INI,
                         # we use the current positions from the GUI (PySide6) - this solves the jumping frame issue
                         try:
                             pass
                         except Exception as e_ini_read:
                             log_debug(f"START: Could not restore overlays from INI, using current positions. Error: {e_ini_read}")
                         
                         # Handle Auto Detection full screen expansion
                         if self.auto_detect_enabled:
                             sw = QApplication.primaryScreen().geometry().width()
                             sh = QApplication.primaryScreen().geometry().height()
                             log_debug(f"Auto Detection ON: Expanding source_overlay to full screen (0, 0, {sw}, {sh})")
                             if self.source_overlay and self._widget_exists_safely(self.source_overlay):
                                 self.source_overlay.setGeometry(0, 0, sw, sh)
                             
                             # Update source_area variables to full screen
                             self.source_area_x1 = 0
                             self.source_area_y1 = 0
                             self.source_area_x2 = sw
                             self.source_area_y2 = sh
                             
                             # Initialize detected coordinates
                             self.detected_source_area_x1 = 0
                             self.detected_source_area_y1 = 0
                             self.detected_source_area_x2 = 0
                             self.detected_source_area_y2 = 0
                             # Resilient discovery_timeout loading logic
                             try:
                                 import configparser
                                 _temp_cfg = configparser.ConfigParser()
                                 _temp_cfg.read('ocr_translator_config.ini', encoding='utf-8')
                                 if 'Settings' not in _temp_cfg:
                                     _temp_cfg['Settings'] = {}
                                 
                                 if 'discovery_timeout' not in _temp_cfg['Settings']:
                                     log_debug("DISCOVERY: discovery_timeout missing from INI. Adding default 120s and saving.")
                                     _temp_cfg['Settings']['discovery_timeout'] = '120'
                                     import io
                                     _buf = io.StringIO()
                                     _temp_cfg.write(_buf)
                                     _content = _buf.getvalue().strip() + '\n'
                                     with open('ocr_translator_config.ini', 'w', encoding='utf-8') as _f:
                                         _f.write(_content)
                                     _new_timeout = 120
                                 else:
                                     _new_timeout = _temp_cfg.getint('Settings', 'discovery_timeout', fallback=120)
                                 
                                 self.discovery_timeout = _new_timeout
                                 log_debug(f"DISCOVERY: Loaded timeout from INI: {_new_timeout}s")
                             except Exception as e_cfg:
                                 log_debug(f"DISCOVERY: Could not handle timeout from INI, using fallback ({self.discovery_timeout}s). Error: {e_cfg}")

                             self.discovery_start_time = time.monotonic()
                             self.is_finishing_discovery = False
                             self.detection_samples = []
                             
                             log_debug(f"detected_source_area_x1 = {self.detected_source_area_x1}")
                             log_debug(f"detected_source_area_y1 = {self.detected_source_area_y1}")
                             log_debug(f"detected_source_area_x2 = {self.detected_source_area_x2}")
                             log_debug(f"detected_source_area_y2 = {self.detected_source_area_y2}")

                             # Re-read geometry after forcing
                             QApplication.processEvents()
                             
                             # Set source_area directly (don't rely on get_geometry which may lag)
                             self.source_area = [0, 0, sw, sh]

                         if self.source_overlay and hasattr(self.source_overlay, 'get_geometry'):
                             self.source_area = self.source_overlay.get_geometry()
                         else:
                             raise ValueError("Source overlay not found or does not support get_geometry()")

                         
                         if self.target_overlay and hasattr(self.target_overlay, 'get_geometry'):
                             self.target_area = self.target_overlay.get_geometry()
                         else:
                             raise ValueError("Target overlay not found or does not support get_geometry()")
                         
                         if not self._validate_area_coords(self.source_area, "source"): valid_start_flag = False
                         if valid_start_flag and not self._validate_area_coords(self.target_area, "target"): valid_start_flag = False
                     except (Exception, AttributeError) as e_gog:
                         raise ValueError(f"Could not get overlay geometry: {e_gog}")
                         valid_start_flag = False
                
                if not valid_start_flag:
                    
                    status_text_failed = "Status: Start Failed"
                    if self.KEYBOARD_AVAILABLE: status_text_failed += " (Press ~ to Retry)"
                    
                    log_debug("Start aborted due to failed pre-start validation checks.")
                    return

                log_debug("Pre-start checks passed. Preparing to start threads...")
                self.text_stability_counter = 0
                self.previous_text = ""
                self.last_image_hash = None
                self.last_screenshot = None 
                self.last_processed_image = None 
                
                self._reset_gemini_batch_state() 

                try:
                    if self.target_overlay and self.target_overlay != None and not self.target_overlay.isVisible():
                        self.target_overlay.show()
                except Exception:
                    log_debug("Warning: Error ensuring target overlay visibility at start (likely closed).")

                self._clear_queue(self.ocr_queue)
                self._clear_queue(self.translation_queue)

                self.cache_manager.load_file_caches()

                # API Key Validation before starting
                missing_gemini = not self.gemini_api_key or self.gemini_api_key.strip() == ""
                missing_deepl = (self.translation_model == 'deepl_api') and (not self.deepl_api_key or self.deepl_api_key.strip() == "")
                
                error_msg = None
                if missing_gemini:
                    error_msg = self.ui_lang.get_label('error_no_gemini_key', 'Provide your Gemini API key first.')
                elif missing_deepl:
                    error_msg = self.ui_lang.get_label('error_no_deepl_key', 'Provide your DeepL API key first.')

                self.is_running = True 
                
                if error_msg:
                    self.update_translation_text(error_msg)
                    log_debug(f"START BLOCKED: {error_msg}")
                    # Skip thread starting logic
                else:
                    if hasattr(self, 'translation_handler'):
                        if self.is_api_based_ocr_model():
                            self.translation_handler.start_ocr_session()
                        self.translation_handler.start_translation_session()
                    
                    status_text_running = "Status: " + self.ui_lang.get_label("status_running", "Running (Press ~ to Stop)")
                    
                    QApplication.processEvents()
                    
                    capture_thread_instance = threading.Thread(target=run_capture_thread, args=(self,), name="CaptureThread", daemon=True)
                    ocr_thread_instance = threading.Thread(target=run_ocr_thread, args=(self,), name="OCRThread", daemon=True)
                    translation_thread_instance = threading.Thread(target=run_translation_thread, args=(self,), name="TranslationThread", daemon=True)

                    self.threads = [capture_thread_instance, ocr_thread_instance, translation_thread_instance]
                    for t_obj in self.threads:
                        t_obj.start()
                    log_debug(f"Threads started: {[t.name for t in self.threads]}")
                
                # Release lock after successful start
                self.toggle_in_progress = False
            
            finally:
                # Release lock if start failed before threads were launched
                if not self.is_running: 
                    self.toggle_in_progress = False

    def _validate_area_coords(self, area_coordinates, area_type_str):
        min_dimension = 10 
        if not area_coordinates or len(area_coordinates) != 4:
            messagebox.showerror("Area Validation Error", f"Invalid {area_type_str} area data: {area_coordinates}.", parent=None)
            return False
        try:
            x1_val, y1_val, x2_val, y2_val = map(int, area_coordinates)
            width_val = x2_val - x1_val
            height_val = y2_val - y1_val
            if width_val < min_dimension or height_val < min_dimension:
                messagebox.showerror("Area Validation Error",
                                     f"{area_type_str.capitalize()} area too small ({width_val}x{height_val}). Min {min_dimension}x{min_dimension}.",
                                     parent=None)
                return False
            return True
        except (ValueError, TypeError) as e_vac:
            messagebox.showerror("Area Validation Error", f"Invalid coordinates in {area_type_str} area: {area_coordinates}. Error: {e_vac}", parent=None)
            return False

    def stop_translation_from_thread(self):
        if self.is_running:
            log_debug("Requesting stop translation from worker thread.")
            if self.root != None:
                QTimer.singleShot(0, self.toggle_translation)

    def update_translation_model_names(self):
        """Update translation model names with localized strings from CSV files."""
        self.translation_model_names = {
            'deepl_api': 'DeepL API'
        }
        
        # Get Gemini model names from CSV file
        gemini_translation_models = self.gemini_models_manager.get_translation_model_names()
        
        for model_name in gemini_translation_models:
            key = f'gemini_translation_{model_name}'
            self.translation_model_names[key] = f"Google {model_name}"
            
        if gemini_translation_models:
            self.translation_model_names['gemini_api'] = gemini_translation_models[0]
            
        # Update the reverse mapping as well
        self.translation_model_values = {v: k for k, v in self.translation_model_names.items()}
        log_debug(f"Updated translation model names: {self.translation_model_names}")

    def update_ocr_model_names(self):
        """Update OCR model names with localized strings."""
        self.ocr_model_names = {}
        
        # Get Gemini model names from CSV file
        gemini_ocr_models = self.gemini_models_manager.get_ocr_model_names()
        
        for model_name in gemini_ocr_models:
            key = f'gemini_ocr_{model_name}'
            self.ocr_model_names[key] = f"Google {model_name}"
            
        log_debug(f"Updated OCR model names: {self.ocr_model_names}")

    def get_current_gemini_model_for_translation(self):
        """Get the API name of currently selected Gemini translation model."""
        display_name = self.gemini_translation_model
        return self.gemini_models_manager.get_api_name_by_display_name(display_name)
    
    def get_current_gemini_model_for_ocr(self):
        """Get the API name of currently selected Gemini OCR model."""
        display_name = self.gemini_ocr_model
        return self.gemini_models_manager.get_api_name_by_display_name(display_name)
    
    def is_gemini_model(self, model_name):
        """Check if the given model name is a Gemini model."""
        if not model_name:
            return False
        
        if model_name in ['gemini', 'gemini_api']:
            return True
        
        if model_name.startswith('gemini_'):
            return True
            
        # Check if it's in our Gemini model lists
        if hasattr(self, 'gemini_models_manager'):
            if model_name in self.gemini_models_manager.get_translation_model_names():
                return True
            if model_name in self.gemini_models_manager.get_ocr_model_names():
                return True
                
        return False
    
    def is_api_based_ocr_model(self, model_name=None):
        """Check if the given (or current) OCR model is API-based."""
        if model_name is None:
            model_name = self.get_ocr_model_setting()
        
        return self.is_gemini_model(model_name)
    


    def setup_network_cleanup(self):
        """Setup periodic network connection cleanup to prevent stack corruption."""
        def cleanup_network_connections():
            try:
                # Force client recreation to clear connection pools
                if hasattr(self, 'translation_handler') and hasattr(self.translation_handler, 'gemini_client'):
                    if self.translation_handler.gemini_client is not None:
                        old_client = self.translation_handler.gemini_client
                        
                        # Force client refresh
                        self.translation_handler._force_client_refresh()
                        
                        # Try to close old client connections if possible
                        try:
                            if hasattr(old_client, 'close'):
                                old_client.close()
                            elif hasattr(old_client, '_transport') and hasattr(old_client._transport, 'close'):
                                old_client._transport.close()
                        except Exception as close_error:
                            log_debug(f"Error closing old client: {close_error}")
                        
                        log_debug("Performed periodic network connection cleanup")
                    
                # Also flush DNS cache
                self.flush_dns_cache_if_needed()
                    
            except Exception as e:
                log_debug(f"Error during periodic network cleanup: {e}")
            
            # Schedule next cleanup in 20 minutes
            if self.is_running:  # Only schedule if application is still running
                QTimer.singleShot(1200000, cleanup_network_connections)  # 20 minutes = 1200000ms
        
        # Start cleanup cycle after 20 minutes of operation
        QTimer.singleShot(1200000, cleanup_network_connections)
        log_debug("Scheduled periodic network cleanup every 20 minutes")


    def flush_dns_cache_if_needed(self):
        """Flush system DNS cache if network performance degrades."""
        if not hasattr(self, 'last_dns_flush'):
            self.last_dns_flush = time.time()
            return
        
        current_time = time.time()
        # Flush DNS every hour during active use
        if current_time - self.last_dns_flush > 3600:  # 1 hour
            try:
                import subprocess
                result = subprocess.run(['ipconfig', '/flushdns'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    self.last_dns_flush = current_time
                    log_debug("Successfully flushed DNS cache for network maintenance")
                else:
                    log_debug(f"DNS flush command failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                log_debug("DNS flush command timed out")
            except Exception as e:
                log_debug(f"Could not flush DNS cache: {e}")


    def load_custom_prompt(self):
        """Loads the custom prompt text from file."""
        try:
            if os.path.exists(self.custom_prompt_file):
                with open(self.custom_prompt_file, 'r', encoding='utf-8-sig') as f:
                    self.custom_prompt_text = f.read()
                log_debug(f"Loaded custom prompt ({len(self.custom_prompt_text)} characters)")
            else:
                self.custom_prompt_text = ""
        except Exception as e:
            log_debug(f"Error loading custom prompt: {e}")
            self.custom_prompt_text = ""
            
        try:
            if os.path.exists(self.custom_ocr_prompt_file):
                with open(self.custom_ocr_prompt_file, 'r', encoding='utf-8-sig') as f:
                    self.custom_ocr_prompt_text = f.read()
                log_debug(f"Loaded custom OCR prompt ({len(self.custom_ocr_prompt_text)} characters)")
            else:
                self.custom_ocr_prompt_text = ""
        except Exception as e:
            log_debug(f"Error loading custom OCR prompt: {e}")
            self.custom_ocr_prompt_text = ""


    def save_custom_prompt(self, text):
        """Saves the custom prompt text to file."""
        try:
            self.custom_prompt_text = text
            with open(self.custom_prompt_file, 'w', encoding='utf-8-sig') as f:
                f.write(text)
            log_debug(f"Saved custom prompt ({len(text)} characters)")
            return True
        except Exception as e:
            log_debug(f"Error saving custom prompt: {e}")
            return False


    def save_custom_ocr_prompt(self, text):
        """Saves the custom OCR prompt text to file."""
        try:
            self.custom_ocr_prompt_text = text
            with open(self.custom_ocr_prompt_file, 'w', encoding='utf-8-sig') as f:
                f.write(text)
            log_debug(f"Saved custom OCR prompt ({len(text)} characters)")
            return True
        except Exception as e:
            log_debug(f"Error saving custom OCR prompt: {e}")
            return False

    def start_ui_update(self):
        self._is_updating_ui = True
        
    def end_ui_update(self):
        self._is_updating_ui = False
