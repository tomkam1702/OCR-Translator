# Game-Changing Translator - File Structure Reference

> **For detailed development information, see [`docs/developer-guide.md`](docs/developer-guide.md)**

This document provides a quick reference to the application's file organization and architecture.

## 🏗️ Architecture Overview

```
Entry Point (main.py) 
    ↓
Central Coordinator (app_logic.py)
    ↓
┌─────────────┬─────────────┬─────────────┬─────────────┐
│   Handlers  │   Workers   │   Utils     │    UI       │
│   (modular) │ (threads)   │ (helpers)   │ (interface) │
└─────────────┴─────────────┴─────────────┴─────────────┘
    ↓
Unified Cache System → File Persistence
```

## 🌟 Key Features

### **Dynamic Gemini Model Configuration**
- **CSV-based model management** - All Gemini models configured in `resources/gemini_models.csv`
- **Separate OCR and Translation models** - Different models can be selected for each operation
- **Automatic cost calculation** - Token costs update based on selected models
- **Real-time model switching** - No application restart required

### **Unified Caching System**
- **Two-tier cache architecture** - In-memory LRU cache + persistent file storage
- **40-60% memory reduction** compared to previous multi-cache approach
- **Thread-safe operations** with proper locking mechanisms

### **Comprehensive API Monitoring**
- **Real-time cost tracking** for Gemini API usage (OCR + Translation)
- **Detailed logging** with token analysis and performance metrics
- **Export capabilities** for usage statistics and billing analysis

## 📁 Core Application Files

### **Entry Point & Coordination**
- **`main.py`** - Application entry point
- **`app_logic.py`** - Central coordinator and main application class
- **`__init__.py`** - Package definition

### **Modular Handlers** (`handlers/`)
- **`cache_manager.py`** - File-based translation cache persistence
- **`configuration_handler.py`** - Settings and configuration management
- **`display_manager.py`** - UI updates for overlays and debug info
- **`gemini_models_manager.py`** - Dynamic Gemini model configuration management
- **`hotkey_handler.py`** - Keyboard shortcut management
- **`statistics_handler.py`** - API usage monitoring and cost tracking
- **`translation_handler.py`** - Translation provider coordination
- **`ui_interaction_handler.py`** - User interface interaction management

### **Core Processing**
- **`worker_threads.py`** - Background threads (capture → OCR → translation)
- **`unified_translation_cache.py`** - LRU cache system for all translation providers

### **Utilities**

- **`translation_utils.py`** - Translation helper functions
- **`language_manager.py`** - Language code mappings for different services
- **`config_manager.py`** - Configuration file handling
- **`resource_handler.py`** - Resource path resolution
- **`resource_copier.py`** - Resource management for compiled builds
- **`logger.py`** - Application logging

### **User Interface**
- **`gui_builder.py`** - UI construction and tab creation
- **`language_ui.py`** - Multi-language interface support
- **`overlay_manager.py`** - Source/target overlay window management
- **`ui_elements.py`** - Custom UI components
- **`constants.py`** - Application constants and language definitions

## 📋 Build & Configuration

### **Build Files**
- **`GameChangingTranslator.spec`** - PyInstaller spec (CPU-optimized)
- **`GameChangingTranslator_GPU.spec`** - PyInstaller spec (GPU/CUDA-optimized)
- **`compile_app.py`** - Python compilation utility
- **`setup.py`** - cx_Freeze setup configuration
- **`requirements.txt`** - Python dependencies

### **Scripts**
- **`run.bat`** - Application launcher
- **`install_dependencies.bat`** - Dependency installer
- **`run_python_compiler.bat`** - Build automation script

### **Configuration**
- **`ocr_translator_config.ini`** - User settings (runtime-generated)

## 📚 Resources & Data

### **Language Resources** (`resources/`)
```
resources/
├── Translation APIs
│   ├── deepl_trans_source.csv / deepl_trans_target.csv
│   ├── gemini_trans_source.csv / gemini_trans_target.csv
│   └── gemini_models.csv         # Gemini model configurations and costs
├── UI Localization
│   ├── gui_eng.csv / gui_pol.csv
│   └── language_display_names.csv
└── Language Mappings
    └── lang_codes.csv
```

### **Runtime Data** (Generated)
- **Cache Files**: `deepl_cache.txt`, `gemini_cache.txt`
- **API Logs**: `Gemini_*_Log.txt`, `DeepL_Translation_Long_Log.txt`
- **Debug**: `translator_debug.log`, `debug_images/`

## 📖 Documentation

### **User Documentation** (`docs/`)
- **`developer-guide.md`** - **Comprehensive development guide**
- **`user-manual.html`** / **`user-manual_pl.html`** - User manuals (EN/PL)
- **`installation.html`** / **`installation_pl.html`** - Installation guides (EN/PL)
- **`gallery.html`** / **`gallery_pl.html`** - Application galleries (EN/PL)
- **`troubleshooting.md`** - Problem resolution guide
- **`flags/`**, **`gallery/`**, **`screenshots/`** - Visual assets

### **Project Documentation**
- **`README.md`** - Project overview and quick start
- **`CHANGELOG.md`** - Version history
- **`LICENSE`** - GPL v3 license
- **`ATTRIBUTION.md`** - Third-party attributions
- **`CONTRIBUTORS.md`** - Project contributors

---

## 🏛️ Key Architecture Benefits

1. **🔧 Modular Design** - Each handler manages specific functionality
2. **⚡ Performance** - Background threads + unified caching
3. **🌍 Localization** - Multi-language UI and comprehensive language support
4. **📊 Monitoring** - Complete API usage tracking and cost management
5. **🚀 Build Flexibility** - Multiple compilation options (CPU/GPU)
6. **🛠️ Maintainability** - Clear separation of concerns and well-organized structure

---

> **📘 For detailed development information including:**
> - How to add new features
> - Testing procedures  
> - Build instructions
> - Code architecture details
> - Contributing guidelines
>
> **See the comprehensive [`docs/developer-guide.md`](docs/developer-guide.md)**
