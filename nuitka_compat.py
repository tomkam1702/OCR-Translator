"""
Nuitka compatibility stub for open-source edition.
Provides get_base_dir() for development mode only.
"""
import os
import sys


def setup():
    """No-op in the open-source edition (no compilation support)."""
    pass


def get_base_dir():
    """Get the application base directory (development mode only).

    Returns the directory containing main.py.
    """
    main = sys.modules.get('__main__')
    if main and hasattr(main, '__file__') and main.__file__:
        return os.path.dirname(os.path.abspath(main.__file__))
    return os.getcwd()
