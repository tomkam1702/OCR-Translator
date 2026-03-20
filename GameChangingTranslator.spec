# -*- mode: python ; coding: utf-8 -*-

"""
Game-Changing Translator PyInstaller Specification File - Optimized Version
This spec file includes all necessary dependencies while excluding unnecessary bloat.
Keeps ALL functionality but optimizes package size by excluding unused parts of heavy libraries.

Updated for Google Gen AI library migration (google.genai) with fallback support.

To build: pyinstaller GameChangingTranslator.spec
"""

import os

# Get the current directory for proper path handling
current_dir = os.path.dirname(os.path.abspath('__file__'))

block_cipher = None

a = Analysis(
    ['main.py'],  # Use main.py instead of bundled_app.py (same as working Alternative spec)
    pathex=[current_dir],  # Include current directory in Python path
    binaries=[],
    # Include all necessary data files
    datas=[
        # Copy entire resources directory to root level (same folder as .exe)
        ('resources', 'resources'),
        # Copy entire docs directory to root level (same folder as .exe)
        ('docs', 'docs'),
        # Essential documentation
        ('README.md', '.'),
        ('LICENSE', '.'),
        # MarianMT conversion script for English-to-Polish models
        ('convert_marian.py', '.'),
    ],
    # Include all modules that are actually needed (keep original working set)
    hiddenimports=[
        # Core application modules
        'logger',
        'app_logic',
        'config_manager',
        'constants',
        'gui_builder',
        'language_manager',
        'language_ui',
        'marian_mt_translator',  # Keep MarianMT functionality
        'unified_translation_cache',  # Unified LRU cache for all translation providers
        'ocr_utils',
        'overlay_manager',
        'pyside_overlay',  # PySide6 RTL translation overlays with native Qt support
        'resource_handler',
        'resource_copier',  # Auto-copy resources functionality
        'rtl_text_processor',  # RTL text processing for tkinter widgets (fallback)
        'translation_utils',
        'ui_elements',
        'worker_threads',
        'main',
        # Auto-update system modules
        'update_checker',  # GitHub API integration and download logic
        'update_applier',  # Startup update detection and application
        # Handler modules
        'handlers',
        'handlers.cache_manager',
        'handlers.configuration_handler',
        'handlers.display_manager',
        'handlers.gemini_models_manager',  # Gemini model configuration management
        'handlers.hotkey_handler',
        'handlers.statistics_handler',
        'handlers.translation_handler',
        'handlers.ui_interaction_handler',
        # Essential GUI libraries
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'tkinter.colorchooser',
        '_tkinter',
        # PySide6 for RTL translation overlays with native Qt support
        # NOTE: Must use PySide6==6.7.3 — Qt 6.8+ breaks frameless window resizing on Windows.
        # See requirements.txt for details.
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        # RTL text processing dependencies
        'python-bidi',
        'arabic-reshaper',
        # Image processing
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        # Scientific libraries (simplified to avoid docstring issues)
        'numpy',
        'cv2',
        'pytesseract',
        'pyautogui',
        # Optional but needed dependencies
        'keyboard',
        'requests',
        'urllib.parse',
        'google.cloud.translate_v2',
        # NEW: Google Gen AI library (primary)
        'google.genai',
        'google.genai.types',
        'google.genai.client',
        'google.genai.models',
        # OLD: Google Generative AI (fallback)
        'google.generativeai',
        'google.auth',
        # Pre-load critical Gemini modules for performance
        'google.generativeai.types',
        'google.generativeai.client',
        'google.ai.generativelanguage',
        'deepl',
        
        # NEW: Additional dependencies for google.genai
        'pydantic',
        'pydantic.types',
        'pydantic.validators',
        'httpx',
        'httpx._client',
        'httpx._models',
        'anyio',
        'sniffio',
        'h11',
        'httpcore',
        'websockets',
        'tenacity',
        # Threading optimization
        'concurrent.futures',
        'threading',
        # Keep torch/transformers/sentencepiece for MarianMT (minimal exclusions)
        'torch',
        'transformers',
        'transformers.models',
        'transformers.models.marian',
        'transformers.models.marian.modeling_marian',
        'transformers.models.marian.tokenization_marian',
        'transformers.models.marian.configuration_marian',
        'transformers.tokenization_utils',
        'transformers.tokenization_utils_base',
        'transformers.modeling_utils',
        'transformers.configuration_utils',
        'sentencepiece',
        # Fix for MarianMT in compiled version - include unittest.mock that transformers needs
        'unittest.mock',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Only exclude clearly unnecessary libraries (be very conservative)
    excludes=[
        # Exclude clearly unused libraries
        'matplotlib',
        'pandas',
        'scipy',
        'sklearn',
        'tensorflow',
        'keras',
        'jupyter',
        'notebook',
        'pytest',
        'sphinx',
        'doctest',
        
        # GUI frameworks we don't use
        'PyQt5',
        'PyQt6',
        'PySide2',
        
        # Web frameworks
        'flask',
        'django',
        'fastapi',
        
        # Large PyTorch modules we don't need
        'torchvision',
        'torchaudio',
        
        # Test modules
        'tkinter.test',
    ],
    optimize=1,  # Use level 1 instead of 2 to avoid potential optimization issues
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GameChangingTranslator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disabled to avoid antivirus false positives
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',  # Add icon if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,  # Disabled to avoid antivirus false positives
    upx_exclude=[],
    name='GameChangingTranslator',
)
