# Nuitka compatibility — must run before any other imports that check sys.frozen
import nuitka_compat
nuitka_compat.setup()

import traceback
import os
import sys

# Silent Qt DPI context logs (prevents technical warnings on Windows)
os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"

from logger import log_debug


def main_entry_point():
    # =========================================================================
    # PySide6 Only
    # =========================================================================
    
    # No legacy UI root needed
    ui_root = None
    
    # QApplication — Main event loop
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from gui_v4 import MainWindowV4
    
    qt_app = QApplication(sys.argv)
    
    translator = None
    window = None
    try:
        # Backend initialized without legacy dependencies
        from app_logic import GameChangingTranslator
        translator = GameChangingTranslator(ui_root)
        
        log_debug("GameChangingTranslator initialized")
        
        # Main PySide6 window
        window = MainWindowV4()
        window.set_translator(translator)
        window.show()
        log_debug("MainWindowV4 shown with backend connected")
        
        sys.exit(qt_app.exec())
        
    except Exception as e:
        log_msg = f"FATAL ERROR in main_entry_point: {type(e).__name__} - {e}"
        print(log_msg)
        log_debug(log_msg)
        tb_str = traceback.format_exc()
        log_debug("Traceback:\n" + tb_str)
        print(f"Check 'translator_debug.log' for details.\nTraceback:\n{tb_str}")
    finally:
        if translator and hasattr(translator, 'is_running'):
            translator.is_running = False


if __name__ == "__main__":
    main_entry_point()
