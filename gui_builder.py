# gui_builder.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import os
from logger import log_debug
from ui_elements import create_scrollable_tab
import tkinter.font as tkFont

def get_system_fonts():
    """Get available system fonts with preferred fonts at the top"""
    try:
        # Get all system fonts
        all_fonts = list(tkFont.families())
        all_fonts.sort()
        
        # Preferred fonts to show at the top (if available)
        preferred_fonts = ['Arial', 'Times New Roman', 'Calibri', 'Cambria']
        
        # Build final list with preferred fonts first
        final_fonts = []
        for font in preferred_fonts:
            if font in all_fonts:
                final_fonts.append(font)
                all_fonts.remove(font)  # Remove to avoid duplicates
        
        # Add remaining fonts alphabetically
        final_fonts.extend(all_fonts)
        return final_fonts
    except Exception:
        # Fallback if system font detection fails
        return ['Arial', 'Times New Roman', 'Calibri', 'Cambria', 'Helvetica', 'Courier New', 'Verdana', 'Tahoma']

def create_main_tab(app):
    # Create a scrollable tab content frame
    scrollable_content = create_scrollable_tab(app.tab_control, app.ui_lang.get_label("main_tab_title"))
    app.tab_main = scrollable_content
    
    # Create the main frame inside the scrollable area
    frame = ttk.LabelFrame(scrollable_content, text=app.ui_lang.get_label("main_tab_title"))
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Add GUI language selection at the top
    language_frame = ttk.Frame(frame)
    language_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="w")
    
    ttk.Label(language_frame, text=app.ui_lang.get_label("gui_language_label")).pack(side=tk.LEFT, padx=(0,5))
    app.gui_language_combobox = ttk.Combobox(language_frame, textvariable=app.gui_language_var,
                                           values=app.ui_lang.get_language_list(), width=15, state='readonly')
    app.gui_language_combobox.pack(side=tk.LEFT)
    
    def on_gui_language_changed(event):
        selected_display_name = app.gui_language_var.get()
        lang_code = app.ui_lang.get_language_code_from_name(selected_display_name)
        
        log_debug(f"GUI Language Change: selected_display='{selected_display_name}', lang_code='{lang_code}', current_lang='{app.ui_lang.current_lang}'")
        
        # Guard: Only process if the language actually changed
        if lang_code and lang_code != app.ui_lang.current_lang:
            log_debug(f"Changing GUI language from {app.ui_lang.current_lang} to {lang_code}")
            app.ui_lang.load_language(lang_code)
            
            # Log the new state after language change
            log_debug(f"GUI language changed - new current_lang: '{app.ui_lang.current_lang}'")
            
            # Update all dropdowns with new language before rebuilding UI
            app.ui_interaction_handler.update_all_dropdowns_for_language_change()
            
            # This complete UI rebuild is necessary to update all elements
            app.update_ui_language()
            
            # Save settings only after all UI updates are complete
            # The UI update methods will suppress saves during the update process
            if app._fully_initialized:
                app.save_settings()
        else:
            log_debug(f"GUI language unchanged: {lang_code}")
    
    app.gui_language_combobox.bind('<<ComboboxSelected>>', on_gui_language_changed)

    ttk.Button(frame, text=app.ui_lang.get_label("select_source_btn"), command=app.select_source_area, width=30).grid(row=1, column=0, padx=5, pady=5, sticky="w")
    ttk.Button(frame, text=app.ui_lang.get_label("select_target_btn"), command=app.select_target_area, width=30).grid(row=2, column=0, padx=5, pady=5, sticky="w")
    app.start_stop_btn = ttk.Button(frame, text=app.ui_lang.get_label("start_btn"), command=app.toggle_translation, width=30)
    app.start_stop_btn.grid(row=3, column=0, padx=5, pady=5, sticky="w")
    
    # Remove individual tab bindings and add a general binding in app_logic.py after tabs are created
    app.main_tab_start_button = app.start_stop_btn  # Store reference for the tab changed handler in app_logic.py
    ttk.Button(frame, text=app.ui_lang.get_label("hide_source_btn"), command=app.toggle_source_visibility, width=30).grid(row=4, column=0, padx=5, pady=5, sticky="w")
    ttk.Button(frame, text=app.ui_lang.get_label("hide_target_btn"), command=app.toggle_target_visibility, width=30).grid(row=5, column=0, padx=5, pady=5, sticky="w")
    ttk.Button(frame, text=app.ui_lang.get_label("clear_cache_btn"), command=app.clear_cache, width=30).grid(row=6, column=0, padx=5, pady=5, sticky="w")
    ttk.Button(frame, text=app.ui_lang.get_label("clear_debug_log_btn"), command=app.clear_debug_log, width=30).grid(row=7, column=0, padx=5, pady=5, sticky="w")
    
    # Debug log toggle button
    if app.debug_logging_enabled_var.get():
        initial_debug_toggle_text = app.ui_lang.get_label("toggle_debug_log_disable_btn")
    else:
        initial_debug_toggle_text = app.ui_lang.get_label("toggle_debug_log_enable_btn")
    app.debug_log_toggle_btn = ttk.Button(frame, text=initial_debug_toggle_text, command=app.toggle_debug_logging, width=30)
    app.debug_log_toggle_btn.grid(row=8, column=0, padx=5, pady=5, sticky="w")

    if app.KEYBOARD_AVAILABLE:
        shortcuts_frame = ttk.LabelFrame(frame, text=app.ui_lang.get_label("keyboard_shortcuts_title"))
        shortcuts_frame.grid(row=9, column=0, columnspan=2, padx=5, pady=10, sticky="ew")
        ttk.Label(shortcuts_frame, text="~ : " + app.ui_lang.get_label("shortcut_start_stop", "Start/Stop Translation")).grid(row=0, column=0, padx=10, pady=2, sticky="w")
        ttk.Label(shortcuts_frame, text="Alt+1 : " + app.ui_lang.get_label("shortcut_toggle_source", "Toggle Source Window Visibility")).grid(row=1, column=0, padx=10, pady=2, sticky="w")
        ttk.Label(shortcuts_frame, text="Alt+2 : " + app.ui_lang.get_label("shortcut_toggle_target", "Toggle Translation Window Visibility")).grid(row=2, column=0, padx=10, pady=2, sticky="w")
        ttk.Label(shortcuts_frame, text="Alt+S : " + app.ui_lang.get_label("shortcut_save_settings", "Save Settings")).grid(row=3, column=0, padx=10, pady=2, sticky="w")
        ttk.Label(shortcuts_frame, text="Alt+C : " + app.ui_lang.get_label("shortcut_clear_cache", "Clear Cache")).grid(row=4, column=0, padx=10, pady=2, sticky="w")
        ttk.Label(shortcuts_frame, text="Alt+L : " + app.ui_lang.get_label("shortcut_clear_log", "Clear Debug Log")).grid(row=5, column=0, padx=10, pady=(2,8), sticky="w")
        status_row = 10
        app.status_label = ttk.Label(frame, text=app.ui_lang.get_label("status_ready_hotkey"))
    else:
        status_row = 9
        app.status_label = ttk.Label(frame, text=app.ui_lang.get_label("status_ready"))
    
    app.status_label.grid(row=status_row, column=0, columnspan=2, padx=5, pady=5, sticky="w")
    frame.columnconfigure(0, weight=1)


def create_settings_tab(app):
    # Create a scrollable tab content frame
    scrollable_content = create_scrollable_tab(app.tab_control, app.ui_lang.get_label("settings_tab_title"))
    app.tab_settings = scrollable_content
    
    # Create the settings frame inside the scrollable area
    frame = ttk.LabelFrame(scrollable_content, text=app.ui_lang.get_label("settings_tab_title"))
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    def validate_int_range(P, min_val, max_val):
        if P == "": return True
        try:
            value = int(P)
            return min_val <= value <= max_val
        except ValueError: return False

    def validate_odd_int_range(P, min_val, max_val):
        if P == "": return True
        try:
            value = int(P)
            return min_val <= value <= max_val and value % 2 == 1  # Must be odd
        except ValueError: return False
            
    # Validation functions for parameters
    validate_block_size = frame.register(lambda P: validate_odd_int_range(P, 3, 101))
    validate_c_value = frame.register(lambda P: validate_int_range(P, -75, 75))
    validate_beam_size = frame.register(lambda P: validate_int_range(P, 1, 50))
    validate_scan_interval = frame.register(lambda P: validate_int_range(P, 50, 2000))
    validate_timeout = frame.register(lambda P: validate_int_range(P, 0, 60))
    validate_stability = frame.register(lambda P: validate_int_range(P, 0, 5))
    validate_confidence = frame.register(lambda P: validate_int_range(P, 0, 100))
    validate_font_size = frame.register(lambda P: validate_int_range(P, 8, 72))
    
    style = ttk.Style()
    
    # Configure TCombobox style for better readability when focused
    # Simple fix: just change text color to white when focused (blue background is system default)
    style.map('TCombobox',
        foreground=[
            ('readonly', 'focus', 'white'),      # White text when focused for better contrast
            ('readonly', '!focus', 'black'),     # Black text when not focused  
            ('!readonly', 'focus', 'white'),     # White text when focused (editable)
            ('!readonly', '!focus', 'black')     # Black text when not focused (editable)
        ]
    )

    # Ensure no insertion cursor is visible
    style.configure('TCombobox',
                    insertwidth=0,
                    insertontime=0
                   )

    # Wrapper function to shift focus after combobox selection
    def create_combobox_handler_wrapper(original_handler_func):
        def wrapper(event):
            # Call the original handler
            original_handler_func(event)

            # Schedule focus shift to the parent tab frame (app.tab_settings)
            widget = event.widget
            if widget.winfo_exists() and app.tab_settings.winfo_exists():
                widget.after_idle(app.tab_settings.focus_set)
        return wrapper

    # Row 0: Translation Model Selection
    ttk.Label(frame, text=app.ui_lang.get_label("translation_model_label")).grid(row=0, column=0, padx=5, pady=5, sticky="w")
    
    translation_models_available_for_ui = []
    log_debug(f"GUI Builder: Translation model availability check:")
    log_debug(f"  GEMINI_API_AVAILABLE: {app.GEMINI_API_AVAILABLE}")
    log_debug(f"  OPENAI_API_AVAILABLE: {app.OPENAI_API_AVAILABLE}")
    log_debug(f"  MARIANMT_AVAILABLE: {app.MARIANMT_AVAILABLE}")  
    log_debug(f"  DEEPL_API_AVAILABLE: {app.DEEPL_API_AVAILABLE}")
    log_debug(f"  GOOGLE_TRANSLATE_API_AVAILABLE: {app.GOOGLE_TRANSLATE_API_AVAILABLE}")
    
    # Add Gemini models first (from CSV file)
    if app.GEMINI_API_AVAILABLE:
        gemini_translation_models = app.gemini_models_manager.get_translation_model_names()
        translation_models_available_for_ui.extend(gemini_translation_models)
        log_debug(f"Added Gemini translation models: {gemini_translation_models}")
    
    # Add OpenAI models second (from CSV file)
    if app.OPENAI_API_AVAILABLE:
        openai_translation_models = app.openai_models_manager.get_translation_model_names()
        translation_models_available_for_ui.extend(openai_translation_models)
        log_debug(f"Added OpenAI translation models: {openai_translation_models}")
    
    # Add other translation models
    if app.MARIANMT_AVAILABLE: 
        translation_models_available_for_ui.append(app.translation_model_names['marianmt'])
    if app.DEEPL_API_AVAILABLE: 
        translation_models_available_for_ui.append(app.translation_model_names['deepl_api'])
    if app.GOOGLE_TRANSLATE_API_AVAILABLE: 
        translation_models_available_for_ui.append(app.translation_model_names['google_api'])
    
    log_debug(f"GUI Builder: Available translation models for UI: {translation_models_available_for_ui}")
    
    if not translation_models_available_for_ui: 
        default_model_key_from_var = app.translation_model_var.get() 
        translation_models_available_for_ui.append(app.translation_model_names.get(default_model_key_from_var, "MarianMT (offline and free)"))

    app.translation_model_combobox = ttk.Combobox(frame, textvariable=app.translation_model_display_var,
                                           values=translation_models_available_for_ui, width=25, state='readonly')
    app.translation_model_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
    
    # Set initial value from config - follow same pattern as OCR model
    current_translation_model = app.translation_model_var.get()
    log_debug(f"Current translation model type: {current_translation_model}")
    
    if current_translation_model == 'gemini_api':
        # For Gemini translation, read the specific model from config
        if hasattr(app, 'config'):
            saved_gemini_translation_model = app.config['Settings'].get('gemini_translation_model', '')
            if saved_gemini_translation_model and saved_gemini_translation_model in translation_models_available_for_ui:
                app.translation_model_display_var.set(saved_gemini_translation_model)
                log_debug(f"Set translation model from config: {saved_gemini_translation_model}")
            elif app.GEMINI_API_AVAILABLE and app.gemini_models_manager.get_translation_model_names():
                app.translation_model_display_var.set(app.gemini_models_manager.get_translation_model_names()[0])
                log_debug(f"Set translation model to first Gemini: {app.gemini_models_manager.get_translation_model_names()[0]}")
            else:
                app.translation_model_display_var.set(translation_models_available_for_ui[0] if translation_models_available_for_ui else "MarianMT (offline and free)")
                log_debug(f"Set translation model to first available: {translation_models_available_for_ui[0] if translation_models_available_for_ui else 'MarianMT'}")
        else:
            # Fallback to first available Gemini model or first overall
            if app.GEMINI_API_AVAILABLE and app.gemini_models_manager.get_translation_model_names():
                app.translation_model_display_var.set(app.gemini_models_manager.get_translation_model_names()[0])
            else:
                app.translation_model_display_var.set(translation_models_available_for_ui[0] if translation_models_available_for_ui else "MarianMT (offline and free)")
    elif app.is_openai_model(current_translation_model):
        # For OpenAI translation, read the specific model from config
        if hasattr(app, 'config'):
            saved_openai_translation_model = app.config['Settings'].get('openai_translation_model', '')
            if saved_openai_translation_model and saved_openai_translation_model in translation_models_available_for_ui:
                app.translation_model_display_var.set(saved_openai_translation_model)
                log_debug(f"Set translation model from config: {saved_openai_translation_model}")
            elif app.OPENAI_API_AVAILABLE and app.openai_models_manager.get_translation_model_names():
                app.translation_model_display_var.set(app.openai_models_manager.get_translation_model_names()[0])
                log_debug(f"Set translation model to first OpenAI: {app.openai_models_manager.get_translation_model_names()[0]}")
            else:
                app.translation_model_display_var.set(translation_models_available_for_ui[0] if translation_models_available_for_ui else "MarianMT (offline and free)")
                log_debug(f"Set translation model to first available: {translation_models_available_for_ui[0] if translation_models_available_for_ui else 'MarianMT'}")
        else:
            # Fallback to first available OpenAI model or first overall
            if app.OPENAI_API_AVAILABLE and app.openai_models_manager.get_translation_model_names():
                app.translation_model_display_var.set(app.openai_models_manager.get_translation_model_names()[0])
            else:
                app.translation_model_display_var.set(translation_models_available_for_ui[0] if translation_models_available_for_ui else "MarianMT (offline and free)")
    elif current_translation_model == 'marianmt' and app.MARIANMT_AVAILABLE:
        app.translation_model_display_var.set(app.translation_model_names['marianmt'])
        log_debug(f"Set translation model to MarianMT: {app.translation_model_names['marianmt']}")
    elif current_translation_model == 'deepl_api' and app.DEEPL_API_AVAILABLE:
        app.translation_model_display_var.set(app.translation_model_names['deepl_api'])
        log_debug(f"Set translation model to DeepL: {app.translation_model_names['deepl_api']}")
    elif current_translation_model == 'google_api' and app.GOOGLE_TRANSLATE_API_AVAILABLE:
        app.translation_model_display_var.set(app.translation_model_names['google_api'])
        log_debug(f"Set translation model to Google: {app.translation_model_names['google_api']}")
    else:
        # Default to first available option
        app.translation_model_display_var.set(translation_models_available_for_ui[0] if translation_models_available_for_ui else "MarianMT (offline and free)")
        log_debug(f"Set translation model to default: {translation_models_available_for_ui[0] if translation_models_available_for_ui else 'MarianMT'}")
    
    def handle_translation_model_selection(event):
        app.on_translation_model_selection_changed(event=event, initial_setup=False)
    app.translation_model_combobox.bind('<<ComboboxSelected>>', 
        create_combobox_handler_wrapper(handle_translation_model_selection))

    # Row 0.5: OCR Model Selection
    ttk.Label(frame, text=app.ui_lang.get_label("ocr_model_label", "OCR Model")).grid(row=1, column=0, padx=5, pady=5, sticky="w")
    
    # Build OCR models list with Gemini models first, then OpenAI, then Tesseract
    ocr_models_available_for_ui = []
    
    # Add Gemini OCR models first (from CSV file)
    if app.GEMINI_API_AVAILABLE:
        gemini_ocr_models = app.gemini_models_manager.get_ocr_model_names()
        ocr_models_available_for_ui.extend(gemini_ocr_models)
        log_debug(f"Added Gemini OCR models: {gemini_ocr_models}")
    
    # Add OpenAI OCR models (from CSV file)
    if app.OPENAI_API_AVAILABLE:
        openai_ocr_models = app.openai_models_manager.get_ocr_model_names()
        ocr_models_available_for_ui.extend(openai_ocr_models)
        log_debug(f"Added OpenAI OCR models: {openai_ocr_models}")
    
    # Add Tesseract
    ocr_models_available_for_ui.append(app.ui_lang.get_label("ocr_model_tesseract", "Tesseract (offline)"))
    
    
    app.ocr_model_combobox = ttk.Combobox(frame, textvariable=app.ocr_model_display_var,
                                        values=ocr_models_available_for_ui, 
                                        width=25, state='readonly')
    app.ocr_model_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
    
    def on_ocr_model_changed(event):
        selected_display = app.ocr_model_display_var.get()
        log_debug(f"OCR model display changed to: {selected_display}")
        
        # Suppress traces during OCR model update to prevent premature saves
        app.suppress_traces()
        try:
            # Determine if this is a Gemini model, OpenAI model, or Tesseract
            if selected_display == app.ui_lang.get_label("ocr_model_tesseract", "Tesseract (offline)"):
                app.ocr_model_var.set('tesseract')
                log_debug("OCR model set to tesseract")
            elif app.GEMINI_API_AVAILABLE and selected_display in app.gemini_models_manager.get_ocr_model_names():
                app.ocr_model_var.set('gemini')
                # Store the specific Gemini model selection
                app.gemini_ocr_model_var.set(selected_display)
                log_debug(f"OCR model set to gemini, specific model: {selected_display}")
            elif app.OPENAI_API_AVAILABLE and selected_display in app.openai_models_manager.get_ocr_model_names():
                app.ocr_model_var.set('openai')
                # --- FIX: Store the specific OpenAI model selection ---
                app.openai_ocr_model_var.set(selected_display)
                log_debug(f"OCR model set to openai, specific model: {selected_display}")
            else:
                log_debug(f"Unknown OCR model selection: {selected_display}")
        finally:
            # Always restore traces
            app.restore_traces()
        
        # Update UI immediately for responsive feedback
        if hasattr(app, 'ui_interaction_handler'):
            app.ui_interaction_handler.update_ocr_model_ui()
        
        # Save settings after all variables are properly updated
        if app._fully_initialized:
            app.save_settings()
    
    app.ocr_model_combobox.bind('<<ComboboxSelected>>', 
        create_combobox_handler_wrapper(on_ocr_model_changed))

    # Store the options for later use when updating language
    app.ocr_model_options = ocr_models_available_for_ui

    app.source_lang_label = ttk.Label(frame, text=app.ui_lang.get_label("source_lang_label"))
    app.source_lang_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
    app.source_lang_combobox = ttk.Combobox(frame, textvariable=app.source_display_var, width=25, state='readonly')
    app.source_lang_combobox.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

    def on_source_lang_gui_changed(event):
        selected_display_name = app.source_display_var.get()
        active_model = app.translation_model_var.get()
        
        # Get current UI language - more robust detection
        current_ui_language = app.ui_lang.current_lang
        ui_language_for_lookup = 'polish' if current_ui_language == 'pol' else 'english'
        
        log_debug(f"Source lang GUI changed: selected='{selected_display_name}', model='{active_model}', ui_lang='{current_ui_language}', lookup='{ui_language_for_lookup}'")
        
        # Convert localized display name back to API code
        # Use the correct provider format for lookup
        provider_for_lookup = active_model  # Keep original format: 'google_api', 'deepl_api'
        api_code = app.language_manager.get_code_from_localized_name(
            selected_display_name, provider_for_lookup, ui_language_for_lookup)
        
        log_debug(f"Lookup result: '{selected_display_name}' -> '{api_code}'")
        
        if api_code:
            # Guard: Check if we're actually changing to a different value
            current_stored_value = None
            if active_model == 'google_api': 
                current_stored_value = app.google_source_lang
            elif active_model == 'deepl_api': 
                current_stored_value = app.deepl_source_lang
            elif active_model == 'gemini_api':
                current_stored_value = app.gemini_source_lang
            elif app.is_openai_model(active_model):
                current_stored_value = app.openai_source_lang
            
            # Only update and save if the value actually changed
            if api_code != current_stored_value:
                if active_model == 'google_api': 
                    app.google_source_lang = api_code
                    log_debug(f"Google source lang set to: {api_code}")
                elif active_model == 'deepl_api': 
                    app.deepl_source_lang = api_code
                    log_debug(f"DeepL source lang set to: {api_code}")
                    # Update DeepL model type options for beta language restriction
                    if hasattr(app, 'update_deepl_model_type_for_language'):
                        app.update_deepl_model_type_for_language()
                elif active_model == 'gemini_api':
                    app.gemini_source_lang = api_code
                    log_debug(f"Gemini source lang set to: {api_code}")
                elif app.is_openai_model(active_model):
                    app.openai_source_lang = api_code
                    log_debug(f"OpenAI source lang set to: {api_code}")
                
                # Clear context for currently active provider when source language is changed
                if (hasattr(app, 'translation_handler') and 
                    hasattr(app.translation_handler, '_clear_active_context')):
                    app.translation_handler._clear_active_context()
                
                app.source_lang_var.set(api_code) 
                log_debug(f"Source lang GUI changed for {active_model}: Display='{selected_display_name}', API Code='{api_code}' - SAVING")
                app.save_settings() 
            else:
                log_debug(f"Source lang unchanged for {active_model}: '{api_code}' - not saving")
        else:
            log_debug(f"ERROR: Could not find API code for source display '{selected_display_name}' / model '{active_model}' / ui_language '{ui_language_for_lookup}' - not saving invalid value")
            # Don't save invalid values - keep the previous valid selection
    
    app.source_lang_combobox.bind('<<ComboboxSelected>>', 
        create_combobox_handler_wrapper(on_source_lang_gui_changed))


    app.target_lang_label = ttk.Label(frame, text=app.ui_lang.get_label("target_lang_label"))
    app.target_lang_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
    app.target_lang_combobox = ttk.Combobox(frame, textvariable=app.target_display_var, width=25, state='readonly')
    app.target_lang_combobox.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

    def on_target_lang_gui_changed(event):
        selected_display_name = app.target_display_var.get()
        active_model = app.translation_model_var.get()
        
        # Get current UI language - more robust detection
        current_ui_language = app.ui_lang.current_lang
        ui_language_for_lookup = 'polish' if current_ui_language == 'pol' else 'english'
        
        log_debug(f"Target lang GUI changed: selected='{selected_display_name}', model='{active_model}', ui_lang='{current_ui_language}', lookup='{ui_language_for_lookup}'")
        
        # Convert localized display name back to API code
        # Use the correct provider format for lookup
        provider_for_lookup = active_model  # Keep original format: 'google_api', 'deepl_api'
        api_code = app.language_manager.get_code_from_localized_name(
            selected_display_name, provider_for_lookup, ui_language_for_lookup)
        
        log_debug(f"Lookup result: '{selected_display_name}' -> '{api_code}'")
        
        if api_code:
            # Guard: Check if we're actually changing to a different value
            current_stored_value = None
            if active_model == 'google_api': 
                current_stored_value = app.google_target_lang
            elif active_model == 'deepl_api': 
                current_stored_value = app.deepl_target_lang
            elif active_model == 'gemini_api':
                current_stored_value = app.gemini_target_lang
            elif app.is_openai_model(active_model):
                current_stored_value = app.openai_target_lang
            
            # Only update and save if the value actually changed
            if api_code != current_stored_value:
                if active_model == 'google_api': 
                    app.google_target_lang = api_code
                    log_debug(f"Google target lang set to: {api_code}")
                elif active_model == 'deepl_api': 
                    app.deepl_target_lang = api_code
                    log_debug(f"DeepL target lang set to: {api_code}")
                    # Update DeepL model type options for beta language restriction
                    if hasattr(app, 'update_deepl_model_type_for_language'):
                        app.update_deepl_model_type_for_language()
                elif active_model == 'gemini_api':
                    app.gemini_target_lang = api_code
                    log_debug(f"Gemini target lang set to: {api_code}")
                elif app.is_openai_model(active_model):
                    app.openai_target_lang = api_code
                    log_debug(f"OpenAI target lang set to: {api_code}")
                
                # Clear context for currently active provider when target language is changed
                if (hasattr(app, 'translation_handler') and 
                    hasattr(app.translation_handler, '_clear_active_context')):
                    app.translation_handler._clear_active_context()
                
                app.target_lang_var.set(api_code)
                log_debug(f"Target lang GUI changed for {active_model}: Display='{selected_display_name}', API Code='{api_code}' - SAVING")
                
                # Check if text direction changed and recreate overlay if needed
                try:
                    if hasattr(app, 'language_manager') and app.language_manager:
                        is_rtl = app.language_manager.is_rtl_language(api_code)
                        current_rtl_status = getattr(app.translation_text, 'is_rtl', False) if app.translation_text else False
                        
                        if is_rtl != current_rtl_status:
                            log_debug(f"Text direction changed (RTL: {is_rtl}), recreating target overlay")
                            # Import and recreate the target overlay with new RTL settings (preserve position)
                            from overlay_manager import create_target_overlay_om
                            create_target_overlay_om(app)  # System recreation, preserve position
                except Exception as e:
                    log_debug(f"Error updating RTL configuration: {e}")
                
                app.save_settings() 
            else:
                log_debug(f"Target lang unchanged for {active_model}: '{api_code}' - not saving")
        else:
            log_debug(f"ERROR: Could not find API code for target display '{selected_display_name}' / model '{active_model}' / ui_language '{ui_language_for_lookup}' - not saving invalid value")
            # Don't save invalid values - keep the previous valid selection
    app.target_lang_combobox.bind('<<ComboboxSelected>>', 
        create_combobox_handler_wrapper(on_target_lang_gui_changed))


    app.marian_model_label = ttk.Label(frame, text=app.ui_lang.get_label("marian_model_label"))
    app.marian_model_label.grid(row=4, column=0, padx=5, pady=5, sticky="w")
    app.marian_model_combobox = ttk.Combobox(frame, textvariable=app.marian_model_display_var, 
                                             values=app.marian_models_list, width=25, state='readonly')
    app.marian_model_combobox.grid(row=4, column=1, padx=5, pady=5, sticky="ew")
    
    def handle_marian_model_selection(event):
        # The marian_models_dict now contains localized display names as keys
        # so we can use the existing logic
        app.on_marian_model_selection_changed(event=event, initial_setup=False)
    app.marian_model_combobox.bind('<<ComboboxSelected>>', 
        create_combobox_handler_wrapper(handle_marian_model_selection))
    
    app.google_api_key_label = ttk.Label(frame, text=app.ui_lang.get_label("google_api_key_label")) 
    app.google_api_key_label.grid(row=5, column=0, padx=5, pady=5, sticky="w")
    app.google_api_key_entry = ttk.Entry(frame, textvariable=app.google_api_key_var, width=40, show="*")
    app.google_api_key_entry.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
    # Set initial button text based on visibility
    initial_google_text = app.ui_lang.get_label("show_btn", "Show")
    if hasattr(app, 'google_api_key_visible') and app.google_api_key_visible:
        initial_google_text = app.ui_lang.get_label("hide_btn", "Hide")
    app.google_api_key_button = ttk.Button(frame, text=initial_google_text, width=5, 
                                          command=lambda: app.toggle_api_key_visibility("google"))
    app.google_api_key_button.grid(row=5, column=2, padx=5, pady=5, sticky="w")

    app.deepl_api_key_label = ttk.Label(frame, text=app.ui_lang.get_label("deepl_api_key_label")) 
    app.deepl_api_key_label.grid(row=6, column=0, padx=5, pady=5, sticky="w")
    app.deepl_api_key_entry = ttk.Entry(frame, textvariable=app.deepl_api_key_var, width=40, show="*")
    app.deepl_api_key_entry.grid(row=6, column=1, padx=5, pady=5, sticky="ew")
    # Set initial button text based on visibility
    initial_deepl_text = app.ui_lang.get_label("show_btn", "Show") 
    if hasattr(app, 'deepl_api_key_visible') and app.deepl_api_key_visible:
        initial_deepl_text = app.ui_lang.get_label("hide_btn", "Hide")
    app.deepl_api_key_button = ttk.Button(frame, text=initial_deepl_text, width=5,
                                         command=lambda: app.toggle_api_key_visibility("deepl"))
    app.deepl_api_key_button.grid(row=6, column=2, padx=5, pady=5, sticky="w")

    # Gemini API Key input (only visible when Gemini is selected)
    app.gemini_api_key_label = ttk.Label(frame, text=app.ui_lang.get_label("gemini_api_key_label", "Gemini API Key")) 
    app.gemini_api_key_label.grid(row=7, column=0, padx=5, pady=5, sticky="w")
    app.gemini_api_key_entry = ttk.Entry(frame, textvariable=app.gemini_api_key_var, width=40, show="*")
    app.gemini_api_key_entry.grid(row=7, column=1, padx=5, pady=5, sticky="ew")
    # Set initial button text based on visibility
    initial_gemini_text = app.ui_lang.get_label("show_btn", "Show") 
    if hasattr(app, 'gemini_api_key_visible') and app.gemini_api_key_visible:
        initial_gemini_text = app.ui_lang.get_label("hide_btn", "Hide")
    app.gemini_api_key_button = ttk.Button(frame, text=initial_gemini_text, width=5,
                                          command=lambda: app.toggle_api_key_visibility("gemini"))
    app.gemini_api_key_button.grid(row=7, column=2, padx=5, pady=5, sticky="w")

    # Gemini Context Window Setting (only visible when Gemini is selected)
    app.gemini_context_window_label = ttk.Label(frame, text=app.ui_lang.get_label("gemini_context_window_label", "Context Window"))
    app.gemini_context_window_label.grid(row=8, column=0, padx=5, pady=5, sticky="w")
    
    context_window_options = [
        (0, app.ui_lang.get_label("gemini_context_window_0", "0 (Disabled)")),
        (1, app.ui_lang.get_label("gemini_context_window_1", "1 (Last subtitle)")),
        (2, app.ui_lang.get_label("gemini_context_window_2", "2 (Two subtitles)")),
        (3, app.ui_lang.get_label("gemini_context_window_3", "3 (Three subtitles)")),
        (4, app.ui_lang.get_label("gemini_context_window_4", "4 (Four subtitles)")),
        (5, app.ui_lang.get_label("gemini_context_window_5", "5 (Five subtitles)"))
    ]
    
    app.gemini_context_window_display_var = tk.StringVar()
    # Set initial display value based on current setting
    current_context_window = app.gemini_context_window_var.get()
    for value, display in context_window_options:
        if value == current_context_window:
            app.gemini_context_window_display_var.set(display)
            break
    else:
        # Fallback if current setting doesn't match any option
        app.gemini_context_window_display_var.set(context_window_options[1][1])  # Default to 1
    
    app.gemini_context_window_combobox = ttk.Combobox(frame, textvariable=app.gemini_context_window_display_var,
                                                     values=[display for _, display in context_window_options], 
                                                     width=25, state='readonly')
    app.gemini_context_window_combobox.grid(row=8, column=1, padx=5, pady=5, sticky="ew")
    
    def on_gemini_context_window_changed(event):
        selected_display = app.gemini_context_window_display_var.get()
        # Find the corresponding value
        for value, display in context_window_options:
            if display == selected_display:
                app.gemini_context_window_var.set(value)
                log_debug(f"Gemini context window changed to: {value} (display: {display})")
                # Clear active context when Gemini context window changes
                if hasattr(app, 'translation_handler') and hasattr(app.translation_handler, '_clear_active_context'):
                    app.translation_handler._clear_active_context()
                    log_debug(f"Active provider context cleared due to Gemini context window setting change")
                if app._fully_initialized:
                    app.save_settings()
                break
    
    app.gemini_context_window_combobox.bind('<<ComboboxSelected>>', 
        create_combobox_handler_wrapper(on_gemini_context_window_changed))

    # OpenAI API Key input (only visible when OpenAI is selected)
    app.openai_api_key_label = ttk.Label(frame, text=app.ui_lang.get_label("openai_api_key_label", "OpenAI API Key")) 
    app.openai_api_key_label.grid(row=9, column=0, padx=5, pady=5, sticky="w")
    app.openai_api_key_entry = ttk.Entry(frame, textvariable=app.openai_api_key_var, width=40, show="*")
    app.openai_api_key_entry.grid(row=9, column=1, padx=5, pady=5, sticky="ew")
    # Set initial button text based on visibility
    initial_openai_text = app.ui_lang.get_label("show_btn", "Show") 
    if hasattr(app, 'openai_api_key_visible') and app.openai_api_key_visible:
        initial_openai_text = app.ui_lang.get_label("hide_btn", "Hide")
    app.openai_api_key_button = ttk.Button(frame, text=initial_openai_text, width=5,
                                          command=lambda: app.toggle_api_key_visibility("openai"))
    app.openai_api_key_button.grid(row=9, column=2, padx=5, pady=5, sticky="w")

    # OpenAI Context Window Setting (only visible when OpenAI is selected)
    app.openai_context_window_label = ttk.Label(frame, text=app.ui_lang.get_label("openai_context_window_label", "Context Window"))
    app.openai_context_window_label.grid(row=10, column=0, padx=5, pady=5, sticky="w")
    
    openai_context_window_options = [
        (0, app.ui_lang.get_label("openai_context_window_0", "0 (Disabled)")),
        (1, app.ui_lang.get_label("openai_context_window_1", "1 (Last subtitle)")),
        (2, app.ui_lang.get_label("openai_context_window_2", "2 (Two subtitles)")),
        (3, app.ui_lang.get_label("openai_context_window_3", "3 (Three subtitles)")),
        (4, app.ui_lang.get_label("openai_context_window_4", "4 (Four subtitles)")),
        (5, app.ui_lang.get_label("openai_context_window_5", "5 (Five subtitles)"))
    ]
    
    app.openai_context_window_display_var = tk.StringVar()
    # Set initial display value based on current setting
    current_openai_context_window = app.openai_context_window_var.get()
    for value, display in openai_context_window_options:
        if value == current_openai_context_window:
            app.openai_context_window_display_var.set(display)
            break
    else:
        # Fallback if current setting doesn't match any option
        app.openai_context_window_display_var.set(openai_context_window_options[2][1])  # Default to 2
    
    app.openai_context_window_combobox = ttk.Combobox(frame, textvariable=app.openai_context_window_display_var,
                                                     values=[display for _, display in openai_context_window_options], 
                                                     width=25, state='readonly')
    app.openai_context_window_combobox.grid(row=10, column=1, padx=5, pady=5, sticky="ew")
    
    def on_openai_context_window_changed(event):
        selected_display = app.openai_context_window_display_var.get()
        # Find the corresponding value
        for value, display in openai_context_window_options:
            if display == selected_display:
                app.openai_context_window_var.set(value)
                log_debug(f"OpenAI context window changed to: {value} (display: {display})")
                # Clear active context when OpenAI context window changes
                if hasattr(app, 'translation_handler') and hasattr(app.translation_handler, '_clear_active_context'):
                    app.translation_handler._clear_active_context()
                    log_debug(f"Active provider context cleared due to OpenAI context window setting change")
                if app._fully_initialized:
                    app.save_settings()
                break
    
    app.openai_context_window_combobox.bind('<<ComboboxSelected>>', 
        create_combobox_handler_wrapper(on_openai_context_window_changed))

    # DeepL Model Type Selection (only visible when DeepL is selected)
    app.deepl_model_type_label = ttk.Label(frame, text=app.ui_lang.get_label("deepl_model_type_label", "Quality"))
    app.deepl_model_type_label.grid(row=11, column=0, padx=5, pady=5, sticky="w")
    
    # Create model type options with user-friendly names
    deepl_model_options = [
        ("latency_optimized", app.ui_lang.get_label("deepl_classic_model", "Classic")),
        ("quality_optimized", app.ui_lang.get_label("deepl_nextgen_model", "Next-gen"))
    ]
    
    app.deepl_model_display_var = tk.StringVar()
    # Set initial display value based on current setting
    current_model_type = app.deepl_model_type_var.get()
    for value, display in deepl_model_options:
        if value == current_model_type:
            app.deepl_model_display_var.set(display)
            break
    else:
        # Fallback if current setting doesn't match any option
        app.deepl_model_display_var.set(deepl_model_options[0][1])  # Default to Classic
    
    app.deepl_model_type_combobox = ttk.Combobox(frame, textvariable=app.deepl_model_display_var,
                                               values=[display for _, display in deepl_model_options], 
                                               width=25, state='readonly')
    app.deepl_model_type_combobox.grid(row=11, column=1, padx=5, pady=5, sticky="ew")
    
    def on_deepl_model_type_changed(event):
        selected_display = app.deepl_model_display_var.get()
        # Find the corresponding value
        for value, display in deepl_model_options:
            if display == selected_display:
                app.deepl_model_type_var.set(value)
                log_debug(f"DeepL model type changed to: {value} (display: {display})")
                if app._fully_initialized:
                    app.save_settings()
                break
    
    app.deepl_model_type_combobox.bind('<<ComboboxSelected>>', 
        create_combobox_handler_wrapper(on_deepl_model_type_changed))

    # Store the options for later use when updating language
    app.deepl_model_options = deepl_model_options

    # DeepL Context Window Setting (only visible when DeepL is selected)
    app.deepl_context_window_label = ttk.Label(frame, text=app.ui_lang.get_label("deepl_context_window_label", "Context Window"))
    app.deepl_context_window_label.grid(row=12, column=0, padx=5, pady=5, sticky="w")
    
    deepl_context_window_options = [
        (0, app.ui_lang.get_label("deepl_context_window_0", "0 (Disabled)")),
        (1, app.ui_lang.get_label("deepl_context_window_1", "1 (Last subtitle)")),
        (2, app.ui_lang.get_label("deepl_context_window_2", "2 (Two subtitles)")),
        (3, app.ui_lang.get_label("deepl_context_window_3", "3 (Three subtitles)"))
    ]
    
    app.deepl_context_window_display_var = tk.StringVar()
    # Set initial display value based on current setting
    current_deepl_context_window = app.deepl_context_window_var.get()
    for value, display in deepl_context_window_options:
        if value == current_deepl_context_window:
            app.deepl_context_window_display_var.set(display)
            break
    else:
        # Fallback if current setting doesn't match any option
        app.deepl_context_window_display_var.set(deepl_context_window_options[2][1])  # Default to 2
    
    app.deepl_context_window_combobox = ttk.Combobox(frame, textvariable=app.deepl_context_window_display_var,
                                                     values=[display for _, display in deepl_context_window_options], 
                                                     width=25, state='readonly')
    app.deepl_context_window_combobox.grid(row=12, column=1, padx=5, pady=5, sticky="ew")
    
    def on_deepl_context_window_changed(event):
        selected_display = app.deepl_context_window_display_var.get()
        # Find the corresponding value
        for value, display in deepl_context_window_options:
            if display == selected_display:
                app.deepl_context_window_var.set(value)
                log_debug(f"DeepL context window changed to: {value} (display: {display})")
                # Clear DeepL context when context window changes
                if hasattr(app, 'translation_handler') and hasattr(app.translation_handler, '_clear_deepl_context'):
                    app.translation_handler._clear_deepl_context()
                if app._fully_initialized:
                    app.save_settings()
                break
    
    app.deepl_context_window_combobox.bind('<<ComboboxSelected>>', 
        create_combobox_handler_wrapper(on_deepl_context_window_changed))

    # Store the options for later use when updating language
    app.deepl_context_window_options = deepl_context_window_options

    # Function to update DeepL model type options when language changes
    def update_deepl_model_type_for_language():
        if hasattr(app, 'deepl_model_type_combobox') and app.deepl_model_type_combobox.winfo_exists():
            from constants import DEEPL_BETA_LANGUAGES
            
            # Get current model type setting
            current_model_type = app.deepl_model_type_var.get()
            
            # Check if either source or target language is a beta language
            is_beta_translation = False
            deepl_source = getattr(app, 'deepl_source_lang', '')
            deepl_target = getattr(app, 'deepl_target_lang', '')
            
            if deepl_source and deepl_source.upper() in DEEPL_BETA_LANGUAGES:
                is_beta_translation = True
                log_debug(f"DeepL source language {deepl_source} is a beta language")
            if deepl_target and deepl_target.upper() in DEEPL_BETA_LANGUAGES:
                is_beta_translation = True
                log_debug(f"DeepL target language {deepl_target} is a beta language")
            
            # Build options based on whether beta languages are involved
            if is_beta_translation:
                # Beta languages only support quality_optimized
                new_deepl_model_options = [
                    ("quality_optimized", app.ui_lang.get_label("deepl_nextgen_model", "Next-gen"))
                ]
                # Force quality_optimized for beta languages
                if current_model_type != "quality_optimized":
                    app.deepl_model_type_var.set("quality_optimized")
                    current_model_type = "quality_optimized"
                    log_debug("Forced model type to quality_optimized for beta language")
            else:
                # Non-beta languages support both models
                new_deepl_model_options = [
                    ("latency_optimized", app.ui_lang.get_label("deepl_classic_model", "Classic")),
                    ("quality_optimized", app.ui_lang.get_label("deepl_nextgen_model", "Next-gen"))
                ]
            
            # Update combobox values
            app.deepl_model_type_combobox['values'] = [display for _, display in new_deepl_model_options]
            
            # Restore selection based on current setting
            for value, display in new_deepl_model_options:
                if value == current_model_type:
                    app.deepl_model_display_var.set(display)
                    break
            else:
                # Fallback to first option if current setting not found
                app.deepl_model_display_var.set(new_deepl_model_options[0][1])
            
            # Update stored options
            app.deepl_model_options = new_deepl_model_options
            
            if is_beta_translation:
                log_debug(f"DeepL model type restricted to Next-gen only (beta language)")
            else:
                log_debug(f"DeepL model type options updated (both Classic and Next-gen available)")
    
    # Store function reference for calling during language updates
    app.update_deepl_model_type_for_language = update_deepl_model_type_for_language

    # Function to update DeepL context window options when language changes
    def update_deepl_context_window_for_language():
        if hasattr(app, 'deepl_context_window_combobox') and app.deepl_context_window_combobox.winfo_exists():
            # Get current context window setting
            current_deepl_context_window = app.deepl_context_window_var.get()
            
            # Update options with new language
            new_deepl_context_window_options = [
                (0, app.ui_lang.get_label("deepl_context_window_0", "0 (Disabled)")),
                (1, app.ui_lang.get_label("deepl_context_window_1", "1 (Last subtitle)")),
                (2, app.ui_lang.get_label("deepl_context_window_2", "2 (Two subtitles)")),
                (3, app.ui_lang.get_label("deepl_context_window_3", "3 (Three subtitles)"))
            ]
            
            # Update combobox values
            app.deepl_context_window_combobox['values'] = [display for _, display in new_deepl_context_window_options]
            
            # Restore selection based on current setting
            for value, display in new_deepl_context_window_options:
                if value == current_deepl_context_window:
                    app.deepl_context_window_display_var.set(display)
                    break
            else:
                # Fallback to default option if current setting not found
                app.deepl_context_window_display_var.set(new_deepl_context_window_options[2][1])  # Default to 2
            
            # Update stored options
            app.deepl_context_window_options = new_deepl_context_window_options
            log_debug(f"Updated DeepL context window options for language change")
    
    # Store function reference for calling during language updates
    app.update_deepl_context_window_for_language = update_deepl_context_window_for_language

    # Function to update Gemini context window options when language changes
    def update_gemini_context_window_for_language():
        if hasattr(app, 'gemini_context_window_combobox') and app.gemini_context_window_combobox.winfo_exists():
            # Get current context window setting
            current_context_window = app.gemini_context_window_var.get()
            
            # Update options with new language
            new_context_window_options = [
                (0, app.ui_lang.get_label("gemini_context_window_0", "0 (Disabled)")),
                (1, app.ui_lang.get_label("gemini_context_window_1", "1 (Last subtitle)")),
                (2, app.ui_lang.get_label("gemini_context_window_2", "2 (Two subtitles)")),
                (3, app.ui_lang.get_label("gemini_context_window_3", "3 (Three subtitles)")),
                (4, app.ui_lang.get_label("gemini_context_window_4", "4 (Four subtitles)")),
                (5, app.ui_lang.get_label("gemini_context_window_5", "5 (Five subtitles)"))
            ]
            
            # Update combobox values
            app.gemini_context_window_combobox['values'] = [display for _, display in new_context_window_options]
            
            # Restore selection based on current setting
            for value, display in new_context_window_options:
                if value == current_context_window:
                    app.gemini_context_window_display_var.set(display)
                    break
            else:
                # Fallback to default option if current setting not found
                app.gemini_context_window_display_var.set(new_context_window_options[1][1])  # Default to 1
            
            log_debug(f"Updated Gemini context window options for language change")
    
    # Store function reference for calling during language updates
    app.update_gemini_context_window_for_language = update_gemini_context_window_for_language

    # Function to update Gemini labels when language changes
    def update_gemini_labels_for_language():
        if hasattr(app, 'gemini_enable_api_log_checkbox') and app.gemini_enable_api_log_checkbox.winfo_exists():
            app.gemini_enable_api_log_checkbox.config(text=app.ui_lang.get_label("gemini_enable_api_log_checkbox", "Enable API Log"))
        if hasattr(app, 'gemini_reset_log_button') and app.gemini_reset_log_button.winfo_exists():
            app.gemini_reset_log_button.config(text=app.ui_lang.get_label("gemini_reset_log_button", "Reset"))
        if hasattr(app, 'gemini_refresh_stats_button') and app.gemini_refresh_stats_button.winfo_exists():
            app.gemini_refresh_stats_button.config(text=app.ui_lang.get_label("gemini_refresh_stats_button", "Refresh"))
        if hasattr(app, 'gemini_total_words_label') and app.gemini_total_words_label.winfo_exists():
            app.gemini_total_words_label.config(text=app.ui_lang.get_label("gemini_total_words_label", "Total Words"))
        if hasattr(app, 'gemini_total_cost_label') and app.gemini_total_cost_label.winfo_exists():
            app.gemini_total_cost_label.config(text=app.ui_lang.get_label("gemini_total_cost_label", "Total Cost"))
        
        # Update cost format when language changes
        if hasattr(app, 'gemini_total_cost_var') and app.gemini_total_cost_var is not None:
            try:
                # Get current cost value and reformat it
                current_value = app.gemini_total_cost_var.get()
                # Parse the current cost regardless of format
                import re
                cost_match = re.search(r'[\d,\.]+', current_value)
                if cost_match:
                    cost_str = cost_match.group().replace(',', '.')  # Normalize to decimal point
                    cost_value = float(cost_str)
                    app.gemini_total_cost_var.set(app.format_cost_for_display(cost_value))
            except Exception as e:
                log_debug(f"Error updating cost format for language change: {e}")
                # Fallback to default formatted value
                app.gemini_total_cost_var.set(app.format_cost_for_display(0.0))
        
        log_debug("Updated Gemini labels for language change")
    
    # Store function reference for calling during language updates
    app.update_gemini_labels_for_language = update_gemini_labels_for_language

    # Function to update DeepL usage labels when language changes
    def update_deepl_usage_for_language():
        if hasattr(app, 'deepl_usage_label') and app.deepl_usage_label.winfo_exists():
            app.deepl_usage_label.config(text=app.ui_lang.get_label("deepl_usage_label", "DeepL Usage"))
        
        # Always refresh DeepL usage display since it's now always visible in API Usage tab
        if hasattr(app, 'update_deepl_usage'):
            app.root.after_idle(app.update_deepl_usage)
        
        log_debug("Updated DeepL usage labels for language change")
    
    # Store function reference for calling during language updates
    app.update_deepl_usage_for_language = update_deepl_usage_for_language

    app.models_file_label = ttk.Label(frame, text=app.ui_lang.get_label("models_file_label")) 
    app.models_file_label.grid(row=14, column=0, padx=5, pady=5, sticky="w")
    app.models_file_frame = ttk.Frame(frame)
    app.models_file_frame.grid(row=14, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
    app.models_file_entry = ttk.Entry(app.models_file_frame, textvariable=app.models_file_var)
    app.models_file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    app.models_file_button = ttk.Button(app.models_file_frame, text=app.ui_lang.get_label("browse_btn"), command=app.browse_marian_models_file)
    app.models_file_button.pack(side=tk.RIGHT, padx=(5,0))

    app.beam_size_label = ttk.Label(frame, text=app.ui_lang.get_label("beam_size_label")) 
    app.beam_size_label.grid(row=15, column=0, padx=5, pady=5, sticky="w")
    app.beam_spinbox = ttk.Spinbox(frame, from_=1, to=50, textvariable=app.num_beams_var, width=10,
                                  validate="key", validatecommand=(validate_beam_size, '%P'))
    app.beam_spinbox.grid(row=15, column=1, padx=5, pady=5, sticky="w")
    def on_beam_spinbox_focus_out(event):
        try:
            value = int(app.num_beams_var.get())
            clamped = max(1, min(50, value))
            if clamped != value: app.num_beams_var.set(clamped)
            app.update_marian_beam_value() 
        except (ValueError, tk.TclError): app.num_beams_var.set(2) 
        app.save_settings() 
    app.beam_spinbox.bind("<FocusOut>", on_beam_spinbox_focus_out)

    app.marian_explanation_labels = [] 
    row_offset = 18  # Adjusted from 15 to account for added OpenAI settings (3 new rows)
    if app.MARIANMT_AVAILABLE:
        texts = [
            app.ui_lang.get_label("marian_beam_explanation", "Higher beam values = better but slower translations"),
            app.ui_lang.get_label("marian_quality_note", "Note: MarianMT provides higher quality translations"),
            app.ui_lang.get_label("marian_quality_vary", "for many language pairs. Quality may vary by language."),
            app.ui_lang.get_label("marian_download_note", "Models are downloaded on first use (requires internet).")
        ]
    else:
        texts = [
            app.ui_lang.get_label("marian_unavailable_line1", "MarianMT is not available. To enable, install:"),
            app.ui_lang.get_label("marian_unavailable_line2", "pip install transformers torch sentencepiece")
        ]
    for i, text_content in enumerate(texts):
        lbl = ttk.Label(frame, text=text_content)
        lbl.grid(row=row_offset + i, column=0, columnspan=3, padx=5, pady=0, sticky="w")
        app.marian_explanation_labels.append(lbl)
    current_row = row_offset + len(texts)

    # Store references to Tesseract-specific widgets for OCR model UI management
    app.tesseract_path_label = ttk.Label(frame, text=app.ui_lang.get_label("tesseract_path_label"))
    app.tesseract_path_label.grid(row=current_row, column=0, padx=5, pady=5, sticky="w")
    app.tesseract_path_frame = ttk.Frame(frame) # Store reference to the frame
    app.tesseract_path_frame.grid(row=current_row, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
    app.tesseract_path_entry = ttk.Entry(app.tesseract_path_frame, textvariable=app.tesseract_path_var) 
    app.tesseract_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    ttk.Button(app.tesseract_path_frame, text=app.ui_lang.get_label("browse_btn"), command=app.browse_tesseract).pack(side=tk.RIGHT, padx=(5,0))
    current_row += 1

    app.keep_linebreaks_label = ttk.Label(frame, text=app.ui_lang.get_label("keep_linebreaks_label", "Keep Linebreaks"))
    app.keep_linebreaks_label.grid(row=current_row, column=0, padx=5, pady=5, sticky="w")
    
    def on_keep_linebreaks_clicked():
        # Schedule focus shift to the parent tab frame (app.tab_settings) to remove dotted focus frame
        if app.keep_linebreaks_checkbox.winfo_exists() and app.tab_settings.winfo_exists():
            app.keep_linebreaks_checkbox.after_idle(app.tab_settings.focus_set)
    
    app.keep_linebreaks_checkbox = ttk.Checkbutton(frame, variable=app.keep_linebreaks_var, command=on_keep_linebreaks_clicked)
    app.keep_linebreaks_checkbox.grid(row=current_row, column=1, padx=5, pady=5, sticky="w")
    current_row += 1

    ttk.Label(frame, text=app.ui_lang.get_label("scan_interval_label")).grid(row=current_row, column=0, padx=5, pady=5, sticky="w") 
    scan_spinbox = ttk.Spinbox(frame, from_=50, to=2000, increment=50, textvariable=app.scan_interval_var, 
                             width=10, validate="key", validatecommand=(validate_scan_interval, '%P'))
    scan_spinbox.grid(row=current_row, column=1, padx=5, pady=5, sticky="w")
    def on_scan_interval_focus_out(event):
        try:
            value = int(app.scan_interval_var.get())
            if not (50 <= value <= 2000): app.scan_interval_var.set(max(50, min(2000, value)))
        except (ValueError, tk.TclError): app.scan_interval_var.set(200)
        app.save_settings()
    scan_spinbox.bind("<FocusOut>", on_scan_interval_focus_out)
    current_row += 1

    ttk.Label(frame, text=app.ui_lang.get_label("clear_timeout_label")).grid(row=current_row, column=0, padx=5, pady=5, sticky="w") 
    timeout_spinbox = ttk.Spinbox(frame, from_=0, to=60, textvariable=app.clear_translation_timeout_var, 
                                width=10, validate="key", validatecommand=(validate_timeout, '%P'))
    timeout_spinbox.grid(row=current_row, column=1, padx=5, pady=5, sticky="w")
    def on_timeout_focus_out(event):
        try:
            value = int(app.clear_translation_timeout_var.get())
            if not (0 <= value <= 60): app.clear_translation_timeout_var.set(max(0, min(60, value)))
            app.clear_translation_timeout = app.clear_translation_timeout_var.get() 
        except (ValueError, tk.TclError): app.clear_translation_timeout_var.set(0)
        app.save_settings()
    timeout_spinbox.bind("<FocusOut>", on_timeout_focus_out)
    current_row += 1
    
    app.stability_label = ttk.Label(frame, text=app.ui_lang.get_label("stability_threshold_label"))
    app.stability_label.grid(row=current_row, column=0, padx=5, pady=5, sticky="w")
    app.stability_spinbox = ttk.Spinbox(frame, from_=0, to=5, textvariable=app.stability_var, 
                                  width=10, validate="key", validatecommand=(validate_stability, '%P'))
    app.stability_spinbox.grid(row=current_row, column=1, padx=5, pady=5, sticky="w")
    def on_stability_focus_out(event):
        try:
            value = int(app.stability_var.get())
            if not (0 <= value <= 5) : app.stability_var.set(max(0, min(5,value)))
            app.update_stability_from_spinbox() 
        except (ValueError, tk.TclError): app.stability_var.set(0)
        app.save_settings()
    app.stability_spinbox.bind("<FocusOut>", on_stability_focus_out)
    current_row += 1

    app.confidence_label = ttk.Label(frame, text=app.ui_lang.get_label("confidence_threshold_label"))
    app.confidence_label.grid(row=current_row, column=0, padx=5, pady=5, sticky="w")
    app.confidence_spinbox = ttk.Spinbox(frame, from_=0, to=100, textvariable=app.confidence_var, 
                                   width=10, validate="key", validatecommand=(validate_confidence, '%P'))
    app.confidence_spinbox.grid(row=current_row, column=1, padx=5, pady=5, sticky="w")
    def on_confidence_focus_out(event):
        try:
            value = int(app.confidence_var.get())
            if not (0 <= value <= 100) : app.confidence_var.set(max(0, min(100, value)))
            app.confidence_threshold = app.confidence_var.get() 
        except (ValueError, tk.TclError): app.confidence_var.set(50)
        app.save_settings()
    app.confidence_spinbox.bind("<FocusOut>", on_confidence_focus_out)
    current_row += 1
    
    app.preprocessing_mode_label = ttk.Label(frame, text=app.ui_lang.get_label("preprocessing_mode_label"))
    app.preprocessing_mode_label.grid(row=current_row, column=0, padx=5, pady=5, sticky="w") 
    
    # Create a display mapping for the preprocessing mode
    preprocessing_values = {
        'none': app.ui_lang.get_label("preprocessing_none", "None"),
        'binary': app.ui_lang.get_label("preprocessing_binary", "Binary"),
        'binary_inv': app.ui_lang.get_label("preprocessing_binary_inv", "Binary Inverted"),
        'adaptive': app.ui_lang.get_label("preprocessing_adaptive", "Adaptive")
    }
    
    # Convert values to list for dropdown
    preprocessing_list = ['none', 'binary', 'binary_inv', 'adaptive']
    
    # Create a custom StringVar for display
    display_var = tk.StringVar()
    
    # Set current display value
    current_value = app.preprocessing_mode_var.get()
    display_var.set(preprocessing_values.get(current_value, preprocessing_values['none']))
    
    # Create combobox with display values
    preprocessing_display_values = [preprocessing_values[val] for val in preprocessing_list]
    app.preprocessing_mode_combobox = ttk.Combobox(frame, textvariable=display_var, 
                                       values=preprocessing_display_values, width=15, state='readonly')
    app.preprocessing_mode_combobox.grid(row=current_row, column=1, padx=5, pady=5, sticky="w")
    
    # Create mapping from display name back to value
    display_to_value = {display: value for value, display in preprocessing_values.items()}
    
    def on_preprocessing_combo_selected(event): 
        # Get selected display value
        selected_display = display_var.get()
        # Map back to actual value
        actual_value = display_to_value.get(selected_display, 'none')
        # Update the actual value
        app.preprocessing_mode_var.set(actual_value)
        app.save_settings()
    
    app.preprocessing_mode_combobox.bind('<<ComboboxSelected>>', 
        create_combobox_handler_wrapper(on_preprocessing_combo_selected))
    current_row += 1

    # Adaptive thresholding parameters (shown only when Adaptive is selected)
    app.adaptive_block_size_label = ttk.Label(frame, text=app.ui_lang.get_label("adaptive_block_size_label", "Block Size"))
    app.adaptive_block_size_label.grid(row=current_row, column=0, padx=5, pady=5, sticky="w")
    app.adaptive_block_size_spinbox = ttk.Spinbox(frame, from_=3, to=101, increment=2, textvariable=app.adaptive_block_size_var, 
                                                 width=10, validate="key", validatecommand=(validate_block_size, '%P'))
    app.adaptive_block_size_spinbox.grid(row=current_row, column=1, padx=5, pady=5, sticky="w")
    def on_block_size_focus_out(event):
        try:
            value = int(app.adaptive_block_size_var.get())
            # Ensure odd number in range
            if value % 2 == 0:
                value += 1  # Make odd
            clamped = max(3, min(101, value))
            if clamped != app.adaptive_block_size_var.get():
                app.adaptive_block_size_var.set(clamped)
        except (ValueError, tk.TclError): 
            app.adaptive_block_size_var.set(41)
        app.save_settings()
    app.adaptive_block_size_spinbox.bind("<FocusOut>", on_block_size_focus_out)
    current_row += 1

    app.adaptive_c_label = ttk.Label(frame, text=app.ui_lang.get_label("adaptive_c_label", "C Value"))
    app.adaptive_c_label.grid(row=current_row, column=0, padx=5, pady=5, sticky="w")
    app.adaptive_c_spinbox = ttk.Spinbox(frame, from_=-75, to=75, textvariable=app.adaptive_c_var, 
                                        width=10, validate="key", validatecommand=(validate_c_value, '%P'))
    app.adaptive_c_spinbox.grid(row=current_row, column=1, padx=5, pady=5, sticky="w")
    def on_c_value_focus_out(event):
        try:
            value = int(app.adaptive_c_var.get())
            clamped = max(-75, min(75, value))
            if clamped != app.adaptive_c_var.get():
                app.adaptive_c_var.set(clamped)
        except (ValueError, tk.TclError): 
            app.adaptive_c_var.set(-60)
        app.save_settings()
    app.adaptive_c_spinbox.bind("<FocusOut>", on_c_value_focus_out)
    current_row += 1

    # Function to show/hide adaptive parameters based on preprocessing mode AND OCR model
    def update_adaptive_fields_visibility():
        mode = app.preprocessing_mode_var.get()
        ocr_model = app.ocr_model_var.get()
        # Adaptive parameters should only be visible when using Tesseract OCR AND adaptive preprocessing
        should_show = (ocr_model == 'tesseract') and (mode == 'adaptive')
        
        if should_show:
            app.adaptive_block_size_label.grid()
            app.adaptive_block_size_spinbox.grid()
            app.adaptive_c_label.grid()
            app.adaptive_c_spinbox.grid()
        else:
            app.adaptive_block_size_label.grid_remove()
            app.adaptive_block_size_spinbox.grid_remove()
            app.adaptive_c_label.grid_remove()
            app.adaptive_c_spinbox.grid_remove()
    
    # Store reference to update function for later use
    app.update_adaptive_fields_visibility = update_adaptive_fields_visibility
    
    # Update the preprocessing combo selection handler to show/hide fields
    original_preprocessing_handler = on_preprocessing_combo_selected
    def on_preprocessing_combo_selected_with_visibility(event):
        original_preprocessing_handler(event)
        update_adaptive_fields_visibility()
    
    # Rebind with new handler
    app.preprocessing_mode_combobox.bind('<<ComboboxSelected>>', 
        create_combobox_handler_wrapper(on_preprocessing_combo_selected_with_visibility))
    
    # Initial visibility update
    update_adaptive_fields_visibility()
    current_row += 1

    # Store references to OCR debugging widgets for OCR model UI management
    app.ocr_debugging_label = ttk.Label(frame, text=app.ui_lang.get_label("ocr_debugging_label"))
    app.ocr_debugging_label.grid(row=current_row, column=0, padx=5, pady=5, sticky="w")
    
    # Create a frame for the OCR debugging checkbox and preview button
    app.ocr_debug_frame = ttk.Frame(frame)
    app.ocr_debug_frame.grid(row=current_row, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
    
    app.ocr_debugging_checkbox = ttk.Checkbutton(app.ocr_debug_frame, text=app.ui_lang.get_label("show_debug_checkbox"), variable=app.ocr_debugging_var)
    app.ocr_debugging_checkbox.pack(side=tk.LEFT)
    
    # Add Preview button
    app.ocr_preview_button = ttk.Button(app.ocr_debug_frame, text=app.ui_lang.get_label("preview_btn", "Preview"), 
               command=app.show_ocr_preview)
    app.ocr_preview_button.pack(side=tk.LEFT, padx=(10,0))
    current_row += 1

    # Store references to Tesseract-specific widgets for OCR model UI management
    app.remove_trailing_label = ttk.Label(frame, text=app.ui_lang.get_label("remove_trailing_label"))
    app.remove_trailing_label.grid(row=current_row, column=0, padx=5, pady=5, sticky="w")
    app.remove_trailing_checkbox = ttk.Checkbutton(frame, text=app.ui_lang.get_label("remove_trailing_checkbox"), variable=app.remove_trailing_garbage_var)
    app.remove_trailing_checkbox.grid(row=current_row, column=1, padx=5, pady=5, sticky="w")
    current_row += 1
    
    color_options = [ 
        (app.ui_lang.get_label("source_color_label"), app.source_colour_var, 'source'),
        (app.ui_lang.get_label("target_color_label"), app.target_colour_var, 'target'),
        (app.ui_lang.get_label("target_text_color_label"), app.target_text_colour_var, 'target_text')
    ]
    app.color_displays = {}
    for i, (label_text, var, color_type) in enumerate(color_options):
        ttk.Label(frame, text=label_text).grid(row=current_row + i, column=0, padx=5, pady=5, sticky="w")
        color_frame_inner = ttk.Frame(frame)
        color_frame_inner.grid(row=current_row + i, column=1, columnspan=2, padx=5, pady=5, sticky="w")
        
        app.color_displays[color_type] = tk.Label(color_frame_inner, width=3, relief="solid", bg=var.get())
        app.color_displays[color_type].pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(color_frame_inner, text=app.ui_lang.get_label("choose_color_btn"), command=lambda ct=color_type: app.choose_color_for_settings(ct)).pack(side=tk.LEFT)
    current_row += len(color_options)

    ttk.Label(frame, text=app.ui_lang.get_label("font_size_label")).grid(row=current_row, column=0, padx=5, pady=5, sticky="w") 
    font_spinbox = ttk.Spinbox(frame, from_=8, to=72, textvariable=app.target_font_size_var, 
                             width=10, validate="key", validatecommand=(validate_font_size, '%P'))
    font_spinbox.grid(row=current_row, column=1, padx=5, pady=5, sticky="w")
    def on_font_size_focus_out(event):
        try:
            value = int(app.target_font_size_var.get())
            if not (8 <= value <= 72): app.target_font_size_var.set(max(8, min(72, value)))
            app.update_target_font_size() 
        except (ValueError, tk.TclError): app.target_font_size_var.set(12)
        app.save_settings()
    font_spinbox.bind("<FocusOut>", on_font_size_focus_out)
    current_row += 1

    # Font type dropdown
    ttk.Label(frame, text=app.ui_lang.get_label("font_type_label")).grid(row=current_row, column=0, padx=5, pady=5, sticky="w")
    font_type_combobox = ttk.Combobox(frame, textvariable=app.target_font_type_var, 
                                    values=get_system_fonts(), width=20, state='readonly')
    font_type_combobox.grid(row=current_row, column=1, padx=5, pady=5, sticky="w")
    
    def on_font_type_change(event):
        app.update_target_font_type()
        if app._fully_initialized:
            app.save_settings()
    font_type_combobox.bind('<<ComboboxSelected>>', create_combobox_handler_wrapper(on_font_type_change))
    current_row += 1
    
    # Opacity controls
    opacity_frame = ttk.Frame(frame)
    opacity_frame.grid(row=current_row, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
    
    ttk.Label(opacity_frame, text=app.ui_lang.get_label("opacity_label", "Opacity:")).grid(row=0, column=0, padx=(0, 10), pady=0, sticky="w")
    
    # Background opacity
    ttk.Label(opacity_frame, text=app.ui_lang.get_label("opacity_background_label", "Background:")).grid(row=0, column=1, padx=(0, 5), pady=0, sticky="w")
    bg_opacity_spinbox = ttk.Spinbox(opacity_frame, from_=0.00, to=1.00, increment=0.05, width=8,
                                   textvariable=app.target_opacity_var, format="%.2f")
    bg_opacity_spinbox.grid(row=0, column=2, padx=(0, 10), pady=0, sticky="w")
    
    # Text opacity  
    ttk.Label(opacity_frame, text=app.ui_lang.get_label("opacity_text_label", "Text:")).grid(row=0, column=3, padx=(0, 5), pady=0, sticky="w")
    text_opacity_spinbox = ttk.Spinbox(opacity_frame, from_=0.00, to=1.00, increment=0.05, width=8,
                                     textvariable=app.target_text_opacity_var, format="%.2f")
    text_opacity_spinbox.grid(row=0, column=4, padx=0, pady=0, sticky="w")
    
    # Bind focus out events to validate and update overlays
    def on_bg_opacity_focus_out(event):
        try:
            value = float(app.target_opacity_var.get())
            if not (0.00 <= value <= 1.00):
                app.target_opacity_var.set(max(0.00, min(1.00, value)))
        except (ValueError, tk.TclError):
            app.target_opacity_var.set(0.15)
        app.update_target_opacity()
        # Note: Settings are saved automatically via trace callback
    
    def on_text_opacity_focus_out(event):
        try:
            value = float(app.target_text_opacity_var.get())
            if not (0.00 <= value <= 1.00):
                app.target_text_opacity_var.set(max(0.00, min(1.00, value)))
        except (ValueError, tk.TclError):
            app.target_text_opacity_var.set(1.0)
        app.update_target_text_opacity()
        # Note: Settings are saved automatically via trace callback
    
    bg_opacity_spinbox.bind("<FocusOut>", on_bg_opacity_focus_out)
    text_opacity_spinbox.bind("<FocusOut>", on_text_opacity_focus_out)
    current_row += 1
    
    file_cache_frame_outer = ttk.LabelFrame(frame, text=app.ui_lang.get_label("file_cache_frame_title")) 
    file_cache_frame_outer.grid(row=current_row, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
    ttk.Label(file_cache_frame_outer, text=app.ui_lang.get_label("file_cache_description"), wraplength=400).grid(row=0, column=0, columnspan=2, padx=5, pady=2, sticky="w")
    ttk.Checkbutton(file_cache_frame_outer, text=app.ui_lang.get_label("google_cache_checkbox"), variable=app.google_file_cache_var).grid(row=1, column=0, padx=5, pady=2, sticky="w")
    ttk.Checkbutton(file_cache_frame_outer, text=app.ui_lang.get_label("deepl_cache_checkbox"), variable=app.deepl_file_cache_var).grid(row=2, column=0, padx=5, pady=2, sticky="w")
    
    # Gemini file cache checkbox (always visible here, not just when Gemini is selected)
    app.gemini_file_cache_checkbox = ttk.Checkbutton(
        file_cache_frame_outer, 
        text=app.ui_lang.get_label("gemini_file_cache_checkbox", "Enable Gemini file cache"),
        variable=app.gemini_file_cache_var,
        command=lambda: [
            log_debug(f"Gemini file cache toggled: {app.gemini_file_cache_var.get()}"),
            app._fully_initialized and app.save_settings()
        ]
    )
    app.gemini_file_cache_checkbox.grid(row=3, column=0, padx=5, pady=2, sticky="w")
    
    # OpenAI file cache checkbox (always visible here, not just when OpenAI is selected)
    app.openai_file_cache_checkbox = ttk.Checkbutton(
        file_cache_frame_outer, 
        text=app.ui_lang.get_label("openai_file_cache_checkbox", "Enable OpenAI file cache"),
        variable=app.openai_file_cache_var,
        command=lambda: [
            log_debug(f"OpenAI file cache toggled: {app.openai_file_cache_var.get()}"),
            app._fully_initialized and app.save_settings()
        ]
    )
    app.openai_file_cache_checkbox.grid(row=4, column=0, padx=5, pady=2, sticky="w")
    
    ttk.Label(file_cache_frame_outer, text=f"{app.ui_lang.get_label('cache_files_label')} {os.path.basename(app.google_cache_file)}, {os.path.basename(app.deepl_cache_file)}, {os.path.basename(app.gemini_cache_file)}, openai_cache.txt", wraplength=400).grid(row=5, column=0, columnspan=2, padx=5, pady=2, sticky="w")
    ttk.Button(file_cache_frame_outer, text=app.ui_lang.get_label("clear_caches_btn"), command=app.clear_file_caches).grid(row=6, column=0, padx=5, pady=5, sticky="w")
    current_row += 1
    
    button_frame_outer = ttk.Frame(frame)
    button_frame_outer.grid(row=current_row, column=0, columnspan=3, pady=10)
    save_settings_button = ttk.Button(button_frame_outer, text=app.ui_lang.get_label("save_settings_btn"), command=app.save_settings)
    save_settings_button.pack(side=tk.LEFT, padx=5)
    
    # Store reference for the tab changed handler in app_logic.py
    app.settings_tab_save_button = save_settings_button
    
    frame.columnconfigure(1, weight=1)

def create_api_usage_tab(app):
    """Create the API Usage tab with provider-specific statistics."""
    scrollable_content = create_scrollable_tab(app.tab_control, app.ui_lang.get_label("api_usage_tab_title"))
    app.tab_api_usage = scrollable_content
    
    frame = ttk.LabelFrame(scrollable_content, text=app.ui_lang.get_label("api_usage_tab_title"))
    frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    current_row = 0

    def create_stats_section(parent, provider, type, stats_keys, row_start):
        section_key = f"api_usage_section_{provider.lower()}_{type.lower()}"
        fallback_text = f"📊 {provider} {type} Statistics"
        section = ttk.LabelFrame(parent, text=app.ui_lang.get_label(section_key, fallback_text))
        section.grid(row=row_start, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        labels_attr = f"{provider.lower()}_{type.lower()}_stat_labels"
        vars_attr = f"{provider.lower()}_{type.lower()}_stat_vars"
        setattr(app, labels_attr, {})
        setattr(app, vars_attr, {})

        for i, (key, fallback) in enumerate(stats_keys):
            label = ttk.Label(section, text=app.ui_lang.get_label(key, fallback))
            label.grid(row=i, column=0, padx=5, pady=2, sticky="w")
            getattr(app, labels_attr)[key] = label
            
            var = tk.StringVar(value=app.ui_lang.get_label("api_usage_no_data", "No data available"))
            value_label = ttk.Label(section, textvariable=var, foreground="blue")
            value_label.grid(row=i, column=1, padx=5, pady=2, sticky="w")
            getattr(app, vars_attr)[key] = var
        
        section.columnconfigure(1, weight=1)
        return row_start + 1

    trans_keys = [
        ("api_usage_total_translation_calls", "Total Translation Calls"), ("api_usage_total_words_translated", "Total Words Translated"),
        ("api_usage_median_duration_translation", "Median Duration"), ("api_usage_words_per_minute", "Average Words per Minute"),
        ("api_usage_avg_cost_per_word", "Average Cost per Word"), ("api_usage_avg_cost_per_call", "Average Cost per Call"),
        ("api_usage_avg_cost_per_minute", "Average Cost per Minute"), ("api_usage_avg_cost_per_hour", "Average Cost per Hour"),
        ("api_usage_total_translation_cost", "Total Translation Cost")
    ]
    ocr_keys = [
        ("api_usage_total_ocr_calls", "Total OCR Calls"), ("api_usage_median_duration_ocr", "Median Duration"),
        ("api_usage_avg_cost_per_call", "Average Cost per Call"), ("api_usage_avg_cost_per_minute", "Average Cost per Minute"),
        ("api_usage_avg_cost_per_hour", "Average Cost per Hour"), ("api_usage_total_ocr_cost", "Total OCR Cost")
    ]
    combined_keys = [
        ("api_usage_combined_cost_per_minute", "Combined Cost per Minute"), ("api_usage_combined_cost_per_hour", "Combined Cost per Hour"),
        ("api_usage_total_api_cost", "Total API Cost")
    ]

    current_row = create_stats_section(frame, "Gemini", "Translation", trans_keys, current_row)
    current_row = create_stats_section(frame, "Gemini", "OCR", ocr_keys, current_row)
    current_row = create_stats_section(frame, "Gemini", "Combined", combined_keys, current_row)
    
    current_row = create_stats_section(frame, "OpenAI", "Translation", trans_keys, current_row)
    current_row = create_stats_section(frame, "OpenAI", "OCR", ocr_keys, current_row)
    current_row = create_stats_section(frame, "OpenAI", "Combined", combined_keys, current_row)
    
    deepl_section = ttk.LabelFrame(frame, text=app.ui_lang.get_label("api_usage_section_deepl"))
    deepl_section.grid(row=current_row, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
    app.deepl_usage_label = ttk.Label(deepl_section, text=app.ui_lang.get_label("deepl_usage_label", "DeepL Usage"))
    app.deepl_usage_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
    app.deepl_usage_var = tk.StringVar(value=app.ui_lang.get_label("deepl_usage_loading", "Loading..."))
    app.deepl_usage_display = ttk.Label(deepl_section, textvariable=app.deepl_usage_var, foreground="blue")
    app.deepl_usage_display.grid(row=0, column=1, padx=5, pady=5, sticky="w")
    deepl_section.columnconfigure(1, weight=1)
    current_row += 1
    
    button_frame = ttk.Frame(frame)
    button_frame.grid(row=current_row, column=0, columnspan=2, padx=5, pady=10, sticky="ew")
    
    app.refresh_stats_button = ttk.Button(button_frame, 
                                        text=app.ui_lang.get_label("api_usage_refresh_btn", "Refresh Statistics"),
                                        command=app.refresh_api_statistics)
    app.refresh_stats_button.pack(side=tk.LEFT, padx=5)
    
    app.export_csv_button = ttk.Button(button_frame,
                                     text=app.ui_lang.get_label("api_usage_export_csv_btn", "Export to CSV"),
                                     command=app.export_statistics_csv)
    app.export_csv_button.pack(side=tk.LEFT, padx=5)
    
    app.export_text_button = ttk.Button(button_frame,
                                      text=app.ui_lang.get_label("api_usage_export_text_btn", "Export to Text"),
                                      command=app.export_statistics_text)
    app.export_text_button.pack(side=tk.LEFT, padx=5)
    
    app.copy_stats_button = ttk.Button(button_frame,
                                     text=app.ui_lang.get_label("api_usage_copy_btn", "Copy"),
                                     command=app.copy_statistics_to_clipboard)
    app.copy_stats_button.pack(side=tk.LEFT, padx=5)
    current_row += 1
    
    info_frame = ttk.Frame(frame)
    info_frame.grid(row=current_row, column=0, columnspan=2, padx=5, pady=(10, 5), sticky="ew")
    
    app.api_usage_info_label = ttk.Label(info_frame, 
                                        text=app.ui_lang.get_label("api_usage_info_note", 
                                            "ℹ️ Note: Statistics are based on the short log files (e.g., Gemini_OCR_Short_Log.txt). Data will be reset if these files are deleted or cleared."),
                                        foreground="gray", 
                                        justify=tk.LEFT, wraplength=600)
    app.api_usage_info_label.pack(anchor="w", fill="x", padx=5, pady=2)
    
    def update_info_label_wraplength(event=None):
        if hasattr(app, 'api_usage_info_label') and app.api_usage_info_label.winfo_exists():
            try:
                frame_width = info_frame.winfo_width()
                if frame_width > 100:
                    new_wraplength = max(200, frame_width - 20)
                    app.api_usage_info_label.config(wraplength=new_wraplength)
            except Exception as e:
                pass
    
    info_frame.bind('<Configure>', update_info_label_wraplength)
    app.update_info_label_wraplength = update_info_label_wraplength
    
    def update_api_usage_info_for_language():
        if hasattr(app, 'api_usage_info_label') and app.api_usage_info_label.winfo_exists():
            app.api_usage_info_label.config(text=app.ui_lang.get_label("api_usage_info_note", 
                "ℹ️ Note: Statistics are based on the short log files (e.g., Gemini_OCR_Short_Log.txt). Data will be reset if these files are deleted or cleared."))
            app.root.after_idle(update_info_label_wraplength)
        log_debug("Updated API usage info label for language change")
    
    app.update_api_usage_info_for_language = update_api_usage_info_for_language
    
    frame.columnconfigure(0, weight=1)
    frame.columnconfigure(1, weight=1)
    
    app.root.after_idle(lambda: app._delayed_api_stats_refresh() if hasattr(app, '_delayed_api_stats_refresh') else None)

def create_debug_tab(app):
    # Create a scrollable tab content frame
    scrollable_content = create_scrollable_tab(app.tab_control, app.ui_lang.get_label("debug_tab_title"))
    app.tab_debug = scrollable_content
    
    # Create the debug frame inside the scrollable area
    frame = ttk.LabelFrame(scrollable_content, text=app.ui_lang.get_label("debug_tab_title"))
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    image_frame = ttk.Frame(frame)
    image_frame.pack(fill="x", padx=5, pady=5)

    original_frame = ttk.LabelFrame(image_frame, text=app.ui_lang.get_label("original_image_label"))
    original_frame.pack(side=tk.LEFT, padx=5, fill="both", expand=True)
    app.original_image_label = ttk.Label(original_frame, text=app.ui_lang.get_label("no_image_captured", "No image captured yet"))
    app.original_image_label.pack(padx=5, pady=5)

    processed_frame = ttk.LabelFrame(image_frame, text=app.ui_lang.get_label("processed_image_label"))
    processed_frame.pack(side=tk.RIGHT, padx=5, fill="both", expand=True)
    app.processed_image_label = ttk.Label(processed_frame, text=app.ui_lang.get_label("no_image_processed", "No image processed yet"))
    app.processed_image_label.pack(padx=5, pady=5)

    ocr_frame = ttk.LabelFrame(frame, text=app.ui_lang.get_label("ocr_results_label"))
    ocr_frame.pack(fill="x", padx=5, pady=5)  # Remove expand=True
    app.ocr_results_text = tk.Text(ocr_frame, height=16, width=50, wrap=tk.WORD)
    app.ocr_results_text.pack(fill="both", expand=True, padx=5, pady=5)
    app.ocr_results_text.insert(tk.END, app.ui_lang.get_label("ocr_results_placeholder"))
    app.ocr_results_text.config(state=tk.DISABLED)

    button_frame = ttk.Frame(frame) # Renamed to avoid conflict
    button_frame.pack(fill="x", padx=5, pady=5)
    ttk.Button(button_frame, text=app.ui_lang.get_label("save_debug_images_btn"), command=app.save_debug_images).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text=app.ui_lang.get_label("refresh_log_btn"), command=app.refresh_debug_log).pack(side=tk.LEFT, padx=5)

    log_frame = ttk.LabelFrame(frame, text=app.ui_lang.get_label("app_log_label"))
    log_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Create text widget without fixed height to allow expansion
    app.log_text = tk.Text(log_frame, wrap=tk.WORD)
    
    # Add scrollbar
    scrollbar = ttk.Scrollbar(log_frame, command=app.log_text.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    app.log_text.config(yscrollcommand=scrollbar.set, state=tk.DISABLED)
    
    # Pack the text widget to fill the frame
    app.log_text.pack(fill="both", expand=True, padx=5, pady=5)
    
    app.refresh_debug_log()

def create_custom_prompt_tab(app):
    # Create a scrollable tab content frame
    scrollable_content = create_scrollable_tab(app.tab_control, app.ui_lang.get_label("custom_prompt_tab_title", "Custom Prompt"))
    app.tab_custom_prompt = scrollable_content
    
    # Create the main frame inside the scrollable area
    frame = ttk.LabelFrame(scrollable_content, text=app.ui_lang.get_label("custom_prompt_tab_title", "Custom Prompt"))
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Info label
    info_text = app.ui_lang.get_label("custom_prompt_info", "This text will be added at the beginning of the translation instruction for Gemini and OpenAI models.")
    info_label = ttk.Label(frame, text=info_text, wraplength=550)
    info_label.pack(fill="x", padx=5, pady=5)

    # Text area
    text_frame = ttk.Frame(frame)
    text_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    app.custom_prompt_text_widget = tk.Text(text_frame, wrap=tk.WORD, height=15)
    scrollbar = ttk.Scrollbar(text_frame, command=app.custom_prompt_text_widget.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    app.custom_prompt_text_widget.pack(side=tk.LEFT, fill="both", expand=True)
    app.custom_prompt_text_widget.config(yscrollcommand=scrollbar.set)
    
    # Load initial text
    if hasattr(app, "custom_prompt_text"):
        app.custom_prompt_text_widget.insert("1.0", app.custom_prompt_text)

    # Buttons
    button_frame = ttk.Frame(frame)
    button_frame.pack(fill="x", padx=5, pady=10)

    def save_prompt():
        text = app.custom_prompt_text_widget.get("1.0", "end-1c")
        if not app.save_custom_prompt(text):
            messagebox.showerror(app.ui_lang.get_label("error_title", "Error"), 
                                 app.ui_lang.get_label("custom_prompt_save_error", "Failed to save custom prompt."))

    def reload_prompt():
        app.load_custom_prompt()
        app.custom_prompt_text_widget.delete("1.0", tk.END)
        app.custom_prompt_text_widget.insert("1.0", app.custom_prompt_text)

    app.save_custom_prompt_btn = ttk.Button(button_frame, text=app.ui_lang.get_label("save_btn", "Save"), command=save_prompt)
    app.save_custom_prompt_btn.pack(side=tk.LEFT, padx=5)

    app.reload_custom_prompt_btn = ttk.Button(button_frame, text=app.ui_lang.get_label("reload_btn", "Reload"), command=reload_prompt)
    app.reload_custom_prompt_btn.pack(side=tk.LEFT, padx=5)
    
    # Function to update labels on language change
    def update_custom_prompt_labels_for_language():
        if hasattr(app, 'tab_custom_prompt') and app.tab_custom_prompt.winfo_exists():
            try:
                frame.config(text=app.ui_lang.get_label("custom_prompt_tab_title", "Custom Prompt"))
                info_label.config(text=app.ui_lang.get_label("custom_prompt_info", "This text will be added at the beginning of the translation instruction for Gemini and OpenAI models."))
                app.save_custom_prompt_btn.config(text=app.ui_lang.get_label("save_btn", "Save"))
                app.reload_custom_prompt_btn.config(text=app.ui_lang.get_label("reload_btn", "Reload"))
            except Exception as e:
                log_debug(f"Error updating custom prompt UI language: {e}")
                
    app.update_custom_prompt_labels_for_language = update_custom_prompt_labels_for_language

