from PySide6.QtCore import QMetaObject, Qt
from logger import log_debug

class HotkeyHandler:
    """Handles keyboard shortcuts and hotkey registration"""
    
    def __init__(self, app):
        """Initialize with a reference to the main application
        
        Args:
            app: The main GameChangingTranslator application instance
        """
        self.app = app
    
    def setup_hotkeys(self):
        """Registers all keyboard shortcuts if the keyboard module is available"""
        if self.app.KEYBOARD_AVAILABLE:
            try:
                # We need to explicitly import keyboard here since it's optional
                import keyboard
                
                # Add suppress=True to ensure hotkeys work when app is not in focus
                keyboard.add_hotkey('`', self.toggle_translation_hotkey, suppress=True)
                keyboard.add_hotkey('~', self.toggle_translation_hotkey, suppress=True)
                keyboard.add_hotkey('alt+1', self.toggle_source_visibility_hotkey, suppress=True)
                keyboard.add_hotkey('alt+2', self.toggle_target_visibility_hotkey, suppress=True)
                keyboard.add_hotkey('alt+s', self.save_settings_hotkey, suppress=True)
                keyboard.add_hotkey('alt+f', self.clear_file_caches_hotkey, suppress=True)
                keyboard.add_hotkey('alt+t', self.clear_cache_hotkey, suppress=True)
                keyboard.add_hotkey('alt+d', self.clear_debug_log_hotkey, suppress=True)
                keyboard.add_hotkey('alt+r', self.reset_window_geometry_hotkey, suppress=True)
                keyboard.add_hotkey('alt+l', self.take_screenshot_hotkey, suppress=True)
                log_debug("Keyboard shortcuts registered.")
            except Exception as e_hk: # Use a distinct variable name
                log_debug(f"Error setting up keyboard shortcuts: {e_hk}")
        else:
            log_debug("Keyboard library not available. Hotkeys disabled.")
    
    def _is_ready(self):
        # Allow shortcuts to work only if the application is fully loaded
        # and initialized.
        return hasattr(self.app, '_fully_initialized') and self.app._fully_initialized and hasattr(self.app, 'gui')

    def toggle_translation_hotkey(self):
        """Hotkey callback for toggling translation on/off"""
        try:
            if self._is_ready(): 
                QMetaObject.invokeMethod(self.app.gui, "toggle_translation", Qt.QueuedConnection)
        except Exception as e:
            log_debug(f"Error in toggle_translation_hotkey: {e}")
            
    def toggle_source_visibility_hotkey(self):
        """Hotkey callback for toggling source overlay visibility"""
        try:
            if self._is_ready(): 
                QMetaObject.invokeMethod(self.app.gui, "toggle_source_overlay", Qt.QueuedConnection)
        except Exception as e:
            log_debug(f"Error in toggle_source_visibility_hotkey: {e}")
            
    def toggle_target_visibility_hotkey(self):
        """Hotkey callback for toggling target overlay visibility"""
        try:
            if self._is_ready(): 
                QMetaObject.invokeMethod(self.app.gui, "toggle_target_overlay", Qt.QueuedConnection)
        except Exception as e:
            log_debug(f"Error in toggle_target_visibility_hotkey: {e}")
            
    def save_settings_hotkey(self):
        """Hotkey callback for saving settings"""
        try:
            if self._is_ready(): 
                QMetaObject.invokeMethod(self.app.gui, "save_all_settings", Qt.QueuedConnection)
        except Exception as e:
            log_debug(f"Error in save_settings_hotkey: {e}")
            
    def clear_file_caches_hotkey(self):
        """Hotkey callback for clearing file caches"""
        try:
            if self._is_ready(): 
                QMetaObject.invokeMethod(self.app.gui, "do_clear_file_caches", Qt.QueuedConnection)
        except Exception as e:
            log_debug(f"Error in clear_file_caches_hotkey: {e}")
            
    def clear_cache_hotkey(self):
        """Hotkey callback for clearing translation cache"""
        try:
            if self._is_ready(): 
                QMetaObject.invokeMethod(self.app.gui, "do_clear_translation_cache", Qt.QueuedConnection)
        except Exception as e:
            log_debug(f"Error in clear_cache_hotkey: {e}")
            
    def clear_debug_log_hotkey(self):
        """Hotkey callback for clearing the debug log"""
        try:
            if self._is_ready(): 
                QMetaObject.invokeMethod(self.app.gui, "do_clear_debug_log", Qt.QueuedConnection)
        except Exception as e:
            log_debug(f"Error in clear_debug_log_hotkey: {e}")

    def reset_window_geometry_hotkey(self):
        """Hotkey callback for resetting window geometry"""
        try:
            if self._is_ready(): 
                QMetaObject.invokeMethod(self.app.gui, "reset_window_geometry", Qt.QueuedConnection)
        except Exception as e:
            log_debug(f"Error in reset_window_geometry_hotkey: {e}")

    def take_screenshot_hotkey(self):
        """Hotkey callback for taking a marketing screenshot (Alt+L)."""
        try:
            if self._is_ready():
                QMetaObject.invokeMethod(self.app.gui, "trigger_screenshot", Qt.QueuedConnection)
        except Exception as e:
            log_debug(f"Error in take_screenshot_hotkey: {e}")