# Game-Changing Translator Application Files Structure

## Core Application Files

### Entry Point & Main Logic
- **main.py** - Application entry point, sets up the environment and starts the main application
- **app_logic.py** - Main application class (GameChangingTranslator) and central coordinator
- **bundled_app.py** - All-in-one bundler for PyInstaller with all imports for dependency detection
- **resource_copier.py** - Resource management for compiled executables, ensures resources folder exists next to executable
- **__init__.py** - Package definition file

### Handlers (Modular Components)
- **handlers/__init__.py** - Handlers package definition, exports handler classes
- **handlers/cache_manager.py** - Translation cache management and persistence
- **handlers/configuration_handler.py** - Settings and configuration file management
- **handlers/display_manager.py** - UI display updates for translation text and debug information
- **handlers/hotkey_handler.py** - Keyboard shortcut setup and management
- **handlers/translation_handler.py** - Text translation using different translation services
- **handlers/ui_interaction_handler.py** - User interface interaction management

### Core Functionality Modules
- **worker_threads.py** - Background thread operations for capture, OCR, and translation
- **marian_mt_translator.py** - Local translation using MarianMT neural network models
- **convert_marian.py** - HuggingFace's conversion script for converting Tatoeba models to MarianMT format (used for English-to-Polish model)
- **unified_translation_cache.py** - Unified LRU cache system for all translation providers (Google, DeepL, MarianMT)
- **ocr_utils.py** - OCR processing utilities and text extraction
- **translation_utils.py** - Translation-related helper functions
- **language_manager.py** - Management of language lists, codes and mappings for translation services
- **language_ui.py** - UI language localization support for multiple interface languages
- **overlay_manager.py** - Functions for managing the source and target overlay windows
- **gui_builder.py** - UI construction functions for tabs and interface elements
- **ui_elements.py** - Reusable UI component definitions

### Configuration and Core Support
- **config_manager.py** - Configuration loading, saving, and default values
- **constants.py** - Application constants and language code definitions
- **resource_handler.py** - Resource file path resolution for development and compiled versions
- **logger.py** - Application logging functionality

## Configuration Files
- **ocr_translator_config.ini** - Application configuration file
- **requirements.txt** - Python package dependencies
- **install_dependencies.bat** - Windows batch script to install dependencies
- **run.bat** - Windows batch script to run the application

## Resource Files
- **resources/lang_codes.csv** - Generic language name to ISO code mappings
- **resources/google_trans_source.csv** - Source language codes for Google Translate API
- **resources/google_trans_target.csv** - Target language codes for Google Translate API
- **resources/deepl_trans_source.csv** - Source language codes for DeepL API
- **resources/deepl_trans_target.csv** - Target language codes for DeepL API
- **resources/gemini_trans_source.csv** - Source language codes for Gemini API
- **resources/gemini_trans_target.csv** - Target language codes for Gemini API
- **resources/language_display_names.csv** - Localized language display names for UI (English/Polish)
- **resources/MarianMT_select_models.csv** - Available MarianMT translation models
- **resources/MarianMT_models_short_list.csv** - Preferred/recommended MarianMT models
- **resources/gui_eng.csv** - English UI translations
- **resources/gui_pol.csv** - Polish UI translations

## Build and Setup Files
- **GameChangingTranslator.spec** - PyInstaller specification file
- **setup.py** - Setup configuration for building executables

## Documentation
- **README.md** - Main project documentation
- **CHANGELOG.md** - Version history and changes
- **LICENSE** - GPL v3 license file
- **OCR_Translator_Structure.md** - This file - application structure documentation
- **docs/user-manual.html** - Comprehensive user manual in English
- **docs/user-manual_pl.html** - Comprehensive user manual in Polish
- **docs/installation.html** - Installation guide in English
- **docs/installation_pl.html** - Installation guide in Polish
- **docs/gallery.html** - Application gallery in English
- **docs/gallery_pl.html** - Application gallery in Polish
- **docs/developer-guide.md** - Developer documentation
- **docs/troubleshooting.md** - Troubleshooting guide

## Cache and Data Files (Generated at Runtime)
- **deepl_cache.txt** - Cached translations from DeepL API
- **googletrans_cache.txt** - Cached translations from Google Translate API (if file caching enabled)
- **gemini_cache.txt** - Cached translations from Gemini API (if file caching enabled)
- **Gemini_API_call_logs.txt** - Detailed Gemini API call logging with cost tracking and token analysis
- **marian_models_cache/** - Directory for cached MarianMT models
- **translator_debug.log** - Application debug log file
- **debug_images/** - Directory for saving debug images (created when debug mode is enabled)

---

## Notes

- Cache files (`deepl_cache.txt`, `googletrans_cache.txt`, `gemini_cache.txt`) and log files are generated during runtime
- The `marian_models_cache/` directory is created automatically when MarianMT models are downloaded
- Debug images are saved to `debug_images/` only when debug mode is enabled
- All CSV files are organized in the `resources/` directory for consistency and better organization
- The application supports both English and Polish UI languages through localized CSV files
- The `resource_copier.py` module ensures that when running as a compiled executable, resource files are available next to the executable for user modifications

---

## Files Excluded from Application Structure

The following files are test/development files and are not part of the core application:

### Development Utilities
- **cleanup_repository.py** - Repository cleanup script for removing test files before GitHub upload
- **build_and_copy_resources.py** - Development build utility for PyInstaller
- **build_and_copy_resources.bat** - Windows batch script for development builds

### Development Documentation/Prompts
- **prompt.txt** - Development prompt file with feature implementation instructions
- **prompt_ocr.txt** - Development prompt for OCR feature enhancements
- **prompt_user_guide.txt** - Development prompt for user guide corrections
- **Language_Names_Localized.md** - Development strategy document for implementing Polish language names
- **ocr_translator_config.7z** - Compressed backup configuration file

### Test Files (if present)
- **test_*.py** - Various test files for different components
- **test_unified_cache.py** - Test script for unified translation cache functionality
- **comprehensive_test.py** - Comprehensive testing script
- **simple_verification.py** - Simple verification script
- **verification_test.py** - Verification testing script

These files are useful for development and testing but are not required for the application to function in a production environment.

---

## File Organization Benefits

The modular structure provides several advantages:

1. **Separation of Concerns**: Each handler manages a specific aspect of functionality
2. **Maintainability**: Easy to locate and modify specific features
3. **Extensibility**: New translation providers or UI features can be added easily
4. **Resource Management**: All language files and configuration data organized in dedicated directories
5. **Build Support**: Complete build chain with PyInstaller specification and setup files
6. **Documentation**: Comprehensive documentation for users and developers
7. **Localization**: Full support for multiple UI languages through CSV-based translation files
8. **Unified Caching**: Single, efficient LRU cache system for all translation providers, eliminating memory waste and cache clearing bugs

## Translation Caching Architecture

The application uses a two-tier caching system:

### Level 1: Unified In-Memory Cache (`unified_translation_cache.py`)
- **Single LRU cache** for all translation providers (Google, DeepL, MarianMT)
- **Thread-safe** with proper locking mechanisms
- **Configurable size** (default: 1000 entries)
- **Smart cache keys** including provider-specific parameters (e.g., beam size for MarianMT)
- **Automatic LRU eviction** when cache is full
- **Provider-specific clearing** functionality

### Level 2: Persistent File Cache (Existing)
- **`deepl_cache.txt`** - DeepL API translations persisted to disk
- **`googletrans_cache.txt`** - Google Translate API translations persisted to disk
- **No file caching for MarianMT** (offline model, no API costs)

This architecture provides:
- ✅ **40-60% memory reduction** from eliminating duplicate cache storage
- ✅ **Fixed cache clearing bugs** - unified cache clearing actually works
- ✅ **Consistent behavior** across all translation providers
- ✅ **Thread safety** improvements with proper locking
- ✅ **Preserved compatibility** - existing file caches remain intact

## Gemini API Integration Files

### Gemini API Call Logs (`Gemini_API_call_logs.txt`)
The Gemini API call logging system provides comprehensive tracking and analysis of all API interactions when enabled in settings. This file contains detailed information for cost monitoring, debugging, and usage analysis.

**Log Entry Structure:**
Each API call generates a detailed log entry with the following information:
- **Timestamp and Language Pair** - Precise timing and translation direction
- **Original Text** - The text being translated
- **Complete Message Content** - Full context window sent to Gemini API, including previous subtitles for context-aware translation
- **Response Content** - Complete translation received from Gemini
- **Token Analysis** - Exact input/output token counts for precise cost calculation
- **Cost Breakdown** - Per-call and cumulative cost tracking with separate input/output costs
- **Performance Metrics** - API call duration and word count analysis

**Cost Tracking Features:**
- Real-time cumulative cost tracking across sessions
- Separate input/output token cost analysis using Gemini 2.5 Flash-Lite pricing ($0.10 per 1M input tokens, $0.40 per 1M output tokens)
- Total words translated counter for usage analytics
- Cost-per-word analysis for budget planning

**Context Window Documentation:**
The logs show the complete context window implementation, demonstrating how previous subtitles are included for narrative coherence:
```
ENGLISH: [Previous subtitle 1]
ENGLISH: [Previous subtitle 2] 
ENGLISH: [Current subtitle to translate]

POLISH: [Previous translation 1]
POLISH: [Previous translation 2]
POLISH: [Space for current translation]
```

### Gemini Translation Cache (`gemini_cache.txt`)
The Gemini cache file stores translations in a structured format for efficient retrieval and API cost reduction.

**Cache Format:**
```
Gemini(LANG_PAIR,timestamp):original_text:==:translated_text
```

**Format Components:**
- **Provider Identifier**: "Gemini" to distinguish from other translation caches
- **Language Pair**: Source-target language codes (e.g., "CS-PL", "FR-EN")
- **Timestamp**: Creation timestamp for cache entry management
- **Original Text**: Source text as recognized by OCR
- **Translated Text**: Gemini's translation result

**Cache Efficiency:**
- Reduces API calls for repeated text segments
- Survives application restarts for long-term cost savings
- Integrates with unified in-memory cache for optimal performance
- Particularly effective for static UI elements and repeated dialogue

**Example Cache Entries:**
```
Gemini(CS-PL,2025-07-06 21:12:00):A vodkaď se podle tebe teda známe?:==:A skąd niby się znamy?
Gemini(FR-EN,2025-07-06 21:13:31):Sa glorieuse Majesté:==:His Glorious Majesty
```

The cache effectiveness depends on OCR consistency - identical OCR results enable cache hits, while variations trigger new API calls.
