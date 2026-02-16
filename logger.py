import time
import os

# Global flag to control debug logging
_debug_logging_enabled = True

def set_debug_logging_enabled(enabled):
    """Enable or disable debug logging."""
    global _debug_logging_enabled
    _debug_logging_enabled = enabled

def is_debug_logging_enabled():
    """Check if debug logging is currently enabled."""
    return _debug_logging_enabled

def log_debug(message):
    """Appends a timestamped message to the debug log file if logging is enabled."""
    if not _debug_logging_enabled:
        return
        
    try:
        # Log filename
        with open('translator_debug.log', 'a', encoding='utf-8-sig') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: {message}\n")
    except Exception as e:
        print(f"Error writing to log file: {e}") # Fallback to console if log fails

