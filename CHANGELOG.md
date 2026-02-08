# Changelog

All notable changes to the Game-Changing Translator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.9.0] - 2025-12-30

### Added
- **Gemini 3 Flash Support**: Added Google's latest Gemini 3 Flash model for translation and OCR
  - Uses `thinking_level="MINIMAL"` configuration optimised for fast, accurate translations
  - Excellent cultural and idiomatic adaptation (e.g., Czech "Trhani z Nemanic" → English "Ragtag nobodies from Nowhere")
  - Pricing: $0.50 per 1M input tokens, $3.00 per 1M output tokens

### Changed
- N/A

### Fixed
- N/A

### Removed
- N/A

## [3.8.0] - 2025-11-20

### Added
- **DeepL Minority Language Support (Beta)**: Added support for over 70 new minority and regional languages via DeepL API.
  - Includes languages such as Welsh, Irish, Breton, Basque, Catalan, Corsican, Occitan, Quechua, Guarani, Aymara, Maori, Sanskrit, Latin, and Esperanto.
  - Note: These languages are currently in Beta status within DeepL, so translation quality may vary.

## [3.7.0] - 2025-10-04

### Added
- **DeepL Translation Context Window Support**: Enhanced DeepL translation with context awareness for improved grammar and meaning
  - Configurable context window supporting up to 3 previous subtitles for narrative coherence
  - Context usage does not count towards DeepL's free translation character limit
  - Dedicated detailed logging system in `DeepL_Translation_Long_Log.txt` file for complete translation tracking
  - Context window improves pronoun resolution and grammatical agreement between consecutive subtitles
- **Updated Gemini Model Support**: Added latest Gemini models with improved performance characteristics
  - Gemini 2.5 Flash (gemini-2.5-flash-preview-09-2025) with good translation quality and lower latency
  - Gemini 2.5 Flash-Lite (gemini-2.5-flash-lite-preview-09-2025) optimised for OCR with reduced latency
  - Gemini 2.0 Flash remains slightly better for translation quality with more than six times lower output cost than Gemini 2.5 Flash
- **Experimental Line Break Preservation**: Optional feature to maintain original line breaks in OCR and translation output
  - Works best with Gemini models for consistent line break handling
  - Less consistent results with GPT models and DeepL
  - Recommended to keep disabled for most scenarios but helpful for certain dialogue scenes without initial dashes

### Changed
- N/A

### Fixed
- N/A

### Removed
- N/A

## [3.6.0] - 2025-09-14

### Added
- **OpenAI API Translation and OCR Support**: Complete integration with OpenAI's translation services providing advanced AI-powered translation capabilities
  - Support for multiple OpenAI models: GPT-4.1 Mini, GPT-4.1 Nano, and GPT-5 Nano
  - Comprehensive API call logging with detailed token usage and cost tracking
  - Dynamic model configuration through CSV-based management system
  
### Changed
- **Enhanced Translation and OCR Provider Architecture**: Expanded translation and OCR workflows to support OpenAI alongside existing Gemini, DeepL, Google Translate, and MarianMT providers

### Fixed
- N/A

### Removed
- N/A

## [3.5.8] - 2025-08-29

### Added
- **Auto-Update System**: Complete auto-update functionality accessible through "Check for Updates" button in the About tab
  - GitHub API integration for checking latest releases automatically
  - Simple one-click update process with progress tracking
  - Safe update application with user file preservation
  - Staging system for secure update downloads and installation
- **Target Window Font Type Selection**: Enhanced typography customisation allowing selection of any Windows system font for translation display
  - Expanded beyond the previous default Arial font limitation
  - Access to complete Windows font library for personalised translation appearance
  - Improved readability options to suit individual preferences and visual requirements
- **Independent Opacity Controls**: Granular transparency management for enhanced translation window customisation
  - Separate background and text opacity sliders providing independent control (0.0 to 1.0 range)
  - Replaced previous fixed 0.85 opacity preset with flexible user-defined transparency levels
  - Enhanced visual integration allowing translation windows to blend seamlessly with any background content

### Changed
- **Improved Subtitle Display for Dialogs**: Enhanced formatting of conversational subtitles with proper line breaks
  - Previous format: `   - How are you? - Fine.    `  
  - New format with proper line separation:
    ```
        - How are you?
        - Fine.                 
    ```
  - Better readability for dialog-heavy content like games and movies

### Fixed
- N/A

### Removed
- N/A

## [3.5.7] - 2025-08-22

### Added
- N/A

### Changed
- **Translation Window Migration to PySide6**: Replaced tkinter-based translation window with PySide6 implementation for superior RTL language support
  - Migrated from tkinter to Qt6-based translation overlays for improved right-to-left text rendering
  - Implemented hybrid RTL architecture combining native Qt support (primary) with fallback tkinter processing
  - Enhanced RTL text display for Arabic, Hebrew, and Persian languages with proper character positioning
  - Improved RTL punctuation handling and bidirectional text flow using Qt's native capabilities
  - Maintained full backward compatibility with automatic fallback when PySide6 unavailable

### Fixed
- **RTL Text Display Issues**: Resolved unreliable RTL support in tkinter translation windows
  - Fixed Hebrew word wrapping issues with native Qt RTL rendering
  - Corrected punctuation positioning problems in right-to-left languages
  - Eliminated manual text repositioning requirements through Qt's bidirectional text algorithm

### Removed
- N/A

## [3.5.6] - 2025-08-17

### Added
- N/A

### Changed
- N/A

### Fixed
- **Translation Cache Duplicate Detection Bug**: Fixed incorrect duplicate detection logic in the file cache system that was preventing translations of the same source text to different target languages from being saved
  - Previously, the cache only checked if the source text was identical, ignoring the language pair
  - Now correctly checks both the source text AND the language pair (source→target) before treating an entry as a duplicate
  - Ensures that translating the same source text to different target languages (e.g., English→French and English→Italian) are both properly saved to cache files
  - Affects all translation providers that use file caching (Gemini, Google Translate, DeepL)

### Removed
- N/A

## [3.5.5] - 2025-08-17

### Added
- Added Persian language support to the Gemini API and Google Translate translation services.
- Enhanced text display formatting for right-to-left (RTL) languages with improved punctuation positioning.

### Changed
- N/A

### Fixed
- N/A

### Removed
- N/A

## [3.5.3] - 2025-08-13

### Added
- **Network Resilience System**: A comprehensive solution to prevent Windows network stack corruption that caused API delays to increase after extended use
  - Circuit Breaker Pattern: Automatically detects network degradation (>3s calls or failures) and forces a client refresh when issues are detected.
  - Periodic Client Refresh: Proactively refreshes the Gemini client every 30 minutes or after 100 API calls to prevent connection staleness.
  - Connection Cleanup: Scheduled maintenance every 20 minutes to clear connection pools and prevent the accumulation of stale connections.
  - DNS Cache Management: Hourly system-level DNS cache flushing (`ipconfig /flushdns`) to address Windows network stack issues.
  - This self-healing behavior eliminates the need for PC restarts to restore performance.

### Changed
- **API Logging Performance Optimization**: Eliminated an O(n) scaling issue in cumulative statistics calculation that caused increasing delays during extended use
  - Replaced file-based cumulative totals lookup with an efficient in-memory cache for OCR and translation operations.
  - Prevents log file reading overhead that grew progressively slower as usage history accumulated.
  - Maintains sub-second logging performance regardless of the application's runtime duration.

### Fixed
- N/A

### Removed
- N/A

## [3.5.2] - 2025-08-05

### Fixed
- **OCR Thread Artificial Delay Elimination**: Important fix for minor bug causing compound translation delays
  - Eliminated unnecessary artificial sleep intervals in Gemini OCR thread processing
  - Fixed issue where OCR thread was artificially pausing between processing queued images, even when work was available
  - Resolved compound delay problem where adaptive scan interval increases were being applied twice (once in capture thread, once in OCR thread)
  - Restores consistent ~2-second translation performance, eliminating scenarios where delays could extend to 3+ seconds
  - Maintains proper natural rate limiting through API response times and thread pool capacity limits
- **Concurrent Call Limits Optimization**: Improved system stability and performance under load
  - Reduced maximum concurrent OCR calls from 10 to 8 for better resource management
  - Reduced maximum concurrent translation calls from 8 to 6 to prevent API saturation
  - Lowered OCR overload detection threshold from >7 to >5 active calls for more responsive load balancing
  - Updated thread pool sizes to match new concurrent call limits for optimal performance
- **503 Error Suppression**: Enhanced user experience during API overload scenarios
  - Added intelligent suppression of "503 UNAVAILABLE" errors from translation window display
  - Errors are still logged for debugging purposes but hidden from end users
  - Application continues working normally when Gemini API recovers from temporary overload

### Changed
- **Adaptive Load Balancing**: More responsive system load detection and management
  - OCR overload detection now triggers at >5 active calls instead of >7 for earlier intervention
  - Improved load recovery threshold remains at <5 active calls for stable operation
  - Enhanced system responsiveness during high API usage periods

### Added
- N/A

### Removed
- **Redundant OCR Thread Delays**: Removed unnecessary artificial sleep intervals that were compounding translation delays

## [3.5.1] - 2025-08-03

### Fixed
- **Gemini OCR Performance Issue**: Fixed client initialization overhead causing OCR timeout and translation failures
  - Resolved issue where successful OCR results were discarded due to timeout limits
  - Implemented automatic Gemini client initialization for OCR operations using the same proven pattern as translation
  - Ensures reliable OCR-to-translation pipeline for all Gemini OCR operations
- **Tesseract Path Validation Error with Gemini OCR**: Fixed application startup and translation errors when Gemini OCR is selected
  - Resolved "Tesseract path invalid!" error that occurred even when Tesseract was not needed
  - Implemented conditional Tesseract path validation only when Tesseract OCR is actually selected
  - Eliminates unnecessary Tesseract dependency checks during Gemini OCR operations
  - Improves application performance by avoiding redundant Tesseract operations when using Gemini OCR

### Changed
- N/A

### Added
- **About Tab Enhancement**: Added current version number and release date display to the About tab for better version tracking

### Removed
- N/A

## [3.5.0] - 2025-08-01

### Added
- **Multiple Gemini Models Support**: Dynamic configuration system for flexible Gemini model selection
  - CSV-based model configuration (`resources/gemini_models.csv`) for easy customization
  - Separate model selection for OCR and translation operations
  - Support for Gemini 2.0 Flash, Gemini 2.0 Flash-Lite, Gemini 2.5 Flash, and Gemini 2.5 Flash-Lite
  - Dynamic cost management that automatically updates based on selected models
- **Enhanced Model Recommendations**: Performance-optimized model selection guidance
  - Gemini 2.5 Flash-Lite recommended for speed (fast-changing subtitles < 1 second)
  - Gemini 2.0 Flash recommended for superior OCR accuracy and idiomatic translations (longer subtitles)
- **Comprehensive OCR Testing Results**: Detailed model comparison data showing Gemini 2.0 models' superior performance
  - Test results demonstrate significantly better OCR accuracy across multilingual content
  - Evidence-based recommendations for optimal model selection

### Changed
- **API Library Migration**: Upgraded from `google.generativeai` to `google.genai` library for improved performance and stability
- **Optimized Threading**: Enhanced OCR and translation thread performance for faster processing and reduced latency
- **Improved Model Management**: Centralized Gemini model configuration through GeminiModelsManager class
- **Dynamic Model Selection**: Models available in UI dropdowns are now dynamically loaded from CSV configuration

### Fixed
- N/A

### Removed
- N/A

## [3.0.1] - 2025-07-24

### Added
- Enhanced debugging and logging capabilities for better troubleshooting in compiled versions
- Comprehensive library availability detection and import status reporting

### Changed
- **Updated Gemini Model**: Default Gemini model name changed from `gemini-2.5-flash-lite-preview-06-17` to `gemini-2.5-flash-lite` (stable release)
  - Provides enhanced stability and reliability with Google's official stable model
  - Automatic upgrade for existing users upon restart
- Improved error handling and exception reporting throughout the application
- Enhanced PyInstaller compilation configuration for better dependency inclusion

### Fixed
- **Critical DeepL Translation Bug**: Fixed "cannot access local variable 'e'" error that occurred when enabling DeepL translation for the first time
  - Previously required disabling and re-enabling translation to work correctly
  - Now works correctly on first attempt without workarounds
- **MarianMT Compilation Issue**: Resolved missing MarianMT translation model in compiled version
  - MarianMT was missing from Translation Model dropdown in compiled applications
  - Fixed by including `unittest.mock` dependency required by transformers library
  - MarianMT now properly available in both Python and compiled versions

### Removed
- N/A

## [3.0.0] - 2025-07-20

### Added
- **Gemini OCR - Premium Text Recognition**: Revolutionary AI-powered OCR using Gemini 2.5 Flash-Lite model for superior accuracy in challenging subtitle scenarios
  - Exceptional OCR quality with outstanding cost-to-quality ratio (~$0.00004 per screenshot)
  - 37.5 times more cost-effective than Google Cloud Vision API while delivering superior results
  - Handles complex backgrounds, low-contrast text, stylized fonts, and motion blur that confuse traditional OCR
  - Unique gaming translation solution combining premium AI OCR with real-time subtitle translation
- **API Usage Monitoring Tab**: Comprehensive cost tracking and usage analytics for all API services
  - Real-time cost monitoring for Gemini OCR and Translation services
  - Detailed statistics with rough cost estimates and performance metrics
  - Export functionality for usage data (CSV/TXT formats)
  - DeepL free usage tracking integration
- **Extended Context Window**: Expanded sliding history window support from 2 to 5 previous subtitles
  - Enhanced narrative coherence and grammatical consistency for longer conversations
  - Improved support for Asian languages that rely heavily on contextual understanding
  - Better pronoun resolution and character voice consistency

### Changed
- Enhanced OCR model selection with Gemini API as premium option alongside traditional Tesseract OCR
- Improved translation context awareness with configurable sliding window (0-5 previous subtitles)
- Updated user interface to accommodate new Gemini OCR configuration options and API usage monitoring

### Fixed
- N/A

### Removed
- N/A

## [2.0.0] - 2025-07-07

### Added
- **Gemini 2.5 Flash-Lite Integration**: Revolutionary AI-powered translation with advanced context awareness and cost-effectiveness
  - Context-aware translation with configurable sliding window (0-2 previous subtitles) for narrative coherence
  - Intelligent OCR error correction that automatically fixes garbled input text
  - Exceptional cost-effectiveness: translate massive projects like The Witcher 3 for under $5
  - Built-in real-time cost tracking with token usage analytics and cumulative cost monitoring
  - Detailed API call logging with complete transparency (`Gemini_API_call_logs.txt`)
  - Advanced file caching system (`gemini_cache.txt`) for reduced API costs
  - Superior translation quality with context understanding for dialogue flow and character consistency
- **DeepL Free Usage Tracker**: Monitor your monthly free quota consumption with real-time tracking in the Settings tab
  - Displays current usage against the 500,000 character monthly limit for DeepL API Free accounts
  - Helps users optimize their free tier usage and avoid unexpected charges

### Changed
- Enhanced translation provider selection with Gemini API as the recommended default option
- Improved cost monitoring and usage analytics across all translation services
- Updated user interface to accommodate new Gemini-specific configuration options

### Fixed
- N/A

### Removed
- N/A

## [1.1.0] - 2025-06-26

### Added
- MarianMT English-to-Polish language pair support: Downloads model from Tatoeba repository and converts it using the official conversion script, as this model is unavailable on Hugging Face
- Batch mode translation for MarianMT multi-sentence processing: Replaces multi-threading approach with native batch processing for improved performance

### Changed
- MarianMT translation architecture: Switched from multi-threaded sentence processing to efficient batch processing, providing faster translation, lower memory usage, reduced CPU overhead, and better GPU utilization while maintaining identical translation quality

### Fixed
- N/A

### Removed
- N/A

## [1.0.0] - 2025-06-20

### Added
- Initial public release
- Three translation methods: Google Translate API, DeepL API, and MarianMT
- Customisable source and target overlay windows
- Real-time OCR and translation
- Multiple image preprocessing modes
- Adjustable OCR confidence and stability thresholds
- Translation caching to improve performance
- Keyboard shortcuts for common actions
- Comprehensive logging and debugging features

### Fixed
- N/A (initial release)

### Changed
- N/A (initial release)

### Removed
- N/A (initial release)
