# GCT v4 Open-Source Edition — Implementation Plan

> **For Antigravity:** REQUIRED SUB-SKILL: Load executing-plans to implement this plan task-by-task.

**Goal:** Create a fully functional FREE-only open-source edition of Game-Changing Translator v4, with all PRO logic removed and the About tab redirecting to GitHub Releases.

**Architecture:** Copy the full repository to a new directory, then systematically: (1) delete files related to licensing, compilation, and build artifacts, (2) replace all `is_pro_active()` calls with a hardcoded `False`, (3) remove the `licence_manager.py` module and all imports, (4) remove `SetWindowDisplayAffinity` calls entirely, (5) redesign the About tab's PRO section into a GitHub Releases link, (6) clean up `.gitignore` and README, (7) publish as a single fresh commit.

**Tech Stack:** Python 3, PySide6, Git

**Source repo:** `d:\GitHub\OCR_Translator_GitHub_v4_new_GUI`  
**Target repo:** `d:\GitHub\OCR_Translator_GitHub_v4_open_source`

---

## Task 1: Copy Repository & Delete Unnecessary Files

**Files:**
- Source: `d:\GitHub\OCR_Translator_GitHub_v4_new_GUI` (entire directory)
- Target: `d:\GitHub\OCR_Translator_GitHub_v4_open_source`

**Step 1: Copy the repository (excluding .git)**

```powershell
robocopy "d:\GitHub\OCR_Translator_GitHub_v4_new_GUI" "d:\GitHub\OCR_Translator_GitHub_v4_open_source" /E /XD .git __pycache__ dist_Nuitka dist_test dist_test2 scratch Screenshots .gemini
```

> **Note:** We intentionally exclude `.git` — we will initialize a fresh repo in Task 8. We also exclude all `dist_*` build output directories, `scratch`, `Screenshots`, and `__pycache__`.

**Step 2: Delete licence-related files**

```powershell
# Licence manager module
Remove-Item "d:\GitHub\OCR_Translator_GitHub_v4_open_source\licence_manager.py"

# All licence data JSON files
Remove-Item "d:\GitHub\OCR_Translator_GitHub_v4_open_source\licence_data*.json"
```

**Step 3: Delete compilation-related files**

```powershell
# Compilation script and spec
Remove-Item "d:\GitHub\OCR_Translator_GitHub_v4_open_source\compile_app.py"
Remove-Item "d:\GitHub\OCR_Translator_GitHub_v4_open_source\compile_app.7z"
Remove-Item "d:\GitHub\OCR_Translator_GitHub_v4_open_source\GameChangingTranslator.spec"

# Nuitka compatibility layer (only needed for compiled version)
Remove-Item "d:\GitHub\OCR_Translator_GitHub_v4_open_source\nuitka_compat.py"

# Setup script (used for compilation)
Remove-Item "d:\GitHub\OCR_Translator_GitHub_v4_open_source\setup.py"

# Resource copier (copies bundled resources at compile time)
Remove-Item "d:\GitHub\OCR_Translator_GitHub_v4_open_source\resource_copier.py"

# Update applier (auto-update for compiled version)
Remove-Item "d:\GitHub\OCR_Translator_GitHub_v4_open_source\update_applier.py"

# Update checker (auto-update for compiled version)
Remove-Item "d:\GitHub\OCR_Translator_GitHub_v4_open_source\update_checker.py"

# Batch installer
Remove-Item "d:\GitHub\OCR_Translator_GitHub_v4_open_source\install_dependencies.bat"
```

**Step 4: Delete log, cache, and runtime files**

```powershell
# Log files
Remove-Item "d:\GitHub\OCR_Translator_GitHub_v4_open_source\*_Log*.txt" -ErrorAction SilentlyContinue
Remove-Item "d:\GitHub\OCR_Translator_GitHub_v4_open_source\translator_debug*.log" -ErrorAction SilentlyContinue

# Cache files
Remove-Item "d:\GitHub\OCR_Translator_GitHub_v4_open_source\*_cache*.txt" -ErrorAction SilentlyContinue

# Config file (user-generated)
Remove-Item "d:\GitHub\OCR_Translator_GitHub_v4_open_source\ocr_translator_config.ini" -ErrorAction SilentlyContinue

# Custom prompt files (user-generated)
Remove-Item "d:\GitHub\OCR_Translator_GitHub_v4_open_source\custom_prompt*.txt" -ErrorAction SilentlyContinue
Remove-Item "d:\GitHub\OCR_Translator_GitHub_v4_open_source\custom_ocr_prompt*.txt" -ErrorAction SilentlyContinue
```

**Step 5: Verify remaining file structure**

```powershell
Get-ChildItem "d:\GitHub\OCR_Translator_GitHub_v4_open_source" -Recurse | Select-Object FullName
```

Expected: No `licence_manager.py`, no `compile_app.*`, no `dist_*`, no `.git`, no `*.log`, no `*_cache*.txt`, no `licence_data*.json`.

---

## Task 2: Create `nuitka_compat.py` Stub

The original `nuitka_compat.py` is needed by many modules (`main.py`, `gui_v4.py`, `app_logic.py`, `resource_handler.py`, etc.) for the `get_base_dir()` function. We must replace it with a minimal stub that only provides `get_base_dir()` for development mode.

**Files:**
- Create: `d:\GitHub\OCR_Translator_GitHub_v4_open_source\nuitka_compat.py`

**Step 1: Create the stub**

```python
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
```

---

## Task 3: Modify `main.py` — Remove Licence & Update Logic

**Files:**
- Modify: `d:\GitHub\OCR_Translator_GitHub_v4_open_source\main.py`

The current `main.py` (98 lines) does three things we must remove:
1. **Licence check** (line 63-64): `from licence_manager import check_licence_on_startup` + `check_licence_on_startup()`
2. **Auto-update** (lines 14, 23-44): `from update_applier import UpdateApplier` + staged update check
3. **Resource copier** (line 13): `from resource_copier import ensure_all_folders_in_main_directory`

**Step 1: Replace `main.py` with simplified version**

```python
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
```

**What changed:**
- Removed `from resource_copier import ensure_all_folders_in_main_directory` and its call
- Removed `from update_applier import UpdateApplier` and the entire staged update block
- Removed `from licence_manager import check_licence_on_startup` and `check_licence_on_startup()`

---

## Task 4: Modify `pyside_overlay.py` — Remove SetWindowDisplayAffinity

**Files:**
- Modify: `d:\GitHub\OCR_Translator_GitHub_v4_open_source\pyside_overlay.py`

There are 3 locations with `SetWindowDisplayAffinity`:
1. **`apply_anti_feedback()` method** (lines 251-263): imports `licence_manager`, sets affinity based on PRO status
2. **`freeze_for_screenshot()` method** (lines 265-274): sets affinity to `0x00`
3. **`unfreeze_after_screenshot()` method** (lines 276-280): calls `apply_anti_feedback()`

Also, **`show()` method** (lines 373-376) calls `apply_anti_feedback()`.

**Step 1: Replace `apply_anti_feedback()` with a no-op**

Replace lines 251-263:
```python
    def apply_anti_feedback(self):
        """No-op in open-source edition (no display affinity manipulation)."""
        pass
```

**Step 2: Remove SetWindowDisplayAffinity from `freeze_for_screenshot()`**

Replace lines 265-274:
```python
    def freeze_for_screenshot(self):
        """Freeze the overlay: block text updates."""
        self.is_frozen = True
        self.pending_text_update = None
```

**Step 3: Simplify `unfreeze_after_screenshot()`**

Replace lines 276-280:
```python
    def unfreeze_after_screenshot(self):
        """Unfreeze the overlay: allow text updates."""
        self.is_frozen = False
```

**Step 4: Simplify `show()` method**

Replace lines 373-376:
```python
    def show(self):
        super().show()
```

**What changed:**
- All `SetWindowDisplayAffinity` calls removed
- All `from licence_manager import is_pro_active` removed
- `apply_anti_feedback()` is now a no-op
- Freeze/unfreeze methods no longer touch display affinity

---

## Task 5: Modify `app_logic.py` — Remove PRO Imports & Logic

**Files:**
- Modify: `d:\GitHub\OCR_Translator_GitHub_v4_open_source\app_logic.py`

### Changes needed:

**5a: Remove licence_manager import (line 27)**

Replace:
```python
from licence_manager import is_pro_active
```
With: *(delete the line entirely)*

**5b: Remove update_checker import (line 37)**

Replace:
```python
from update_checker import UpdateChecker
```
With: *(delete the line entirely)*

**5c: Replace `apply_pro_overrides()` method (lines 705-735)**

Replace the entire method with:
```python
    def apply_pro_overrides(self):
        """Apply PRO overrides — open-source edition always locks PRO features.

        Keys locked:
        - source_area_colour, target_area_colour, target_text_colour
        - translation_model (forced to gemini_api, blocks DeepL)
        - auto_detect_enabled (Find Subtitles)
        - target_on_source_enabled (Target on Source)
        - capture_padding_enabled (Scan Wider)
        - custom_ocr_prompt_enabled (OCR Prompt)
        """
        log_debug("Applying PRO overrides (open-source edition) to instance attributes")

        self.source_colour = SIMPLE_CONFIG_SETTINGS['source_area_colour']
        self.target_colour = SIMPLE_CONFIG_SETTINGS['target_area_colour']
        self.target_text_colour = SIMPLE_CONFIG_SETTINGS['target_text_colour']
        self.translation_model = SIMPLE_CONFIG_SETTINGS['translation_model']
        self.auto_detect_enabled = SIMPLE_CONFIG_SETTINGS['auto_detect_enabled'] == 'True'
        self.target_on_source_enabled = SIMPLE_CONFIG_SETTINGS['target_on_source_enabled'] == 'True'
        self.capture_padding_enabled = SIMPLE_CONFIG_SETTINGS['capture_padding_enabled'] == 'True'
        self.custom_ocr_prompt_enabled = SIMPLE_CONFIG_SETTINGS['custom_ocr_prompt_enabled'] == 'True'

        log_debug("PRO overrides applied - PRO features locked to defaults")
```

> This removes the `if is_pro_active(): return` guard so PRO features are always locked.

**5d: Remove UpdateChecker initialization (line 382)**

Delete:
```python
        self.update_checker = UpdateChecker()
```

**5e: Remove auto-update scheduling (lines 473-483)**

Delete the entire block:
```python
        # Automatic update check for compiled version
        import sys
        is_compiled = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
        if is_compiled and self.check_for_updates_on_startup:
            ...
        elif is_compiled:
            ...
        else:
            ...
```

**5f: Remove SetWindowDisplayAffinity from `_show_discovery_notification()` (line 1451)**

Delete this single line inside the method:
```python
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
```

**5g: Remove `reload_from_ini()` call to `apply_pro_overrides()` is OK**

The `reload_from_ini()` method (line 781) calls `self.apply_pro_overrides()` which is fine — our modified version always locks PRO.

---

## Task 5A: Remove PRO Feature Backend Logic (CRITICAL)

> [!CAUTION]
> Without this task, someone could change `is_pro_active()` to `return True`, recompile, and get all PRO features for free. This task removes the actual implementation code so there is nothing to unlock.

**Strategy:** For each PRO feature, we remove/gut the backend implementation while keeping the UI widgets (grayed out) intact. The flags (`auto_detect_enabled`, `target_on_source_enabled`, etc.) remain in config/app_logic as `False`-hardcoded values — the code that *acts on* those flags is what we remove.

---

### 5A-1: Remove DeepL Translation Backend

**Files:** `handlers/translation_handler.py`

The entire DeepL integration lives in `translation_handler.py` (lines 47-648). Remove:

**Step 1:** Remove DeepL imports and constants (line 14):
```python
# DELETE:
from constants import DEEPL_BETA_LANGUAGES
```

**Step 2:** Remove DeepL context storage from `__init__` (lines 47-55):
```python
# DELETE these lines from __init__:
        # DeepL-specific context storage
        self.deepl_context_window = []
        self.deepl_current_source_lang = None
        self.deepl_current_target_lang = None
        
        # DeepL logging system
        self.deepl_log_file = 'DeepL_Translation_Long_Log.txt'
        self.deepl_log_lock = threading.Lock()
        self._initialize_deepl_log_file()
```

**Step 3:** Remove DeepL context clearing from session methods (lines 95-97, 106-108, 152-153):
```python
# DELETE from start_translation_session():
        self._clear_deepl_context()
        log_debug("DeepL context cleared for new translation session")

# DELETE from request_end_translation_session():
        self._clear_deepl_context()
        log_debug("DeepL context cleared on translation session end")

# DELETE from force_end_sessions_on_app_close():
        self._clear_deepl_context()
```

**Step 4:** Remove DeepL branch from `translate_text()` (lines 330-340):
```python
# REPLACE lines 330-340:
        if selected_model == 'deepl_api':
            if not self.app.DEEPL_API_AVAILABLE: return "DeepL API libraries not available."
            if not self.app.deepl_api_key.strip(): return "DeepL API key missing."
            if self.app.deepl_api_client is None:
                try:
                    import deepl
                    self.app.deepl_api_client = deepl.Translator(self.app.deepl_api_key.strip())
                except Exception as e:
                    return f"DeepL Client init error: {e}"
            source_lang, target_lang = self.app.deepl_source_lang, self.app.deepl_target_lang
            extra_params = {"model_type": "quality_optimized"}
# WITH:
        if selected_model == 'deepl_api':
            return "DeepL is not available in the open-source edition."
```

**Step 5:** Remove DeepL cache branches from `translate_text()` (lines 360-363, 390-393, 412-413, 423-426):
```python
# DELETE all `elif selected_model == 'deepl_api'` cache branches
# and the `self._deepl_translate(...)` call at line 413
```

**Step 6:** Delete ALL DeepL methods entirely (lines 155-648):
- `_clear_deepl_context()` (lines 156-164)
- `_build_deepl_context()` (lines 166-193)
- `_update_deepl_context()` (lines 195-211)
- `_initialize_deepl_log_file()` (lines 215-225)
- `_is_deepl_logging_enabled()` (lines 227-230)
- `_log_deepl_translation_call()` (lines 232-291)
- `_deepl_translate()` (lines 437-602)
- `get_deepl_usage()` (lines 604-648)

---

### 5A-2: Remove Find Subtitles (Auto-Detection/Discovery) Backend

**Files:** `app_logic.py`, `worker_threads.py`, `handlers/gemini_ocr_provider.py`

The discovery system is a complex multi-step pipeline. Remove the backend logic:

**Step 1:** In `app_logic.py`, gut these methods to no-ops:

```python
    def handle_auto_detection_result(self, ocr_result):
        """No-op in open-source edition (Find Subtitles is PRO)."""
        pass

    def _check_discovery_timer(self):
        """No-op in open-source edition."""
        pass

    def apply_discovery_to_target_overlay(self):
        """No-op in open-source edition."""
        pass

    def finish_discovery_phase(self):
        """No-op in open-source edition."""
        pass

    def show_discovery_notification(self):
        """No-op in open-source edition."""
        pass

    def _parse_discovery_coordinates(self, result_str):
        """No-op in open-source edition."""
        return None
```

This guts lines 990-1477 (the entire discovery pipeline). The methods still exist (preventing AttributeErrors) but do nothing.

**Step 2:** In `worker_threads.py`, remove auto-detect OCR prompt branching.

In `run_api_ocr()` (line 250), the `is_auto_detect` flag is read from `app.auto_detect_enabled`. Since `auto_detect_enabled` is always `False` in the open-source edition, this branch is already dead code. **No change strictly needed** — but for safety, hardcode it:

Replace line 250:
```python
        is_auto_detect = app.auto_detect_enabled
```
With:
```python
        is_auto_detect = False  # Find Subtitles disabled in open-source edition
```

**Step 3:** In `worker_threads.py` `process_api_ocr_response()`, remove the discovery result handling block (lines 322-357).

Replace the entire `if is_auto_detect:` block with:
```python
        # Auto-detect / Find Subtitles disabled in open-source edition
```

**Step 4:** In `handlers/gemini_ocr_provider.py`, remove the auto-detect prompt variant.

In `_make_api_call()` (lines 142-156), replace the `if is_auto_detect:` branch:
```python
        if is_auto_detect:
            # Find Subtitles disabled in open-source edition
            prompt = "1. Transcribe the text from the image exactly as it appears. Do not correct, rephrase, or alter the words in any way. Provide a literal and verbatim transcription of all text in the image. Don't return anything else.\n2. If there is no text in the image, you MUST return exactly: <EMPTY>."
        else:
```

This removes the sophisticated auto-detection prompt that instructs Gemini to detect bounding boxes.

---

### 5A-3: Remove Scan Wider (Capture Padding) Backend

**Files:** `worker_threads.py`

The capture padding logic is in `run_capture_thread()` at lines 104-121.

**Replace lines 104-121 with:**
```python
            # Scan Wider (capture_padding) disabled in open-source edition
            # Capture exactly the source overlay area, no expansion
```

This removes the code that expands the capture area beyond the source overlay boundaries.

---

### 5A-4: Remove Target on Source Backend

**Files:** `app_logic.py`

The Target on Source alignment logic is spread across multiple methods. Gut them:

```python
    def _align_target_to_source(self):
        """No-op in open-source edition (Target on Source is PRO)."""
        pass

    def update_target_on_source_btn_text(self):
        """No-op in open-source edition."""
        pass
```

Also, remove the `_align_target_to_source()` calls from:
- `handle_source_manual_move()` (line 1345): delete the `if target_on_source_enabled: _align_target_to_source()` block
- `_process_source_manual_move()` (line 1400): same
- `_process_target_manual_move()` (lines 1415-1419): delete the `target_on_source_enabled = False` auto-disable block

And in `gui_v4.py` `save_all_settings()` (lines 1623-1626), remove the immediate alignment call:
```python
# DELETE:
        if t.target_on_source_enabled and not getattr(self, '_is_loading', False):
            if hasattr(t, '_align_target_to_source'):
                t._align_target_to_source()
```

---

### 5A-5: Remove Colour Pickers Backend

**Files:** `handlers/ui_interaction_handler.py`

Gut the `choose_color_for_settings()` method (lines 24-73):

```python
    def choose_color_for_settings(self, color_type):
        """No-op in open-source edition (colour pickers are PRO)."""
        pass
```

---

### 5A-6: Remove OCR Custom Prompt Backend

**Files:** `handlers/gemini_ocr_provider.py`

In `_make_api_call()` (lines 136-140), remove custom OCR prompt injection:

Replace:
```python
        ocr_enabled = getattr(self.app, 'custom_ocr_prompt_enabled', True)
        custom_ocr = getattr(self.app, 'custom_ocr_prompt_text', '').strip()
        custom_inject = ""
        if ocr_enabled and custom_ocr:
            custom_inject = f"{custom_ocr}"
```
With:
```python
        custom_inject = ""  # OCR Prompt disabled in open-source edition
```

And in the regional OCR prompt (line 159), remove `{custom_inject}` from the prompt string.

---

### 5A-7: Remove DeepL Import from `app_logic.py`

In `app_logic.py`, remove:
- Line 57-61: `import deepl` / `DEEPL_API_AVAILABLE` block — replace with `DEEPL_API_AVAILABLE = False`
- All `deepl_api_client` initialization and references

---

### Verification for Task 5A

| Check | Expected |
|-------|----------|
| `rg "_deepl_translate\|_build_deepl_context\|_update_deepl_context" handlers/` | **No results** |
| `rg "handle_auto_detection_result\|finish_discovery_phase\|_parse_discovery_coordinates" app_logic.py` | Only no-op stubs |
| `rg "padding_pct\|pad_w\|pad_h" worker_threads.py` | **No results** |
| `rg "_align_target_to_source" app_logic.py` | Only no-op stub |
| `rg "choose_color_for_settings" handlers/ui_interaction_handler.py` | Only no-op stub |
| `rg "custom_inject" handlers/gemini_ocr_provider.py` | Only `custom_inject = ""` |
| Someone changes `is_pro_active()` to `True` and compiles? | DeepL returns error, Find Subtitles/Scan Wider/TOS/Colours/OCR Prompt **do nothing** |

---

## Task 6: Modify `gui_v4.py` — Remove Licence Imports, Redesign About Tab

**Files:**
- Modify: `d:\GitHub\OCR_Translator_GitHub_v4_open_source\gui_v4.py`

This is the largest file (3094 lines) with the most PRO references. Changes:

### 6a: Replace licence_manager import (lines 13-16)

Replace:
```python
from licence_manager import (
    is_pro_active, set_pro_active, verify_licence_online,
    save_licence_data, load_licence_data, get_machine_id, MAX_ACTIVATIONS, get_pro_uses
)
```
With:
```python
# Open-source edition: PRO features are always disabled
def is_pro_active():
    return False
```

### 6b: Replace all `is_pro_active()` calls throughout the file

Every call to `is_pro_active()` already returns `False` from our stub (6a), so no code changes are needed for the ~20 call sites. The GUI will correctly show all PRO widgets as grayed out.

### 6c: Simplify `apply_pro_state()` method (lines 1280-1357)

The method already handles the `is_pro = False` case correctly (it disables all PRO widgets). Since `is_pro_active()` always returns `False`, the `if is_pro: return` branch will never execute, but we can leave it for clarity or simplify. **No change needed** — it works correctly as-is.

### 6d: Remove `activate_pro_licence()` method (lines 1470-1550)

Replace the entire method with:
```python
    @Slot()
    def activate_pro_licence(self):
        """No-op in open-source edition."""
        pass
```

### 6e: Simplify `update_pro_status_label()` method (lines 1443-1468)

Replace with:
```python
    def update_pro_status_label(self):
        """No-op in open-source edition."""
        pass
```

### 6f: Redesign the About tab PRO section (lines 2724-2773)

Replace the entire `# -- GROUP 2: PRO Licence --` block with a GitHub Releases link:

```python
        # -- GROUP 2: PRO Information (Open-Source Edition) --
        self.grp_pro = QGroupBox()
        l_pro = QVBoxLayout(self.grp_pro)
        l_pro.setContentsMargins(self.dp(15), self.dp(20), self.dp(15), self.dp(15))
        l_pro.setSpacing(self.dp(12))
        
        self.pro_info_label = QLabel()
        self.pro_info_label.setWordWrap(True)
        self.pro_info_label.setTextFormat(Qt.RichText)
        self.pro_info_label.setOpenExternalLinks(True)
        self.pro_info_label.setText(
            '<p style="font-size: 13px; line-height: 1.6;">'
            'This is the <b>open-source edition</b> of Game-Changing Translator. '
            'PRO features (DeepL, Find Subtitles, Scan Wider, Target on Source, '
            'colour pickers, OCR Prompt) are available exclusively in the '
            '<b>compiled version</b> with a purchased licence key.</p>'
            '<p style="font-size: 13px; line-height: 1.6;">'
            '👉 <a href="https://github.com/tomkam1702/OCR-Translator/releases" '
            'style="color: #2196F3; text-decoration: underline;">'
            'Download the compiled version from GitHub Releases</a></p>'
        )
        l_pro.addWidget(self.pro_info_label)
        
        # Dummy attributes to prevent AttributeErrors in retranslate_ui
        self.pro_key_entry = type('obj', (object,), {
            'setEnabled': lambda self, x: None,
            'setPlaceholderText': lambda self, x: None,
            'setText': lambda self, x: None,
            'text': lambda self: '',
        })()
        self.activate_pro_btn = type('obj', (object,), {
            'setEnabled': lambda self, x: None,
            'setText': lambda self, x: None,
        })()
        self.pro_status_label = type('obj', (object,), {
            'setText': lambda self, x: None,
            'setStyleSheet': lambda self, x: None,
        })()
        
        l_outer_about.addWidget(self.grp_pro)
```

### 6g: Remove `check_updates_manual()` references

Search for `check_updates_manual` in `gui_v4.py`. The button `self.check_updates_btn` calls this method. We need to replace it or make it a no-op.

Find the `check_updates_manual` method and replace with:
```python
    def check_updates_manual(self):
        """Open GitHub releases page in browser (open-source edition)."""
        QDesktopServices.openUrl(QUrl("https://github.com/tomkam1702/OCR-Translator/releases"))
```

### 6h: Remove `update_licence_display()` body (lines 1552-1565)

Replace the method body so it always shows FREE:
```python
    def update_licence_display(self):
        """Always show FREE in open-source edition."""
        if not self.translator or not hasattr(self, 'licence_status_label'):
            return
            
        prefix = self.translator.ui_lang.get_label('status_licence', 'Licence:')
        text = f'{prefix} <span style="color: #27AE60; font-weight: bold;">FREE</span> (Open Source)'
        self.licence_status_label.setText(text)
```

---

## Task 7: Modify `handlers/ui_interaction_handler.py` — Remove PRO Import

**Files:**
- Modify: `d:\GitHub\OCR_Translator_GitHub_v4_open_source\handlers\ui_interaction_handler.py`

### 7a: Replace licence_manager import (line 12)

Replace:
```python
from licence_manager import is_pro_active
```
With:
```python
# Open-source edition: PRO features are always disabled
def is_pro_active():
    return False
```

No other changes needed in this file — the `save_settings()` method at line 343 calls `is_pro_active()` which will now return `False`, meaning PRO-locked keys won't be written to the ini (which is correct).

---

## Task 8: Cleanup & Git Publication

### 8a: Update `.gitignore`

**Files:**
- Modify: `d:\GitHub\OCR_Translator_GitHub_v4_open_source\.gitignore`

Remove references to compilation-specific files that no longer exist:
- Remove `compile_app.bat` line
- Remove `*licence*.json` line (no licence files in open-source)
- Keep other entries as they are

Add:
```
# Open-source edition: no compilation
*.spec
compile_app.*
```

### 8b: Update `README.md`

Review `README.md` and ensure it clearly states:
- This is the open-source edition
- PRO features require the compiled version + licence key
- Link to GitHub Releases for the compiled version
- Link to Gumroad for licence purchase

### 8c: Initialize fresh Git repo and push as single commit

```powershell
cd "d:\GitHub\OCR_Translator_GitHub_v4_open_source"
git init
git add .
git commit -m "v4.0.0 — Open Source Edition"
git remote add origin https://github.com/tomkam1702/OCR-Translator.git
git push --force origin main
```

> **IMPORTANT:** `git push --force` replaces the ENTIRE remote history with this single commit. This means:
> - The old v3.9.6 history disappears from the main branch
> - Existing forks retain the old history (this is normal and unavoidable)
> - No intermediate commits exposing PRO code will be visible
> - Consider making a backup tag of v3.9.6 before force-pushing if you want to preserve a reference

### 8d: Alternative safer approach (recommended)

If you want to keep v3.9.6 accessible as a tag but still have a clean history:

```powershell
# First, in the OLD repo — create a preservation tag
cd "d:\GitHub\OCR_Translator_GitHub_v4_new_GUI"
git tag v3.9.6-archive
git push origin v3.9.6-archive

# Then push the new open-source edition
cd "d:\GitHub\OCR_Translator_GitHub_v4_open_source"
git init
git add .
git commit -m "v4.0.0 — Open Source Edition"
git remote add origin https://github.com/tomkam1702/OCR-Translator.git
git push --force origin main
```

---

## Verification Checklist

After all tasks are complete, verify:

| Check | Expected |
|-------|----------|
| `rg "licence_manager" *.py handlers/*.py` | **No results** |
| `rg "SetWindowDisplayAffinity" *.py` | **No results** |
| `rg "is_pro_active" *.py handlers/*.py` | Only local stubs in `gui_v4.py` and `ui_interaction_handler.py` |
| `rg "compile_app" .` | **No results** |
| `rg "GUMROAD" .` | **No results** |
| `rg "verify_licence" .` | **No results** |
| `rg "update_applier\|update_checker\|UpdateChecker\|UpdateApplier" *.py` | **No results** |
| `rg "_deepl_translate\|_build_deepl_context" handlers/` | **No results** (DeepL backend removed) |
| `rg "padding_pct\|pad_w\|pad_h" worker_threads.py` | **No results** (Scan Wider backend removed) |
| `rg "custom_inject" handlers/gemini_ocr_provider.py` | Only `custom_inject = ""` (OCR Prompt gutted) |
| File `licence_manager.py` exists? | **No** |
| File `compile_app.py` exists? | **No** |
| File `nuitka_compat.py` exists? | **Yes** (stub only) |
| `python main.py` runs successfully? | **Yes** — app starts in FREE mode |
| All PRO widgets grayed out? | **Yes** |
| About tab shows GitHub Releases link? | **Yes** |
| About tab has NO licence key input field? | **Yes** |
| Bottom status bar shows "Licence: FREE (Open Source)"? | **Yes** |
| Change `is_pro_active()` to `True` and run? | PRO features **still don't work** — backend removed |

---

## Files Summary

### Files to DELETE
| File | Reason |
|------|--------|
| `licence_manager.py` | Licence verification logic (trade secret) |
| `licence_data*.json` | Licence data files |
| `compile_app.py` | Compilation script |
| `compile_app.7z` | Compilation archive |
| `GameChangingTranslator.spec` | PyInstaller/Nuitka spec |
| `setup.py` | Build setup |
| `resource_copier.py` | Compilation resource copier |
| `update_applier.py` | Auto-update system |
| `update_checker.py` | Auto-update system |
| `install_dependencies.bat` | Installer batch |
| All `dist_*` directories | Build outputs |
| All `*_Log*.txt`, `*_cache*.txt`, `*.log` | Runtime files |
| `ocr_translator_config.ini` | User config |
| `custom_prompt*.txt`, `custom_ocr_prompt*.txt` | User prompts |

### Files to MODIFY
| File | Changes |
|------|---------|
| `nuitka_compat.py` | Replace with minimal stub (get_base_dir only) |
| `main.py` | Remove licence check, update system, resource copier |
| `pyside_overlay.py` | Remove all SetWindowDisplayAffinity + licence import |
| `app_logic.py` | Remove is_pro_active import, update_checker, lock PRO permanently, gut discovery/TOS methods |
| `gui_v4.py` | Replace licence import with stub, redesign About tab, simplify PRO methods |
| `handlers/ui_interaction_handler.py` | Replace licence import with stub, gut colour picker method |
| `handlers/translation_handler.py` | Remove entire DeepL backend (translate, context, logging, usage) |
| `worker_threads.py` | Remove Scan Wider padding logic, hardcode auto_detect=False, remove discovery handler |
| `handlers/gemini_ocr_provider.py` | Remove auto-detect prompt, remove custom OCR prompt injection |
| `.gitignore` | Clean up compilation references |
| `README.md` | Add open-source edition notice |

### Files UNCHANGED (no modifications needed)
| File | Reason |
|------|---------|
| `config_manager.py` | No PRO/licence references |
| `constants.py` | No changes needed |
| `handlers/gemini_provider.py` | No PRO references |
| `handlers/llm_provider_base.py` | No PRO references |
| `handlers/ocr_provider_base.py` | No PRO references |
| `handlers/cache_manager.py` | No PRO references |
| `handlers/display_manager.py` | No PRO references |
| `handlers/hotkey_handler.py` | No PRO references |
| `handlers/statistics_handler.py` | No PRO references |
| `language_manager.py` | No PRO references |
| `language_ui.py` | No PRO references |
| `overlay_manager.py` | No PRO references |
| `logger.py` | No PRO references |
| `qt_dialogs.py` | No PRO references |
| `translation_utils.py` | No PRO references |
| `unified_translation_cache.py` | No PRO references |
| `resource_handler.py` | No PRO references |
| `signals.py` | No PRO references |
| All `assets/*` | Static resources |
| All `resources/*` | CSV data files |
| All `docs/*` | Documentation |
