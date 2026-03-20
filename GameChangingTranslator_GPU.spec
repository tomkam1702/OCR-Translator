# -*- mode: python ; coding: utf-8 -*-

"""
Game-Changing Translator PyInstaller Specification File - Simple GPU Version
This spec file bundles everything needed for CUDA support without detection.
Just includes all necessary dependencies statically.

Updated for Google Gen AI library migration (google.genai) with fallback support.

To build: pyinstaller GameChangingTranslator_GPU.spec
"""

import os

# Get the current directory
current_dir = os.path.dirname(os.path.abspath('__file__'))

block_cipher = None

a = Analysis(
    ['main.py'],  # Use main.py instead of bundled_app.py (same as working Alternative spec)
    pathex=[current_dir],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('docs', 'docs'),
        ('README.md', '.'),
        ('LICENSE', '.'),
        # MarianMT conversion script for English-to-Polish models
        ('convert_marian.py', '.'),
    ],
    hiddenimports=[
        # Core application
        'logger',
        'app_logic',
        'config_manager',
        'constants',
        'gui_builder',
        'language_manager',
        'language_ui',
        'marian_mt_translator',
        'unified_translation_cache',
        'ocr_utils',
        'overlay_manager',
        'pyside_overlay',  # PySide6 RTL translation overlays with native Qt support
        'resource_handler',
        'resource_copier',
        'rtl_text_processor',  # RTL text processing for tkinter widgets (fallback)
        'translation_utils',
        'ui_elements',
        'worker_threads',
        'main',
        # Auto-update system modules
        'update_checker',  # GitHub API integration and download logic
        'update_applier',  # Startup update detection and application
        
        # Handlers
        'handlers',
        'handlers.cache_manager',
        'handlers.configuration_handler',
        'handlers.display_manager',
        'handlers.gemini_models_manager',  # Gemini model configuration management
        'handlers.hotkey_handler',
        'handlers.statistics_handler',
        'handlers.translation_handler',
        'handlers.ui_interaction_handler',
        
        # GUI
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
        
        # Core dependencies
        'numpy',
        'cv2',
        'pytesseract',
        'pyautogui',
        
        # Optional
        'keyboard',
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
        
        # GPU monitoring (Windows)
        'nvidia_ml_py3',
        
        # PyTorch (CPU + CUDA)
        'torch',
        'torch.nn',
        'torch.nn.functional',
        'torch.nn.modules',
        'torch.cuda',
        'torch.cuda.amp',
        'torch.amp',
        'torch.backends',
        'torch.backends.cuda',
        'torch.serialization',
        'torch.storage',
        'torch.utils',
        'torch.utils.data',
        'torch._C',
        
        # Transformers
        'transformers',
        'transformers.models',
        'transformers.models.marian',
        'transformers.models.marian.configuration_marian',
        'transformers.models.marian.modeling_marian',
        'transformers.models.marian.tokenization_marian',
        'transformers.configuration_utils',
        'transformers.modeling_utils',
        'transformers.tokenization_utils',
        'transformers.tokenization_utils_base',
        'transformers.tokenization_utils_fast',
        'transformers.utils',
        'transformers.utils.hub',
        'transformers.utils.import_utils',
        'transformers.file_utils',
        'transformers.generation',
        'transformers.generation.utils',
        
        # Tokenization
        'tokenizers',
        'tokenizers.implementations',
        'tokenizers.models',
        'tokenizers.pre_tokenizers',
        'tokenizers.processors',
        'sentencepiece',
        
        # Hugging Face Hub
        'huggingface_hub',
        'huggingface_hub.file_download',
        'huggingface_hub.hf_api',
        'huggingface_hub.repository',
        'huggingface_hub.snapshot_download',
        
        # Networking and utilities
        'requests',
        'requests.adapters',
        'requests.auth',
        'requests.models',
        'requests.sessions',
        'urllib3',
        'tqdm',
        'tqdm.auto',
        
        # File and data handling
        'pathlib',
        'tempfile',
        'shutil',
        'json',
        'yaml',
        'safetensors',
        'safetensors.torch',
        
        # Text processing
        'regex',
        're',
        'unicodedata',
        
        # System
        'threading',
        'concurrent.futures',
        'multiprocessing',
        'logging',
        'warnings',
        'traceback',
        # Fix for MarianMT in compiled version - include unittest.mock that transformers needs
        'unittest.mock',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Only exclude what's definitely not needed
        'tensorflow',
        'keras',
        'sklearn',
        'pandas',
        'matplotlib',
        'seaborn',
        'plotly',
        'jupyter',
        'ipython',
        'notebook',
        'pytest',
        'PySide2',
        'PyQt5',
        'PyQt6',
        'flask',
        'django',
        'fastapi',
        'torchvision',
        'torchaudio',
        'torchtext',
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
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='GameChangingTranslator',
)
