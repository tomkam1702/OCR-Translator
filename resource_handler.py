import os
import sys
import nuitka_compat

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller/Nuitka"""
    try:
        # When running in a compiled executable, prioritize the base directory
        # (next to launcher) over the _MEIPASS/_internal directory to allow
        # for user-modified files
        
        # First check in the base directory - this allows users to update files
        # without rebuilding the application
        base_dir = nuitka_compat.get_base_dir()
        base_path = os.path.join(base_dir, relative_path)
        if os.path.exists(base_path):
            return base_path
            
        # If not found next to the executable, use the bundled version in _MEIPASS
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # Nuitka uses _internal/ via nuitka_compat
        bundle_dir = getattr(sys, '_MEIPASS', base_dir)
        direct_path = os.path.join(bundle_dir, relative_path)
        if os.path.exists(direct_path):
            return direct_path
            
        # If still not found, default to bundle path anyway (consistent with original behavior)
        return direct_path
    except Exception:
        # In development mode, look relative to the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(script_dir, relative_path)

