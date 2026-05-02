from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLineEdit
# handlers/ui_interaction_handler.py
import os
import time
import re
import qt_dialogs as messagebox
import qt_dialogs as colorchooser
import cv2 
from PIL import Image 
from config_manager import save_app_config, SIMPLE_CONFIG_SETTINGS
from logger import log_debug
import traceback

# Open-source edition: PRO features are always disabled
def is_pro_active():
    return False


class UIInteractionHandler:
    def __init__(self, app):
        self.app = app
        self._save_in_progress = False
        self._last_save_time = 0
        self._save_debounce_interval = 0.1  # 100ms debounce

    def choose_color_for_settings(self, color_type):
        """No-op in open-source edition (colour pickers are PRO)."""
        pass

    def toggle_api_key_visibility(self, api_type_toggle):
        target_entry, target_button, visibility_flag_attr = None, None, None
        if api_type_toggle == "deepl":
            target_entry, target_button, visibility_flag_attr = self.app.deepl_api_key_entry, self.app.deepl_api_key_button, "deepl_api_key_visible"
        elif api_type_toggle == "gemini":
            target_entry, target_button, visibility_flag_attr = self.app.gemini_api_key_entry, self.app.gemini_api_key_button, "gemini_api_key_visible"

        if target_entry and target_button:
            current_visibility = getattr(self.app, visibility_flag_attr, False)
            new_visibility = not current_visibility
            setattr(self.app, visibility_flag_attr, new_visibility)
            target_entry.setEchoMode(QLineEdit.Normal if new_visibility else QLineEdit.Password)

            # Use the language system for button text
            if new_visibility:
                button_text = self.app.ui_lang.get_label("hide_btn", "Hide")
            else:
                button_text = self.app.ui_lang.get_label("show_btn", "Show")

            target_button.setText(button_text)
            log_debug(f"API key visibility for {api_type_toggle} changed to {new_visibility}, button text: {button_text}")

    def update_translation_model_ui(self):
        selected_model_ui_code = self.app.translation_model 
        log_debug(f"Updating UI visibility for model code: {selected_model_ui_code}")

        is_deepl = (selected_model_ui_code == 'deepl_api')
        is_gemini = (selected_model_ui_code == 'gemini_api')
        is_api_model = is_deepl or is_gemini

        # Manage visibility using setVisible for PySide6 widgets
        if hasattr(self.app, 'keep_linebreaks_check'):
            self.app.keep_linebreaks_check.setVisible(True)

        # We need to handle labels and inputs in the new GUI
        if hasattr(self.app, 'gui') and self.app.gui:
            g = self.app.gui
            if hasattr(g, 'models_form_layout'):
                g.models_form_layout.setRowVisible(2, is_gemini)  # Gemini Context
                g.models_form_layout.setRowVisible(3, is_deepl)   # DeepL Context

            # Language labels and combos are always visible in the new GUI
            g.lbl_source_lang.setVisible(is_api_model)
            g.source_lang_combo.setVisible(is_api_model)
            g.lbl_target_lang.setVisible(is_api_model)
            g.target_lang_combo.setVisible(is_api_model)

            g.lbl_gemini_key.setVisible(is_gemini)
            g.gemini_api_key_entry.setVisible(is_gemini)
            g.lbl_deepl_key.setVisible(is_deepl)
            g.deepl_api_key_entry.setVisible(is_deepl)

        # Update statistics when respective models are selected
        if is_gemini and hasattr(self.app, 'update_gemini_stats'):
            QTimer.singleShot(0, self.app.update_gemini_stats)

        if is_deepl and hasattr(self.app, 'update_deepl_usage'):
            QTimer.singleShot(0, self.app.update_deepl_usage)

    def update_ocr_model_ui(self):
        """Update UI visibility for OCR model-specific settings."""
        # Only Gemini OCR is currently supported, so UI is static.
        pass


    def update_all_dropdowns_for_language_change(self):
        """Update all language dropdowns when UI language changes."""
        try:
            # Start comprehensive UI update
            self.app.start_ui_update()

            ui_language_for_lookup = self.get_current_ui_language_for_lookup()

            log_debug(f"Updating dropdowns for language change - UI language: {ui_language_for_lookup}")

            # Preserve current selections
            current_deepl_source = self.app.deepl_source_lang
            current_deepl_target = self.app.deepl_target_lang
            current_gemini_source = self.app.gemini_source_lang
            current_gemini_target = self.app.gemini_target_lang

            # Update API language dropdowns
            active_model = self.app.translation_model
            if active_model in ['deepl_api', 'gemini_api']:
                self._update_language_dropdowns_for_model(active_model)

            # Restore selections if needed
            if self.app.deepl_source_lang != current_deepl_source:
                self.app.deepl_source_lang = current_deepl_source
            if self.app.deepl_target_lang != current_deepl_target:
                self.app.deepl_target_lang = current_deepl_target
            if self.app.gemini_source_lang != current_gemini_source:
                self.app.gemini_source_lang = current_gemini_source
            if self.app.gemini_target_lang != current_gemini_target:
                self.app.gemini_target_lang = current_gemini_target

            log_debug(f"Updated all dropdowns for UI language change to: {self.app.ui_lang.current_lang}")

        except Exception as e:
            log_debug(f"Error updating dropdowns for language change: {e}\n{traceback.format_exc()}")
        finally:
            self.app.end_ui_update()

    def get_current_ui_language_for_lookup(self):
        """Get the current UI language in the format expected by localization methods."""
        current_ui_language = self.app.ui_lang.current_lang
        ui_language_for_lookup = 'polish' if current_ui_language == 'pol' else 'english'
        return ui_language_for_lookup

    def _update_language_dropdowns_for_model(self, active_model_code):
        lm = self.app.language_manager
        ui_language_for_lookup = self.get_current_ui_language_for_lookup()
        
        def sort_pairs(pairs_list):
            def get_sort_key(item):
                name = item[0]
                return "" if name == "Auto" else name.lower()
            return sorted(pairs_list, key=get_sort_key)

        source_pairs = []
        detect_lbl = self.app.ui_lang.get_label('detect_language', '< Detect language >')
        if active_model_code == 'deepl_api':
            for _, code in lm.deepl_source_languages:
                name = detect_lbl if code == 'auto' else lm.get_localized_language_name(code, 'deepl', ui_language_for_lookup)
                source_pairs.append((name, code))
            current_source_api_code = self.app.deepl_source_lang
        elif active_model_code == 'gemini_api':
            for _, code in lm.gemini_source_languages:
                name = detect_lbl if code == 'auto' else lm.get_localized_language_name(code, 'gemini', ui_language_for_lookup)
                source_pairs.append((name, code))
            current_source_api_code = self.app.gemini_source_lang

        source_pairs = sort_pairs(source_pairs)

        target_pairs = []
        if active_model_code == 'deepl_api':
            for _, code in lm.deepl_target_languages:
                name = lm.get_localized_language_name(code, 'deepl', ui_language_for_lookup)
                target_pairs.append((name, code))
            current_target_api_code = self.app.deepl_target_lang
        elif active_model_code == 'gemini_api':
            for _, code in lm.gemini_target_languages:
                name = lm.get_localized_language_name(code, 'gemini', ui_language_for_lookup)
                target_pairs.append((name, code))
            current_target_api_code = self.app.gemini_target_lang
            
        target_pairs = sort_pairs(target_pairs)

        # Update GUI combos directly via MainWindow reference
        if hasattr(self.app, 'gui') and self.app.gui:
            g = self.app.gui
            
            g.source_lang_combo.clear()
            for name, code in source_pairs:
                g.source_lang_combo.addItem(name, code)

            idx_src = g.source_lang_combo.findData(current_source_api_code)
            if idx_src >= 0: g.source_lang_combo.setCurrentIndex(idx_src)

            g.target_lang_combo.clear()
            for name, code in target_pairs:
                g.target_lang_combo.addItem(name, code)
                
            idx_tgt = g.target_lang_combo.findData(current_target_api_code)
            if idx_tgt >= 0: g.target_lang_combo.setCurrentIndex(idx_tgt)

            g.synchronize_language_combo_widths()

    def on_translation_model_selection_changed(self, event=None, initial_setup=False):
        try:
            if not initial_setup:
                self.app.start_ui_update()

            if event is not None and hasattr(self.app, 'gui') and self.app.gui:
                selected_display_name = self.app.gui.translation_model_combo.currentText()

                new_model_code = 'gemini_api'
                if selected_display_name == 'DeepL API':
                    new_model_code = 'deepl_api'
                else:
                    self.app.gemini_translation_model = selected_display_name

                previous_model = self.app.translation_model
                if new_model_code != previous_model:
                    if (hasattr(self.app, 'translation_handler') and 
                        hasattr(self.app.translation_handler, '_clear_active_context')):
                        self.app.translation_handler._clear_active_context()

                    self.app.translation_model = new_model_code

            self.update_translation_model_ui() 
            if self.app.translation_model in ['deepl_api', 'gemini_api']:
                self._update_language_dropdowns_for_model(self.app.translation_model)

        finally:
            if not initial_setup:
                self.app.end_ui_update()


    def update_target_font_size(self):
        if self.app.translation_text :
            try:
                font_size = self.app.target_font_size
                font_type = self.app.target_font_type
                self.app.translation_text.update_text_style(font_family=font_type, font_size=font_size)
            except Exception: pass

    def update_target_font_type(self):
        if self.app.translation_text :
            try:
                font_size = self.app.target_font_size
                font_type = self.app.target_font_type
                self.app.translation_text.update_text_style(font_family=font_type, font_size=font_size)
            except Exception: pass

    def update_target_opacity(self):
        """Update the background opacity of the translation overlay"""
        if self.app.target_overlay :
            try:
                if hasattr(self.app.target_overlay, 'update_color'):
                    self.app.target_overlay.update_color(self.app.target_colour, self.app.target_opacity)
            except Exception as e:
                log_debug(f"Error updating target opacity: {e}")

    def update_target_text_opacity(self):
        """Update the text opacity of the translation overlay"""
        if self.app.target_overlay :
            try:
                if hasattr(self.app.target_overlay, 'update_text_color'):
                    self.app.target_overlay.update_text_color(self.app.target_text_colour)
            except Exception as e:
                log_debug(f"Error updating target text opacity: {e}")

    def refresh_debug_log(self):
        # In PySide version, debug log refresh is handled via signal-driven updates
        # rather than manual polling of a text widget.
        pass

    def save_debug_images(self):
        try:
            if self.app.last_screenshot is None:
                messagebox.showinfo("Debug", "No screenshot captured."); return
            debug_dir = "debug_images"; os.makedirs(debug_dir, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            original_fn = os.path.join(debug_dir, f"original_{ts}.png")
            self.app.last_screenshot.save(original_fn)
            if hasattr(self.app, 'last_processed_image') and self.app.last_processed_image is not None:
                processed_fn = os.path.join(debug_dir, f"processed_{ts}.png")
                cv2.imwrite(processed_fn, self.app.last_processed_image)

            messagebox.showinfo(
                self.app.ui_lang.get_label("dialog_debug_images_saved_title", "Debug Images Saved"), 
                self.app.ui_lang.get_label("dialog_debug_images_saved_message", "Images saved to '{0}'.").format(debug_dir)
            )
        except Exception as e:
            log_debug(f"Error saving debug images: {e}")
            messagebox.showerror("Error", f"Failed to save debug images: {e}")

    def save_settings(self):
        current_time = time.time()
        if self._save_in_progress or (current_time - self._last_save_time < self._save_debounce_interval):
            return True

        self._last_save_time = current_time
        self._save_in_progress = True
        try:
            cfg = self.app.config['Settings']
            is_simple = (getattr(self.app, 'config_mode', 'Advanced') == 'Simple')
            is_pro = is_pro_active()

            # Keys that require PRO licence to persist custom values
            PRO_LOCKED_KEYS = {
                'source_area_colour', 'target_area_colour', 'target_text_colour',
                'translation_model', 'auto_detect_enabled', 'target_on_source_enabled',
                'capture_padding_enabled', 'custom_ocr_prompt_enabled',
            }
            
            def set_cfg(key, value):
                """Write to cfg only if not locked by Simple mode or PRO restriction."""
                if is_simple and key in SIMPLE_CONFIG_SETTINGS:
                    return  # Preserve user's Advanced value in ini
                if not is_pro and key in PRO_LOCKED_KEYS:
                    return  # Preserve user's saved value - don't overwrite with locked defaults
                cfg[key] = value
            
            # Always save config_mode itself
            cfg['config_mode'] = getattr(self.app, 'config_mode', 'Advanced')
            
            set_cfg('translation_model', self.app.translation_model)
            set_cfg('deepl_source_lang', self.app.deepl_source_lang)
            cfg['deepl_target_lang'] = self.app.deepl_target_lang  # Always save (not locked)
            set_cfg('gemini_source_lang', self.app.gemini_source_lang)
            cfg['gemini_target_lang'] = self.app.gemini_target_lang  # Always save (not locked)
            set_cfg('scan_interval', str(self.app.scan_interval))
            set_cfg('clear_translation_timeout', str(self.app.clear_translation_timeout))
            set_cfg('source_area_colour', self.app.source_colour)
            set_cfg('target_area_colour', self.app.target_colour)
            set_cfg('target_text_colour', self.app.target_text_colour)
            set_cfg('target_font_size', str(self.app.target_font_size))
            set_cfg('target_font_type', self.app.target_font_type)
            set_cfg('target_opacity', str(self.app.target_opacity))
            set_cfg('target_text_opacity', str(self.app.target_text_opacity))
            cfg['gui_language'] = self.app.gui_language  # Always save (not locked)
            set_cfg('ocr_model', self.app.ocr_model)
            cfg['check_for_updates_on_startup'] = 'yes' if self.app.check_for_updates_on_startup else 'no'
            set_cfg('auto_detect_enabled', str(self.app.auto_detect_enabled))
            set_cfg('target_on_source_enabled', str(self.app.target_on_source_enabled))
            set_cfg('capture_padding_enabled', str(self.app.capture_padding_enabled))
            set_cfg('capture_padding', str(self.app.capture_padding))
            cfg['discovery_timeout'] = str(self.app.discovery_timeout)  # Always save (not locked)
            cfg['deepl_api_key'] = self.app.deepl_api_key  # Always save (not locked)
            cfg['deepl_context_window'] = str(self.app.deepl_context_window)  # Always save (not locked)
            cfg['gemini_api_key'] = self.app.gemini_api_key  # Always save (not locked)
            set_cfg('gemini_context_window', str(self.app.gemini_context_window))
            set_cfg('deepl_file_cache', str(self.app.deepl_cache_enabled))
            set_cfg('gemini_file_cache', str(self.app.gemini_cache_enabled))
            set_cfg('gemini_api_log_enabled', str(self.app.gemini_api_log_enabled))
            set_cfg('keep_linebreaks', str(self.app.keep_linebreaks))
            set_cfg('debug_logging_enabled', str(self.app.debug_logging_enabled))
            set_cfg('gemini_translation_model', self.app.gemini_translation_model)
            set_cfg('gemini_ocr_model', self.app.gemini_ocr_model)
            set_cfg('custom_prompt_enabled', str(self.app.custom_prompt_enabled))
            set_cfg('custom_ocr_prompt_enabled', str(self.app.custom_ocr_prompt_enabled))
            
            # Save UI visibility mode
            cfg['ui_visibility_mode'] = getattr(self.app, 'ui_visibility_mode', 'Show')
            cfg['top_visibility_mode'] = getattr(self.app, 'top_visibility_mode', 'Show')
            
            # Save Window Geometry (if available) - Normalized by scale_factor
            if hasattr(self.app, 'gui') and self.app.gui:
                sf = self.app.gui.scale_factor
                pos = self.app.gui.pos()
                geom = self.app.gui.geometry()
                cfg['window_x'] = str(round(pos.x() / sf))
                cfg['window_y'] = str(round(pos.y() / sf))
                cfg['window_width'] = str(round(geom.width() / sf))
                # Only save height if we are currently in Show mode, to avoid saving compact height
                if getattr(self.app, 'ui_visibility_mode', 'Show') == 'Show':
                    cfg['window_height_show'] = str(round(geom.height() / sf))


            if self.app.source_overlay:
                area = self.app.source_overlay.get_geometry()
                if area: cfg['source_area_x1'], cfg['source_area_y1'], \
                         cfg['source_area_x2'], cfg['source_area_y2'] = map(str, area)
                cfg['source_area_visible'] = str(self.app.source_overlay.isVisible())
            if self.app.target_overlay:
                area = self.app.target_overlay.get_geometry()
                if area: cfg['target_area_x1'], cfg['target_area_y1'], \
                         cfg['target_area_x2'], cfg['target_area_y2'] = map(str, area)
                cfg['target_area_visible'] = str(self.app.target_overlay.isVisible())

            if not save_app_config(self.app.config): return False

            if hasattr(self.app, 'status_label') and self.app.status_label:
                self.app.status_label.setText(self.app.ui_lang.get_label("settings_saved", "Status: Settings Saved"))
            return True
        except Exception as e:
             log_debug(f"Error saving settings: {e}\n{traceback.format_exc()}")
             return False
        finally:
            self._save_in_progress = False

    def clear_debug_log(self):
        try:
            log_filename = 'translator_debug.log' 
            with open(log_filename, 'w', encoding='utf-8-sig') as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Debug log cleared by user.\n")
            if hasattr(self.app, 'status_label') and self.app.status_label:
                self.app.status_label.setText("Status: Debug log cleared")
        except Exception as e:
            log_debug(f"Error clearing debug log: {e}")