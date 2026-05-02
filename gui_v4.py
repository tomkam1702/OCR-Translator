import sys
import os
import ctypes
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QComboBox, 
                             QLineEdit, QToolBar, QStatusBar, QFrame, QFormLayout, 
                             QSizePolicy, QScrollArea, QCheckBox, QGridLayout, QTextEdit, QTabWidget, QGroupBox, QSpacerItem)
from PySide6.QtCore import Qt, QSize, QMetaObject, Signal, QTimer, Slot, QUrl
from PySide6.QtGui import QIcon, QAction, QFont, QColor, QFontDatabase, QDesktopServices
import nuitka_compat
from logger import log_debug
from qt_dialogs import askcolor


# --- Modern CustomSpinBox (Replaces unreliable system SpinBoxes) ---
class CustomSpinBox(QWidget):
    valueChanged = Signal(float)
    
    def __init__(self, min_val=0, max_val=100, step=1, is_double=False, decimals=2, parent=None):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.is_double = is_double
        self.decimals = decimals
        self._value = min_val
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.btn_minus = QPushButton("-")
        self.btn_plus = QPushButton("+")
        
        self.btn_minus.setCursor(Qt.PointingHandCursor)
        self.btn_plus.setCursor(Qt.PointingHandCursor)
        
        self.lbl_value = QLabel(self._format_val(self._value))
        self.lbl_value.setAlignment(Qt.AlignCenter)
        
        # Enforce proportions - buttons should not grow indefinitely, they act as icons
        self.btn_minus.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.btn_plus.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.lbl_value.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        layout.addWidget(self.btn_minus)
        layout.addWidget(self.lbl_value)
        layout.addWidget(self.btn_plus)
        
        self.btn_minus.clicked.connect(self.decrement)
        self.btn_plus.clicked.connect(self.increment)
        
    def _format_val(self, val):
        if self.is_double: return f"{val:.{self.decimals}f}"
        return str(int(val))
        
    def value(self):
        return self._value if self.is_double else int(self._value)
        
    def setValue(self, val):
        old_val = self._value
        self._value = max(self.min_val, min(self.max_val, float(val)))
        if not self.is_double: self._value = int(self._value)
        self.lbl_value.setText(self._format_val(self._value))
        if old_val != self._value:
            self.valueChanged.emit(self._value)
        
    def setRange(self, min_val, max_val):
        self.min_val = min_val
        self.max_val = max_val
        self.setValue(self._value)
        
    def setSingleStep(self, step):
        self.step = step
        
    def setDecimals(self, decimals):
        self.decimals = decimals
        self.lbl_value.setText(self._format_val(self._value))
        
    def decrement(self):
        new_val = self._value - self.step
        if self.is_double: new_val = round(new_val, self.decimals)
        self.setValue(new_val)
        
    def increment(self):
        new_val = self._value + self.step
        if self.is_double: new_val = round(new_val, self.decimals)
        self.setValue(new_val)
# ------------------------------------------------------------------------

class SegmentedToggle(QWidget):
    valueChanged = Signal(int)

    def __init__(self, parent=None, active_color="#2196F3"):
        super().__init__(parent)
        self.active_color = active_color
        self._current_index = 0
        self._dp_func = parent.dp if parent and hasattr(parent, 'dp') else lambda x: x
        self._scaled_font_size = parent.scaled_font_size if parent and hasattr(parent, 'scaled_font_size') else 14

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(self._dp_func(5)) # Slight spacing between merged buttons

        self.btn1 = QPushButton()
        self.btn2 = QPushButton()
        
        # Use standard app scaling for icons (base 20px)
        fs = self._dp_func(20)
            
        for btn in [self.btn1, self.btn2]:
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            btn.setIconSize(QSize(fs, fs))
            btn.setFont(QFont('Segoe UI', parent.scaled_font_size, QFont.Weight.Bold))

        self.layout.addWidget(self.btn1)
        self.layout.addWidget(self.btn2)

        self.btn1.clicked.connect(self.on_btn_clicked)
        self.btn2.clicked.connect(self.on_btn_clicked)

    def on_btn_clicked(self):
        new_index = 1 if self._current_index == 0 else 0
        self.setCurrentIndex(new_index, emit=True)

    def set_labels(self, label1, label2):
        self.btn1.setText(label1)
        self.btn2.setText(label2)
        
    def set_icons(self, icon1, icon2):
        self.btn1.setIcon(icon1)
        self.btn2.setIcon(icon2)
        self._update_styles()

    def currentIndex(self):
        return self._current_index

    def setCurrentIndex(self, index, emit=False):
        if self._current_index == index and not emit:
            return
        self._current_index = index
        self._update_styles()
        if emit:
            self.valueChanged.emit(index)

    def _update_styles(self):
        dp = self._dp_func
        rad = dp(4)
        fs = 11 # Default fallback
        if hasattr(self.parent(), 'scaled_font_size'):
            # Increase base font size slightly to match QToolBar actions
            fs = round(self.parent().scaled_font_size * 1.15)
        
        # Base style: Consistent with standard app scaling
        style_base = f"""
            QPushButton {{
                border: none;
                background-color: transparent;
                padding: {dp(4)}px {dp(10)}px;
                font-size: {self._scaled_font_size}pt;
                font-weight: normal;
                color: #757575;
                font-family: 'Segoe UI';
            }}
            QPushButton:hover {{
                background-color: #F0F0F0;
            }}
        """
        
        # Active: bold black, NO border
        active_style = f"""
            QPushButton {{
                color: #333333;
                font-weight: bold;
                border: none;
            }}
        """

        s1 = style_base
        if self._current_index == 0: s1 += active_style
            
        s2 = style_base
        if self._current_index == 1: s2 += active_style

        self.btn1.setStyleSheet(s1)
        self.btn2.setStyleSheet(s2)

class StatusToggleButton(QPushButton):
    """A button that supports an 'active' state with a blue border and no background."""
    def __init__(self, text, active_color="#4CAF50", parent=None):
        super().__init__(text, parent)
        self.active_color = active_color
        self._is_active = False
        self._dp_func = parent.dp if parent and hasattr(parent, 'dp') else lambda x: x
        self._scaled_font_size = parent.scaled_font_size if parent and hasattr(parent, 'scaled_font_size') else 14
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        # Consistent icon scaling (base 20px)
        fs = self._dp_func(20)
        self.setIconSize(QSize(fs, fs))
        self.setFont(QFont('Segoe UI', parent.scaled_font_size, QFont.Weight.Bold))
        
        self.update_appearance()

    def set_active(self, active):
        self._is_active = active
        self.update_appearance()

    def update_appearance(self):
        dp = self._dp_func
        
        style = f"""
            QPushButton {{
                border: none;
                background-color: transparent;
                padding: {dp(4)}px {dp(10)}px;
                font-size: {self._scaled_font_size}pt;
                font-weight: normal;
                color: #757575;
                font-family: 'Segoe UI';
            }}
            QPushButton:hover {{
                background-color: #F0F0F0;
            }}
        """
        
        if self._is_active:
            style += f"""
                QPushButton {{
                    color: #333333;
                    font-weight: bold;
                }}
            """
        
        self.setStyleSheet(style)

# ------------------------------------------------------------------------

class HelpButton(QPushButton):
    """Przycisk z ikoną pomocy, który po kliknięciu otwiera podręcznik użytkownika we wskazanym miejscu."""
    def __init__(self, anchor="", icon_name="info", parent=None, tooltip_key=None):
        super().__init__(parent)
        self.anchor = anchor
        self.icon_name = icon_name
        self.tooltip_key = tooltip_key
        
        # Pobieranie funkcji skalowania dp() od rodzica (MainWindowV4)
        self.dp = parent.dp if parent and hasattr(parent, "dp") else lambda x: x
        
        self.setFixedSize(self.dp(28), self.dp(28))
        self.setIconSize(QSize(self.dp(24), self.dp(24)))
        self.setCursor(Qt.PointingHandCursor)
        self.update_tooltip()

        # Load icon safely
        try:
            import nuitka_compat
            import os
            base_dir = nuitka_compat.get_base_dir()
            if self.icon_name.endswith('.svg'):
                icon_path = os.path.join(base_dir, "assets", self.icon_name)
            else:
                icon_path = os.path.join(base_dir, "assets", f"{self.icon_name}_flat.svg")
            if os.path.exists(icon_path):
                self.setIcon(QIcon(icon_path))
            else:
                self.setText("ℹ")
        except Exception:
            self.setText("ℹ")
            
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 16px;
                border-radius: 4px;
                color: #1565C0;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
            QPushButton:pressed {
                background-color: #d1d5db;
            }
        """)
        self.clicked.connect(self.open_manual)

    def update_tooltip(self):
        mw = self.window()
        if mw and hasattr(mw, "translator") and mw.translator:
            lng = mw.translator.ui_lang
            if self.tooltip_key:
                self.setToolTip(lng.get_label(self.tooltip_key))
            elif self.icon_name in ["idea", "lightbulb"]:
                self.setToolTip(lng.get_label('tooltip_help_idea', 'Read in-depth guide'))
            else:
                self.setToolTip(lng.get_label('tooltip_help_info', 'View in user manual'))
        else:
            if self.tooltip_key:
                self.setToolTip("Info") # Simple fallback
            elif self.icon_name in ["idea", "lightbulb"]:
                self.setToolTip("Read in-depth guide")
            else:
                self.setToolTip("View in user manual")

    def open_manual(self):
        import os
        import nuitka_compat
        base_dir = nuitka_compat.get_base_dir()
        manual_path = os.path.join(base_dir, "docs", "user-manual.html")
        if os.path.exists(manual_path):
            url_str = f"file:///{manual_path.replace(os.sep, '/')}"
            if self.anchor:
                url_str += f"#{self.anchor}"
            QDesktopServices.openUrl(QUrl(url_str))
        else:
            print(f"Manual not found at: {manual_path}")



class ScreenshotToast(QLabel):
    """Transient notification widget for screenshot confirmation."""
    def __init__(self, message):
        super().__init__(None)
        self.setText(message)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(30, 30, 30, 220);
                color: #00FFCC;
                border: 1px solid #00FFCC;
                border-radius: 12px;
                padding: 14px 20px;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_DeleteOnClose)  # prevent memory leak on repeated screenshots

    def show_and_fade(self):
        screen = QApplication.primaryScreen().availableGeometry()  # excludes taskbar
        self.adjustSize()
        self.move(screen.right() - self.width() - 20, screen.bottom() - self.height() - 20)
        self.show()
        QTimer.singleShot(2500, self.close)

class MainWindowV4(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game-Changing Translator v4")
        self.translator = None
        self.source_overlay = None
        self.target_overlay = None
        self._pending_colors = {}
        self._is_loading = True
        self._is_toggling_visibility = False
        
        # Set Application Icon
        icon_path = os.path.join(nuitka_compat.get_base_dir(), "assets", "app_icon_shadow.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.init_dpi_scaling()
        self.init_ui()
        self.bind_auto_save()

    def get_system_fonts(self):
        db = QFontDatabase()
        all_fonts = sorted(db.families())
        preferred_fonts = ['Arial', 'Times New Roman', 'Calibri', 'Cambria', 'Segoe UI']
        final_fonts = []
        for font in preferred_fonts:
            if font in all_fonts:
                final_fonts.append(font); all_fonts.remove(font)
        final_fonts.extend(all_fonts)
        return final_fonts

    def synchronize_combo_widths(self):
        """Ensure all model and context combos have the same width based on the widest one."""
        combos = [self.translation_model_combo, self.ocr_model_combo, 
                  self.gemini_context_combo, self.deepl_context_combo]
        
        # Reset to allow natural size hint calculation
        for c in combos:
            c.setMinimumWidth(0)
            
        # Force a layout update to ensure size hints are fresh
        QApplication.processEvents()
            
        # Find maximum width required
        max_w = 0
        for c in combos:
            max_w = max(max_w, c.sizeHint().width())
            
        # Apply the uniform width
        if max_w > 0:
            for c in combos:
                c.setMinimumWidth(max_w)

    def synchronize_language_combo_widths(self):
        """Ensure Source and Target language combos have the same width based on the widest content."""
        combos = [self.source_lang_combo, self.target_lang_combo]
        
        # Reset to allow natural size hint calculation
        for c in combos:
            c.setMinimumWidth(0)
            c.updateGeometry()
            
        # Force layout updates to ensure size hints are fresh
        QApplication.processEvents()
        QApplication.sendPostedEvents()
            
        # Find maximum width required
        max_w = 0
        for c in combos:
            hint_w = c.sizeHint().width()
            max_w = max(max_w, hint_w)
            
        # Apply the uniform width
        if max_w > 0:
            for c in combos:
                c.setMinimumWidth(max_w)

    def retranslate_ui(self):
        if not self.translator: return
        self.setWindowTitle(self.translator.ui_lang.get_label('app_title', 'Game-Changing Translator v4'))
        
        already_loading = getattr(self, '_is_loading', False)
        self._is_loading = True
        lng = self.translator.ui_lang
        
        # Actions/Buttons
        # Update Segmented Toggles and Settings Button with SVG icons
        self.config_mode_btn.set_labels(
            lng.get_label('config_mode_simple', 'Simple'),
            lng.get_label('config_mode_advanced', 'Custom')
        )
        self.config_mode_btn.set_icons(
            QIcon("assets/mode_simple.svg"),
            QIcon("assets/mode_custom.svg")
        )
        
        self.settings_visibility_btn.setText(lng.get_label('settings_tab_title', 'Settings'))
        self.settings_visibility_btn.setIcon(QIcon("assets/settings.svg"))
        
        # Update standard toolbar actions with SVG icons
        self.action_source.setText(lng.get_label('select_source_btn', 'Select Source Area (OCR)'))
        self.action_source.setIcon(QIcon("assets/source.svg"))
        
        self.action_target.setText(lng.get_label('select_target_btn', 'Select Target Area (Translation)'))
        self.action_target.setIcon(QIcon("assets/target.svg"))
        
        self.show_gemini_key_btn.setText(lng.get_label('ui_visibility_show', 'Show'))
        self.show_deepl_key_btn.setText(lng.get_label('ui_visibility_show', 'Show'))
        self.lbl_gemini_key.setText(lng.get_label('gemini_api_key_label', 'Gemini API Key:'))
        self.lbl_deepl_key.setText(lng.get_label('deepl_api_key_label', 'DeepL API Key:'))
        
        # Status & Button state
        self.update_status_display()
        self.update_licence_display()
        self.update_about_text()
        
        self.save_settings_btn.setText(" " + lng.get_label('save_settings_btn', 'Save Settings'))
        save_icon_path = os.path.join(nuitka_compat.get_base_dir(), "assets", "floppy_disk_flat.svg")
        if os.path.exists(save_icon_path):
            self.save_settings_btn.setIcon(QIcon(save_icon_path))
            self.save_settings_btn.setIconSize(QSize(self.dp(20), self.dp(20)))
        else:
            self.save_settings_btn.setIcon(QIcon())
        
        # Main Tab labels
        self.lbl_source_lang.setText(lng.get_label('source_lang_label', 'Source Language:'))
        self.lbl_target_lang.setText(lng.get_label('target_lang_label', 'Target Language:'))
        self.lbl_gemini_key.setText(lng.get_label('gemini_api_key_label', 'Gemini API Key:'))
        self.lbl_deepl_key.setText(lng.get_label('deepl_api_key_label', 'DeepL API Key:'))
        
        # Tab Titles
        # Tab Titles - New Order: Settings, Costs, Shortcuts, About
        self.tab_widget.setTabText(0, lng.get_label('settings_tab_title', 'Settings'))
        self.tab_widget.setTabText(1, lng.get_label('custom_prompt_tab_title', 'Custom Prompt'))
        self.tab_widget.setTabText(2, lng.get_label('api_usage_tab_title', 'API Usage'))
        self.tab_widget.setTabText(3, lng.get_label('shortcuts_tab_title', 'Shortcuts'))
        self.tab_widget.setTabText(4, lng.get_label('about_tab_title', 'About'))
        
        # Custom Prompt Tab
        if hasattr(self, 'grp_custom_trans'):
            self.grp_custom_trans.setTitle(lng.get_label('custom_prompt_translation_title', 'Translation Prompt'))
            self.grp_custom_ocr.setTitle(lng.get_label('custom_prompt_ocr_title', 'OCR Prompt'))
            self.lbl_cp_trans_info.setText(lng.get_label('custom_prompt_info', 'This text will be added...'))
            self.lbl_cp_ocr_info.setText(f"<sup style='color: gray; font-style: normal;'>PRO</sup> {lng.get_label('custom_prompt_ocr_info', 'This text will be added...')}")
            self.save_cp_btn.setText(lng.get_label('save_btn', 'Save'))
            self.reload_cp_btn.setText(lng.get_label('reload_btn', 'Reload'))
            self.save_ocr_cp_btn.setText(lng.get_label('save_btn', 'Save'))
            self.reload_ocr_cp_btn.setText(lng.get_label('reload_btn', 'Reload'))
            
            enable_lbl = lng.get_label('custom_prompt_enabled_label', 'Enabled')
            self.custom_prompt_trans_enabled_check.setText(enable_lbl)
            self.custom_prompt_ocr_enabled_check.setText(enable_lbl)
        
        # API Key Toggle Buttons
        show_lbl = lng.get_label('show_btn', 'Show')
        hide_lbl = lng.get_label('hide_btn', 'Hide')
        
        for btn, entry in [(self.show_gemini_key_btn, self.gemini_api_key_entry), 
                          (self.show_deepl_key_btn, self.deepl_api_key_entry)]:
            is_hidden = (entry.echoMode() == QLineEdit.Password)
            btn.setText(show_lbl if is_hidden else hide_lbl)
            
        # API Key Placeholders
        self.gemini_api_key_entry.setPlaceholderText(lng.get_label('gemini_api_key_placeholder', 'Mandatory field'))
        self.deepl_api_key_entry.setPlaceholderText(lng.get_label('deepl_api_key_placeholder', 'Optional field'))
        
        # Settings Groups & Elements
        self.grp_models.setTitle(lng.get_label('models_and_context_section_label', 'Models and Context'))
        self.lbl_translation_model.setText(lng.get_label('translation_model_label', 'Translation Model:'))
        self.lbl_ocr_model.setText(lng.get_label('ocr_model_label', 'OCR Model:'))
        self.lbl_gemini_context.setText(lng.get_label('gemini_context_window_label', 'Context Window:'))
        
        current_g = self.gemini_context_combo.currentData()
        self.gemini_context_combo.clear()
        for i in range(6):
            self.gemini_context_combo.addItem(lng.get_label(f'gemini_context_window_{i}', str(i)), i)
        if current_g is not None: self.gemini_context_combo.setCurrentIndex(self.gemini_context_combo.findData(current_g))
            
        current_d = self.deepl_context_combo.currentData()
        self.deepl_context_combo.clear()
        for i in range(4):
            lbl = lng.get_label(f'deepl_context_window_{i}', lng.get_label(f'gemini_context_window_{i}', str(i)))
            self.deepl_context_combo.addItem(lbl, i)
        if current_d is not None: self.deepl_context_combo.setCurrentIndex(self.deepl_context_combo.findData(current_d))
            
        self.lbl_deepl_context.setText(lng.get_label('deepl_context_window_label', 'Context Window:'))
        
        self.grp_behavior.setTitle(lng.get_label('behavior_frame_title', 'App Behaviour'))
        self.update_auto_detect_label()
        self.update_capture_padding_label()
        self.update_target_on_source_label()
        self.update_debug_log_label()
        self.update_info_tooltips()
        
        self.keep_linebreaks_check.setText(lng.get_label('keep_linebreaks_label', 'Keep Linebreaks'))
        self.lbl_scan_interval.setText(lng.get_label('scan_interval_label', 'Scan Interval (ms):'))
        self.lbl_clear_timeout.setText(lng.get_label('clear_timeout_label', 'Clear Translation Timeout (s):'))
        self.lbl_discovery_time.setText(lng.get_label('discovery_timeout_label', 'Time:'))
        self.lbl_discovery_unit.setText(lng.get_label('discovery_timeout_unit', 'seconds'))
        
        self.grp_appearance.setTitle(lng.get_label('appearance_frame_title', 'Appearance & Formatting'))
        is_simple = getattr(self.translator, 'config_mode', '') == 'Simple'
        self.lbl_source_color.setText(f"{lng.get_label('source_color_label', 'Source Area Colour:')} <sup style='color: gray;'>PRO</sup>")
        self.lbl_target_color.setText(f"{lng.get_label('target_color_label', 'Target Area Colour:')} <sup style='color: gray;'>PRO</sup>")
        self.lbl_target_text_color.setText(f"{lng.get_label('target_text_color_label', 'Target Text Colour:')} <sup style='color: gray;'>PRO</sup>")
        self.source_color_btn.setText(lng.get_label('choose_color_btn', 'Choose Colour'))
        self.target_color_btn.setText(lng.get_label('choose_color_btn', 'Choose Colour'))
        self.target_text_color_btn.setText(lng.get_label('choose_color_btn', 'Choose Colour'))
        
        self.lbl_font_size.setText(lng.get_label('font_size_label', 'Target Window Font Size:'))
        self.lbl_font_type.setText(lng.get_label('font_type_label', 'Target Window Font Type:'))
        
        self.lbl_opacity_bg.setText(lng.get_label('opacity_background_label', 'Opacity Background:'))
        self.lbl_opacity_text.setText(lng.get_label('opacity_text_label', 'Opacity Text:'))
        
        self.grp_performance.setTitle(lng.get_label('performance_frame_title', 'Performance & Cache'))
        self.lbl_file_cache_desc.setText(lng.get_label('file_cache_description', 'File caching saves translations to disk...'))
        self.gemini_cache_check.setText(lng.get_label('gemini_file_cache_checkbox', 'Enable Gemini file cache...'))
        self.deepl_cache_check.setText(lng.get_label('deepl_file_cache_checkbox', 'Enable DeepL file cache...'))
        
        self.clear_caches_btn.setText(lng.get_label('clear_caches_btn', 'Clear File Caches'))
        self.clear_cache_btn.setText(lng.get_label('clear_cache_btn', 'Clear Translation Cache'))
        self.clear_debug_log_btn.setText(lng.get_label('clear_debug_log_btn', 'Clear Debug Log'))

        if hasattr(self, 'grp_lang'):
            self.grp_lang.setTitle(lng.get_label('gui_language_label', 'Interface Language'))
            self.lbl_gui_lang.setText(lng.get_label('gui_language_dropdown_label', 'Language:'))
        
        # Shortcuts Tab
        if hasattr(self, 'grp_shortcuts'):
            sc_title = lng.get_label('keyboard_shortcuts_title', 'Keyboard Shortcuts')
            self.grp_shortcuts.setTitle(f"{sc_title}")
            
            self.lbl_sc_start.setText(f"~ :  {lng.get_label('shortcut_start_stop', 'Start/Stop Translation')}")
            self.lbl_sc_src.setText(f"Alt+1 :  {lng.get_label('shortcut_toggle_source', 'Toggle Source Window Visibility')}")
            self.lbl_sc_tgt.setText(f"Alt+2 :  {lng.get_label('shortcut_toggle_target', 'Toggle Translation Window Visibility')}")
            self.lbl_sc_save.setText(f"Alt+S :  {lng.get_label('shortcut_save_settings', 'Save Settings')}")
            self.lbl_sc_file.setText(f"Alt+F :  {lng.get_label('shortcut_clear_file_caches', 'Clear File Caches')}")
            self.lbl_sc_cache.setText(f"Alt+T :  {lng.get_label('shortcut_clear_cache', 'Clear Translation Cache')}")
            self.lbl_sc_log.setText(f"Alt+D :  {lng.get_label('shortcut_clear_log', 'Clear Debug Log')}")
            self.lbl_sc_reset.setText(f"Alt+R :  {lng.get_label('shortcut_reset_window', 'Reset App Window')}")
            self.lbl_sc_screenshot.setText(f"Alt+L :  {lng.get_label('shortcut_screenshot', 'Take Screenshot')}")

        if hasattr(self, 'status_label'):
            self.update_status_display()

        # Costs Tab
        if hasattr(self, 'refresh_stats_btn'):
            self.refresh_stats_btn.setText(lng.get_label("api_usage_refresh_btn", 'Refresh Statistics'))
            self.export_csv_btn.setText(lng.get_label("api_usage_export_csv_btn", 'Export (CSV)'))
            self.export_text_btn.setText(lng.get_label("api_usage_export_text_btn", 'Export (Text)'))
            self.copy_stats_btn.setText(lng.get_label("api_usage_copy_btn", 'Copy'))
            
            # Retranslate section titles and row labels
            for attr in ["gui_gemini_translation_labels", "gui_gemini_ocr_labels", "gui_gemini_combined_labels"]:
                if hasattr(self, f"{attr}_group"):
                    group = getattr(self, f"{attr}_group")
                    key = getattr(self, f"{attr}_group_key")
                    fallback = getattr(self, f"{attr}_group_fallback")
                    group.setTitle(lng.get_label(key, fallback))
                
                if hasattr(self, f"{attr}_metadata"):
                    metadata = getattr(self, f"{attr}_metadata")
                    for row_label, lang_key, fallback in metadata:
                        row_label.setText(lng.get_label(lang_key, fallback))
            
            if hasattr(self, 'grp_deepl_stats'):
                self.grp_deepl_stats.setTitle(lng.get_label("api_usage_section_deepl", "📈 DeepL Usage Tracker"))
            if hasattr(self, 'lbl_deepl_usage_title'):
                self.lbl_deepl_usage_title.setText(lng.get_label("deepl_usage_label", "DeepL Usage:"))
            
            if hasattr(self, 'lbl_api_usage_note'):
                self.lbl_api_usage_note.setText(lng.get_label("api_usage_info_note", 
                    "Note: Statistics are based on the short log files (e.g., Gemini_OCR_Short_Log.txt). Data will be reset if these files are deleted or cleared."))

            self.refresh_stats()


        # About Tab
        if hasattr(self, 'grp_about'):
            from constants import APP_VERSION, APP_RELEASE_DATE, APP_RELEASE_DATE_POLISH
            rel_date = APP_RELEASE_DATE_POLISH if lng.current_lang == 'pol' else APP_RELEASE_DATE
            
            clean_version = APP_VERSION.lstrip('v')
            self.grp_about.setTitle(f"Game-Changing Translator v{clean_version}")
            
            self.lbl_about_release.setText(f"{lng.get_label('released_label', 'Released')} {rel_date}")
            self.lbl_about_copyright.setText(lng.get_label('copyright_label', 'Copyright © 2025-2026 Tomasz Kamiński'))
            
            self.lbl_about_app_desc.setText(lng.get_label('about_app_description', 'Game-Changing Translator is a desktop application...'))
            self.lbl_about_models_desc.setText(lng.get_label('about_description', 'This application was developed...'))
            self.lbl_about_manual.setText(lng.get_label('about_info_manual', 'For more information, see the user manual.'))
            
            self.lbl_about_tool_header.setText(lng.get_label('about_other_tool_header', 'Check my other tool:'))
            
            ohlc_link = f"<a href='https://github.com/tomkam1702/OHLC-Forge' style='color: #2196F3; text-decoration: underline;'>OHLC Forge</a>"
            ohlc_desc = lng.get_label('about_other_tool_desc', 'OHLC Forge – specialist tool...')
            if ohlc_desc.startswith("OHLC Forge"):
                if " – " in ohlc_desc: ohlc_desc = ohlc_desc.split(" – ", 1)[1]
                elif " - " in ohlc_desc: ohlc_desc = ohlc_desc.split(" - ", 1)[1]
            
            self.lbl_about_tool_desc.setText(f"{ohlc_link} - {ohlc_desc}")
            
            self.check_updates_btn.setText(lng.get_label('check_for_updates_btn', 'Check for Updates'))
            self.grp_pro.setTitle(f"Open-Source Edition")

        # Status Label
        if not self.translator.is_running:
            self.status_label.setText(lng.get_label('status_ready', 'Status: Ready'))
        else:
            self.status_label.setText(lng.get_label('status_running', 'Running (Press ~ to Stop)'))

        self.refresh_language_lists()
        self.synchronize_combo_widths()
        self.update_visibility_btns()
        if not already_loading:
            self._is_loading = False

    def toggle_key_visibility(self, entry, btn):
        if not self.translator: return
        lng = self.translator.ui_lang
        if entry.echoMode() == QLineEdit.Password:
            entry.setEchoMode(QLineEdit.Normal)
            btn.setText(lng.get_label('hide_btn', 'Hide'))
        else:
            entry.setEchoMode(QLineEdit.Password)
            btn.setText(lng.get_label('show_btn', 'Show'))

    def update_auto_detect_label(self, checked=None):
        if not self.translator: return
        lbl = self.translator.ui_lang.get_label('auto_detect_label', 'Find Subtitles')
        self.lbl_auto_detect_text.setText(f'{lbl} <sup style="color: gray;">PRO</sup>')
        is_on = self.auto_detect_check.isChecked()
            
        if hasattr(self, 'discovery_timeout_spin'):
            self.lbl_discovery_time.setVisible(is_on)
            self.discovery_timeout_container.setVisible(is_on)
        
    def update_capture_padding_label(self, checked=None):
        if not self.translator: return
        lbl = self.translator.ui_lang.get_label('capture_padding_label', 'Scan Wider')
        self.lbl_capture_padding_text.setText(f'{lbl} <sup style="color: gray;">PRO</sup>')
        is_on = self.capture_padding_check.isChecked()
        if hasattr(self, 'capture_padding_container'):
            self.capture_padding_container.setVisible(is_on)
        if is_on:
            suffix = self.translator.ui_lang.get_label('capture_padding_suffix', '%')
            self.capture_padding_value_label.setText(suffix)

    def update_target_on_source_label(self, checked=None):
        if not self.translator: return
        lbl = self.translator.ui_lang.get_label('target_on_source_label', 'Target Area on Source Area')
        self.lbl_target_on_source_text.setText(f'{lbl} <sup style="color: gray;">PRO</sup>')

    def update_info_tooltips(self):
        if not self.translator: return
        lng = self.translator.ui_lang
        # All HelpButton tooltips are updated via the loop below
        
        for btn in self.findChildren(HelpButton):
            btn.update_tooltip()

        
    def update_debug_log_label(self, checked=None):
        if not self.translator: return
        lbl_enable = self.translator.ui_lang.get_label('toggle_debug_log_enable_btn', 'Enable Debug Log')
        self.debug_log_check.setText(lbl_enable)

    def bind_auto_save(self):
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.setSingleShot(True)
        self._auto_save_timer.timeout.connect(self.save_all_settings)
        
        combos = [
            self.translation_model_combo, self.ocr_model_combo, self.gemini_context_combo,
            self.deepl_context_combo, self.source_lang_combo,
            self.target_lang_combo, self.font_type_combo
        ]
        for c in combos: c.currentIndexChanged.connect(self._on_setting_changed)
            
        checks = [
            self.auto_detect_check, self.target_on_source_check, self.keep_linebreaks_check,
            self.deepl_cache_check, self.gemini_cache_check, self.debug_log_check,
            self.custom_prompt_trans_enabled_check, self.custom_prompt_ocr_enabled_check,
            self.capture_padding_check
        ]
        for c in checks: c.toggled.connect(self._on_setting_changed)
            
        spins = [
            self.scan_interval_spin, self.clear_timeout_spin, self.discovery_timeout_spin,
            self.font_size_spin, self.target_opacity_spin, self.target_text_opacity_spin,
            self.capture_padding_spin
        ]
        for s in spins: s.valueChanged.connect(self._on_setting_changed)
            
        entries = [self.gemini_api_key_entry, self.deepl_api_key_entry]
        for e in entries: e.editingFinished.connect(self._on_setting_changed)
        
        # Immediate backend sync for language combos (no 500ms delay)
        self.source_lang_combo.currentIndexChanged.connect(self._on_language_combo_changed)
        self.target_lang_combo.currentIndexChanged.connect(self._on_language_combo_changed)

    def _on_setting_changed(self, *args):
        if getattr(self, '_is_loading', False): return
        self._auto_save_timer.start(500) # 500ms debounce before automatic save

    def _on_capture_padding_changed(self, value):
        """Update the displayed percentage label when capture padding spin changes."""
        if self.translator:
            suffix = self.translator.ui_lang.get_label('capture_padding_suffix', '%')
            self.capture_padding_value_label.setText(suffix)

    def _on_language_combo_changed(self):
        """Immediately sync language combo selections to backend and save to .ini."""
        if getattr(self, '_is_loading', False) or not self.translator:
            return
        
        t = self.translator
        is_deepl = (t.translation_model == 'deepl_api')
        
        source_code = self.source_lang_combo.currentData()
        target_code = self.target_lang_combo.currentData()
        
        log_debug(f"_on_language_combo_changed: source_code={source_code!r}, target_code={target_code!r}, "
                  f"source_text={self.source_lang_combo.currentText()!r}, target_text={self.target_lang_combo.currentText()!r}, "
                  f"source_count={self.source_lang_combo.count()}, target_count={self.target_lang_combo.count()}, "
                  f"is_deepl={is_deepl}")
        
        if source_code:
            t.source_lang = source_code
            if is_deepl:
                t.deepl_source_lang = source_code
            else:
                t.gemini_source_lang = source_code
        
        if target_code:
            t.target_lang = target_code
            if is_deepl:
                t.deepl_target_lang = target_code
            else:
                t.gemini_target_lang = target_code
        
        log_debug(f"_on_language_combo_changed: AFTER UPDATE -> gemini_source={t.gemini_source_lang!r}, gemini_target={t.gemini_target_lang!r}")
        
        # Cancel pending debounce timer and save everything immediately
        self._auto_save_timer.stop()
        self.save_all_settings()

    def set_translator(self, translator):
        self.translator = translator
        self.translator.gui = self
        log_debug("Stage III: Backend connected to MainWindowV4")
        
        self.font_type_combo.addItems(self.get_system_fonts())
        if self.translator.GEMINI_API_AVAILABLE:
            self.ocr_model_combo.clear()
            self.ocr_model_combo.addItems(self.translator.gemini_models_manager.get_ocr_model_names())
        
        self.translation_model_combo.clear()
        if self.translator:
            model_names = self.translator.gemini_models_manager.get_translation_model_names()
            if "DeepL" not in model_names:
                model_names.append("DeepL")
            self.translation_model_combo.addItems(model_names)
        else:
            self.translation_model_combo.addItems(["Gemini 2.5 Flash-Lite", "DeepL"])
        
        self.refresh_language_lists()
        
        # Populate GUI language combo
        self.gui_lang_combo.clear()
        self.gui_lang_combo.addItems(self.translator.ui_lang.get_language_list())
        
        self.retranslate_ui()
        self.load_settings_to_ui()
        self._is_loading = False # End of initialisation

    def refresh_language_lists(self):
        if not self.translator: return
        already_loading = getattr(self, '_is_loading', False)
        self._is_loading = True
        lm = self.translator.language_manager
        ui_lang_for_lookup = 'polish' if self.translator.ui_lang.current_lang == 'pol' else 'english'
        current_text = self.translation_model_combo.currentText()
        active_model = 'deepl' if current_text == 'DeepL' else 'gemini'
        
        # Helper for sorting language pairs
        def sort_pairs(pairs, ui_lang):
            auto_pair = [p for p in pairs if p[1] == 'auto']
            others = [p for p in pairs if p[1] != 'auto']
            if ui_lang == 'polish':
                others.sort(key=lambda x: lm._polish_sort_key(x[0]))
            else:
                others.sort(key=lambda x: x[0])
            return auto_pair + others

        # Source Languages
        source_pairs = []
        detect_lbl = self.translator.ui_lang.get_label('detect_language', '< Detect language >')
        if active_model == 'deepl':
            source_pairs = [(detect_lbl if code == 'auto' else lm.get_localized_language_name(code, 'deepl', ui_lang_for_lookup), code) 
                          for _, code in lm.deepl_source_languages]
        elif active_model == 'gemini':
            source_pairs = [(detect_lbl if code == 'auto' else lm.get_localized_language_name(code, 'gemini', ui_lang_for_lookup), code) 
                          for _, code in lm.gemini_source_languages]
        
        source_pairs = sort_pairs(source_pairs, ui_lang_for_lookup)
        self.source_lang_combo.clear()
        for name, code in source_pairs:
            self.source_lang_combo.addItem(name, code)
            
        # Target Languages
        target_pairs = []
        if active_model == 'deepl':
            target_pairs = [(lm.get_localized_language_name(code, 'deepl', ui_lang_for_lookup), code) 
                          for _, code in lm.deepl_target_languages]
        elif active_model == 'gemini':
            target_pairs = [(lm.get_localized_language_name(code, 'gemini', ui_lang_for_lookup), code) 
                          for _, code in lm.gemini_target_languages]
                          
        target_pairs = sort_pairs(target_pairs, ui_lang_for_lookup)
        self.target_lang_combo.clear()
        for name, code in target_pairs:
            self.target_lang_combo.addItem(name, code)
            
        self.synchronize_language_combo_widths()
            
        if not already_loading:
            self._is_loading = False

    def on_translation_model_changed(self):
        if not self.translator: return
        already_loading = getattr(self, '_is_loading', False)
        self._is_loading = True
        current_text = self.translation_model_combo.currentText()
        is_gemini = (current_text != 'DeepL')
            
        self.refresh_language_lists()
        
        ui_lang_lookup = 'polish' if self.translator.ui_lang.current_lang == 'pol' else 'english'
        provider = 'gemini' if is_gemini else 'deepl'
        
        saved_source_code = self.translator.gemini_source_lang if is_gemini else self.translator.deepl_source_lang
        saved_target_code = self.translator.gemini_target_lang if is_gemini else self.translator.deepl_target_lang
        
        idx_src = self.source_lang_combo.findData(saved_source_code)
        if idx_src >= 0: self.source_lang_combo.setCurrentIndex(idx_src)
        
        idx_tgt = self.target_lang_combo.findData(saved_target_code)
        if idx_tgt >= 0: self.target_lang_combo.setCurrentIndex(idx_tgt)
        
        if hasattr(self, 'models_form_layout'):
            self.models_form_layout.setRowVisible(2, is_gemini)  # Gemini Context
            self.models_form_layout.setRowVisible(3, not is_gemini) # DeepL Context

        self.synchronize_language_combo_widths()

        if not already_loading:
            self._is_loading = False
        self._on_setting_changed()

    def on_gui_language_changed(self):
        if not self.translator or getattr(self, '_is_loading', False): return
        new_lang_name = self.gui_lang_combo.currentText()
        if not new_lang_name: return
        
        lang_code = self.translator.ui_lang.get_language_code_from_name(new_lang_name)
        if lang_code:
            self._is_loading = True
            try:
                # Important: Update the backend setting BEFORE retranslation/reloading
                self.translator.gui_language = new_lang_name
                self.translator.ui_lang.load_language(lang_code)
                
                self.retranslate_ui()
                self.load_settings_to_ui()  # Restore all selections from backend
                self.translator.save_settings()
                self.show_status(f"Language changed to {new_lang_name}", 3000)
            finally:
                self._is_loading = False

    def on_config_mode_changed(self, index=0):
        """Handle Simple / Advanced mode toggle."""
        if not self.translator or getattr(self, '_is_loading', False):
            return
        
        new_mode = 'Simple' if index == 0 else 'Advanced'
        old_mode = self.translator.config_mode
        
        if new_mode == old_mode:
            return
        
        self.translator.config_mode = new_mode
        log_debug(f"Config mode changed: {old_mode} -> {new_mode}")
        
        # Automatic transition: Show -> Hide when user manually switches Advanced -> Simple
        if new_mode == 'Simple' and old_mode == 'Advanced' and self.translator.ui_visibility_mode == 'Show':
            self.on_settings_btn_clicked()  # Trigger visibility toggle to Hide
        self._is_loading = True
        try:
            if new_mode == 'Simple':
                self.translator.apply_simple_overrides()
            else:
                self.translator.reload_from_ini()
            
            # Clear any pending color choices from the previous mode
            self._pending_colors.clear()
            
            self.load_settings_to_ui()
            self.update_simple_mode_sensitivity()
            
            # Sync live overlays to new mode's colors/opacity
            t = self.translator
            if t.source_overlay:
                t.source_overlay.update_color(t.source_colour, 0.7)
            if t.target_overlay:
                t.target_overlay.update_color(t.target_colour, t.target_opacity)
                t.target_overlay.update_text_color(t.target_text_colour)
            
            # Save only the mode change (save_settings will skip locked keys)
            self.translator.save_settings()
            
            mode_label = self.translator.ui_lang.get_label(
                'config_mode_simple' if new_mode == 'Simple' else 'config_mode_advanced',
                new_mode
            )
            mode_prefix = self.translator.ui_lang.get_label('status_mode_prefix', 'Mode')
            self.show_status(f"{mode_prefix}: {mode_label}", 2000)
        finally:
            self._is_loading = False

    def on_top_visibility_btn_clicked(self):
        """Toggle Show / Hide mode for the top configuration area."""
        if not self.translator or getattr(self, '_is_loading', False):
            return
            
        old_mode = getattr(self.translator, 'top_visibility_mode', 'Show')
        new_mode = 'Hide' if old_mode == 'Show' else 'Show'
        
        self.translator.top_visibility_mode = new_mode
        log_debug(f"Top Visibility toggled: {old_mode} -> {new_mode}")
        
        self.apply_top_visibility_settings(new_mode)
        self.translator.save_settings()

    def apply_top_visibility_settings(self, mode):
        """Apply Show/Hide logic to the top config widget."""
        import os
        import nuitka_compat
        base_dir = nuitka_compat.get_base_dir()
        
        if mode == 'Hide':
            self.top_config_widget.hide()
            icon_path = os.path.join(base_dir, "assets", "expand.svg")
            tt = self.translator.ui_lang.get_label('expand_top_area', 'Show languages and API keys') if self.translator else "Show languages and API keys"
            self.top_visibility_btn.setToolTip(tt)
            
            # Dynamic height for custom prompts
            if hasattr(self, 'custom_prompt_trans_edit'):
                self.custom_prompt_trans_edit.setMinimumHeight(self.dp(80))
                self.custom_prompt_trans_edit.setMaximumHeight(16777215)
                self.custom_prompt_trans_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
                self.custom_prompt_ocr_edit.setMinimumHeight(self.dp(80))
                self.custom_prompt_ocr_edit.setMaximumHeight(16777215)
                self.custom_prompt_ocr_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        else:
            self.top_config_widget.show()
            icon_path = os.path.join(base_dir, "assets", "collapse.svg")
            tt = self.translator.ui_lang.get_label('collapse_top_area', 'Hide languages and API keys') if self.translator else "Hide languages and API keys"
            self.top_visibility_btn.setToolTip(tt)
            
            # Rigid height for custom prompts
            if hasattr(self, 'custom_prompt_trans_edit'):
                self.custom_prompt_trans_edit.setMinimumHeight(self.dp(145))
                self.custom_prompt_trans_edit.setMaximumHeight(self.dp(145))
                self.custom_prompt_trans_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.custom_prompt_ocr_edit.setMinimumHeight(self.dp(145))
                self.custom_prompt_ocr_edit.setMaximumHeight(self.dp(145))
                self.custom_prompt_ocr_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            
        if os.path.exists(icon_path):
            self.top_visibility_btn.setIcon(QIcon(icon_path))
            
        if self.translator and getattr(self.translator, 'ui_visibility_mode', 'Show') == 'Hide':
            current_width = self.width()
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            self._is_toggling_visibility = True
            QTimer.singleShot(50, lambda: self._do_adjust_size(current_width))

    def on_settings_btn_clicked(self):
        """Toggle Show / Hide mode when Settings button is clicked."""
        if not self.translator or getattr(self, '_is_loading', False):
            return
            
        # Toggle current mode
        old_mode = self.translator.ui_visibility_mode
        new_mode = 'Hide' if old_mode == 'Show' else 'Show'
        
        self.translator.ui_visibility_mode = new_mode
        log_debug(f"UI Visibility toggled via Settings button: {old_mode} -> {new_mode}")
        
        # Update button appearance
        self.settings_visibility_btn.set_active(new_mode == 'Show')
        self.apply_visibility_settings(new_mode)
        
        # Save change
        self.translator.save_settings()
        
    def update_visibility_btns(self):
        """Sync button appearance with current window/overlay visibility."""
        if not self.translator: return
        
        # 1. Update Settings Toggle
        if hasattr(self, 'settings_visibility_btn') and self.translator:
            self.settings_visibility_btn.set_active(self.translator.ui_visibility_mode == 'Show')
            
        # 2. Update Source/Target Action buttons
        if hasattr(self, 'action_source') and hasattr(self, 'toolbar'):
            btn_src = self.toolbar.widgetForAction(self.action_source)
            if btn_src:
                # Overlays are hosted in the translator object
                is_active = False
                if hasattr(self.translator, 'source_overlay') and self.translator.source_overlay:
                    is_active = self.translator.source_overlay.isVisible()
                btn_src.setProperty("active", is_active)
                btn_src.style().unpolish(btn_src)
                btn_src.style().polish(btn_src)
                
        if hasattr(self, 'action_target') and hasattr(self, 'toolbar'):
            btn_tgt = self.toolbar.widgetForAction(self.action_target)
            if btn_tgt:
                is_active = False
                if hasattr(self.translator, 'target_overlay') and self.translator.target_overlay:
                    is_active = self.translator.target_overlay.isVisible()
                btn_tgt.setProperty("active", is_active)
                btn_tgt.style().unpolish(btn_tgt)
                btn_tgt.style().polish(btn_tgt)

    def apply_visibility_settings(self, mode):
        """Apply Show/Hide logic to the tab widget and window height."""
        self._is_toggling_visibility = True
        current_width = self.width()
        if mode == 'Hide':
            self.tab_widget.hide()
            self.bottom_stretch.changeSize(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
            self.main_layout.invalidate()
            # Temporarily remove restrictions to allow adjustSize to find the ideal compact height
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            QTimer.singleShot(50, lambda: self._do_adjust_size(current_width))
        else:
            self.tab_widget.show()
            self.setMinimumHeight(self.dp(500))
            self.setMaximumHeight(16777215) # Remove restriction for Show mode
            self.bottom_stretch.changeSize(0, 0, QSizePolicy.Minimum, QSizePolicy.Minimum)
            
            # Use current memory value if available, else fallback to config
            cfg = self.translator.config['Settings']
            try:
                h_norm = int(cfg.get('window_height_show', '-1'))
                if h_norm > 0:
                    h = round(h_norm * self.scale_factor)
                    if h > 500: # Threshold for full UI
                        self.resize(current_width, h)
            except:
                pass
        
        self._is_toggling_visibility = False

    def resizeEvent(self, event):
        """Monitor manual resizes to update Show-mode height memory."""
        super().resizeEvent(event)
        if not self.translator or getattr(self, '_is_loading', False) or getattr(self, '_is_toggling_visibility', False):
            return
            
        # Do not save dimensions if the window is maximized or minimized
        # to preserve the "Normal" size for restoration.
        if self.isMaximized() or self.isMinimized():
            return
            
        # If we are in Show mode, update the height memory immediately
        if self.translator.ui_visibility_mode == 'Show':
            # Normalize and store in config object for persistence using round
            h_norm = round(self.height() / self.scale_factor)
            w_norm = round(self.width() / self.scale_factor)
            self.translator.config['Settings']['window_height_show'] = str(h_norm)
            self.translator.config['Settings']['window_width'] = str(w_norm)

    def _do_adjust_size(self, forced_width):
        """Helper to adjust height while preserving width, and locking it if in Hide mode."""
        self.adjustSize()
        real_h = self.height()
        
        # If we are in Hide mode, lock the window to this exact "real" height
        # to prevent vertical resizing and unwanted Windows expansion on restore.
        if self.translator and self.translator.ui_visibility_mode == 'Hide':
            self.setMinimumHeight(real_h)
            self.setMaximumHeight(real_h)
            
        self.resize(forced_width, real_h)
        self._is_toggling_visibility = False
                
    def update_simple_mode_sensitivity(self):
        """Enable or disable GUI widgets based on config mode."""
        if not self.translator:
            return
        
        is_simple = (self.translator.config_mode == 'Simple')
        enabled = not is_simple
        style = "color: gray;" if is_simple else ""
        
        # Combos and their labels
        if hasattr(self, 'lbl_translation_model'): 
            self.lbl_translation_model.setEnabled(enabled)
            self.lbl_translation_model.setStyleSheet(style)
        if hasattr(self, 'lbl_ocr_model'): 
            self.lbl_ocr_model.setEnabled(enabled)
            self.lbl_ocr_model.setStyleSheet(style)
        if hasattr(self, 'lbl_gemini_context'): 
            self.lbl_gemini_context.setEnabled(enabled)
            self.lbl_gemini_context.setStyleSheet(style)
        if hasattr(self, 'lbl_deepl_context'): 
            self.lbl_deepl_context.setEnabled(enabled)
            self.lbl_deepl_context.setStyleSheet(style)
            
        self.translation_model_combo.setEnabled(enabled)
        self.ocr_model_combo.setEnabled(enabled)
        self.gemini_context_combo.setEnabled(enabled)
        self.font_type_combo.setEnabled(enabled)
        self.source_lang_combo.setEnabled(enabled)
        
        if hasattr(self, 'lbl_source_lang'):
            self.lbl_source_lang.setEnabled(enabled)
            self.lbl_source_lang.setStyleSheet(style)
        
        # Spin boxes and Combos standalone labels
        if hasattr(self, 'lbl_scan_interval'): 
            self.lbl_scan_interval.setEnabled(enabled)
            self.lbl_scan_interval.setStyleSheet(style)
        if hasattr(self, 'lbl_clear_timeout'): 
            self.lbl_clear_timeout.setEnabled(enabled)
            self.lbl_clear_timeout.setStyleSheet(style)
        if hasattr(self, 'lbl_font_size'): 
            self.lbl_font_size.setEnabled(enabled)
            self.lbl_font_size.setStyleSheet(style)
        if hasattr(self, 'lbl_font_type'): 
            self.lbl_font_type.setEnabled(enabled)
            self.lbl_font_type.setStyleSheet(style)
        if hasattr(self, 'lbl_opacity_bg'): 
            self.lbl_opacity_bg.setEnabled(enabled)
            self.lbl_opacity_bg.setStyleSheet(style)
        if hasattr(self, 'lbl_opacity_text'): 
            self.lbl_opacity_text.setEnabled(enabled)
            self.lbl_opacity_text.setStyleSheet(style)
        
        # Spin boxes
        self.scan_interval_spin.setEnabled(enabled)
        self.clear_timeout_spin.setEnabled(enabled)
        self.font_size_spin.setEnabled(enabled)
        self.target_opacity_spin.setEnabled(enabled)
        self.target_text_opacity_spin.setEnabled(enabled)
        
        # Checkboxes
        
        self.auto_detect_check.setEnabled(enabled)
        if hasattr(self, 'lbl_auto_detect_text'):
            self.lbl_auto_detect_text.setEnabled(enabled)
            self.lbl_auto_detect_text.setStyleSheet(style)
        self.capture_padding_check.setEnabled(enabled)
        if hasattr(self, 'lbl_capture_padding_text'):
            self.lbl_capture_padding_text.setEnabled(enabled)
            self.lbl_capture_padding_text.setStyleSheet(style)
        self.capture_padding_spin.setEnabled(enabled)
        self.target_on_source_check.setEnabled(enabled)
        if hasattr(self, 'lbl_target_on_source_text'):
            self.lbl_target_on_source_text.setEnabled(enabled)
            self.lbl_target_on_source_text.setStyleSheet(style)
            
        self.lbl_source_color.setStyleSheet(style)
        self.lbl_target_color.setStyleSheet(style)
        self.lbl_target_text_color.setStyleSheet(style)
        
        # Trigger text updates to change the PRO color
        self.update_auto_detect_label()
        self.update_capture_padding_label()
        self.update_target_on_source_label()
        
        self.keep_linebreaks_check.setEnabled(enabled)
        self.deepl_cache_check.setEnabled(enabled)
        self.gemini_cache_check.setEnabled(enabled)
        self.debug_log_check.setEnabled(enabled)
        self.custom_prompt_trans_edit.setEnabled(enabled)
        self.custom_prompt_trans_enabled_check.setEnabled(enabled)
        self.save_cp_btn.setEnabled(enabled)
        self.reload_cp_btn.setEnabled(enabled)
        
        self.custom_prompt_ocr_edit.setEnabled(enabled)
        self.custom_prompt_ocr_enabled_check.setEnabled(enabled)
        self.save_ocr_cp_btn.setEnabled(enabled)
        self.reload_ocr_cp_btn.setEnabled(enabled)
        
        # Colour buttons
        self.source_color_btn.setEnabled(enabled)
        self.target_color_btn.setEnabled(enabled)
        self.target_text_color_btn.setEnabled(enabled)

        self.apply_pro_state()

    def load_settings_to_ui(self):

        if not self.translator: return
        already_loading = getattr(self, '_is_loading', False)
        self._is_loading = True
        t = self.translator
        
        self.gemini_api_key_entry.setText(t.gemini_api_key)
        self.deepl_api_key_entry.setText(t.deepl_api_key)
        
        ui_lang_lookup = 'polish' if t.ui_lang.current_lang == 'pol' else 'english'
        provider = 'deepl' if t.translation_model == 'deepl_api' else 'gemini'
        
        source_lang_code = t.deepl_source_lang if provider == 'deepl' else t.gemini_source_lang
        target_lang_code = t.deepl_target_lang if provider == 'deepl' else t.gemini_target_lang
        
        idx_src = self.source_lang_combo.findData(source_lang_code)
        if idx_src >= 0: self.source_lang_combo.setCurrentIndex(idx_src)
        
        idx_tgt = self.target_lang_combo.findData(target_lang_code)
        if idx_tgt >= 0: self.target_lang_combo.setCurrentIndex(idx_tgt)
        
        if t.translation_model == 'deepl_api':
            self.translation_model_combo.setCurrentText('DeepL')
        elif t.translation_model == 'gemini_api':
            self.translation_model_combo.setCurrentText(t.gemini_translation_model)
        self.ocr_model_combo.setCurrentText(t.gemini_ocr_model)
        
        
        idx_deepl = self.deepl_context_combo.findData(t.deepl_context_window)
        if idx_deepl >= 0: self.deepl_context_combo.setCurrentIndex(idx_deepl)
        
        idx_gemini = self.gemini_context_combo.findData(t.gemini_context_window)
        if idx_gemini >= 0: self.gemini_context_combo.setCurrentIndex(idx_gemini)
        
        self.auto_detect_check.setChecked(t.auto_detect_enabled)
        self.target_on_source_check.setChecked(t.target_on_source_enabled)
        self.capture_padding_check.setChecked(t.capture_padding_enabled)
        self.capture_padding_spin.setValue(t.capture_padding)
        
        self.source_color_preview.setStyleSheet(f"background-color: {t.source_colour}; border: {self.dp(1)}px solid #8b949e;")
        self.target_color_preview.setStyleSheet(f"background-color: {t.target_colour}; border: {self.dp(1)}px solid #8b949e;")
        self.target_text_color_preview.setStyleSheet(f"background-color: {t.target_text_colour}; border: {self.dp(1)}px solid #8b949e;")
        self.target_opacity_spin.setValue(t.target_opacity)
        self.target_text_opacity_spin.setValue(t.target_text_opacity)
        self.font_type_combo.setCurrentText(t.target_font_type)
        self.font_size_spin.setValue(t.target_font_size)
        self.keep_linebreaks_check.setChecked(t.keep_linebreaks)
        
        self.scan_interval_spin.setValue(t.scan_interval)
        self.clear_timeout_spin.setValue(t.clear_translation_timeout)
        self.discovery_timeout_spin.setValue(t.discovery_timeout)
        self.deepl_cache_check.setChecked(t.deepl_cache_enabled)
        self.gemini_cache_check.setChecked(t.gemini_cache_enabled)
        self.debug_log_check.setChecked(t.debug_logging_enabled)
        
        idx_lang = self.gui_lang_combo.findText(t.gui_language)
        if idx_lang >= 0: self.gui_lang_combo.setCurrentIndex(idx_lang)

        self.custom_prompt_trans_enabled_check.setChecked(t.custom_prompt_enabled)
        self.custom_prompt_ocr_enabled_check.setChecked(t.custom_ocr_prompt_enabled)

        self.on_translation_model_changed()
        self.reload_custom_prompts()
        
        # Mode integration
        mode_idx = 0 if t.config_mode == 'Simple' else 1
        self.config_mode_btn.setCurrentIndex(mode_idx)
        self.update_simple_mode_sensitivity()
        

        # Visibility integration
        v_mode = t.ui_visibility_mode
        self.settings_visibility_btn.set_active(v_mode == 'Show')
        self.apply_visibility_settings(v_mode)
        
        # Top Visibility Integration
        top_v_mode = getattr(t, 'top_visibility_mode', 'Show')
        self.apply_top_visibility_settings(top_v_mode)
        
        if not already_loading:
            self._is_loading = False

    def update_licence_display(self):
        """Update the licence status label in the bottom bar with FREE formatting."""
        if not self.translator or not hasattr(self, 'licence_status_label'):
            return
        lng = self.translator.ui_lang
        prefix = lng.get_label('status_licence', 'Licence:')
        # Hardcoded FREE for open-source with original formatting
        text = f'{prefix} <b style="color: #27AE60;">FREE</b>'
        self.licence_status_label.setText(text)

    def apply_pro_state(self):
        """Always disable PRO-gated widgets in open-source edition."""
        pro_style = "color: gray;"
        try:
            # Disable PRO-specific widgets
            self.auto_detect_check.setEnabled(False)
            if hasattr(self, 'lbl_auto_detect_text'):
                self.lbl_auto_detect_text.setEnabled(False)
                self.lbl_auto_detect_text.setStyleSheet(pro_style)

            self.capture_padding_check.setEnabled(False)
            if hasattr(self, 'lbl_capture_padding_text'):
                self.lbl_capture_padding_text.setEnabled(False)
                self.lbl_capture_padding_text.setStyleSheet(pro_style)

            self.target_on_source_check.setEnabled(False)
            if hasattr(self, 'lbl_target_on_source_text'):
                self.lbl_target_on_source_text.setEnabled(False)
                self.lbl_target_on_source_text.setStyleSheet(pro_style)

            # Colour pickers
            self.source_color_btn.setEnabled(False)
            self.target_color_btn.setEnabled(False)
            self.target_text_color_btn.setEnabled(False)
            self.lbl_source_color.setStyleSheet(pro_style)
            self.lbl_target_color.setStyleSheet(pro_style)
            self.lbl_target_text_color.setStyleSheet(pro_style)

            # OCR Prompt
            self.custom_prompt_ocr_edit.setEnabled(False)
            self.custom_prompt_ocr_enabled_check.setEnabled(False)
            self.save_ocr_cp_btn.setEnabled(False)
            self.reload_ocr_cp_btn.setEnabled(False)

            # DeepL API Key row (PRO feature)
            self.deepl_api_key_entry.setEnabled(False)
            self.deepl_api_key_entry.setStyleSheet(pro_style)
            self.show_deepl_key_btn.setEnabled(False)
            if hasattr(self, 'lbl_deepl_key'):
                self.lbl_deepl_key.setEnabled(False)
                self.lbl_deepl_key.setStyleSheet(pro_style)

            # DeepL in combobox — REMOVE IT ENTIRELY for open-source
            deepl_index = self.translation_model_combo.findText("DeepL")
            if deepl_index != -1:
                if self.translation_model_combo.currentIndex() == deepl_index:
                    self.translation_model_combo.setCurrentIndex(0)
                self.translation_model_combo.removeItem(deepl_index)
        except Exception:
            pass

    def update_about_text(self):
        """Replaces the PRO activation section with a GitHub release link."""
        if not self.translator: return
        lng = self.translator.ui_lang
        
        # Show the PRO promotion message with links (analogous to OHLC Forge)
        m1 = lng.get_label('about_pro_msg_1', "To use PRO features, download the")
        m2 = lng.get_label('about_pro_msg_2', "compiled version")
        m3 = lng.get_label('about_pro_msg_3', "and buy a PRO license on")
        m4 = lng.get_label('about_pro_msg_4', "Gumroad")
        
        link_compiled = f"<a href='https://github.com/tomkam1702/OCR-Translator/releases' style='color: #2196F3; text-decoration: underline;'>{m2}</a>"
        link_gumroad = f"<a href='https://tomkam17.gumroad.com/l/gct' style='color: #2196F3; text-decoration: underline;'>{m4}</a>"
        
        about_html = f"<p style='line-height: 1.4;'>{m1} {link_compiled} {m3} {link_gumroad}.</p>"
        
        if hasattr(self, 'about_label'):
            self.about_label.setText(about_html)

    def save_all_settings(self, manual=False):

        if not self.translator: return
        t = self.translator
        t.config_mode = 'Simple' if self.config_mode_btn.currentIndex() == 0 else 'Advanced'
        
        t.gemini_api_key = self.gemini_api_key_entry.text()
        t.deepl_api_key = self.deepl_api_key_entry.text()
        
        current_text = self.translation_model_combo.currentText()
        if current_text == 'DeepL':
            t.translation_model = 'deepl_api'
        else:
            t.translation_model = 'gemini_api'
            t.gemini_translation_model = current_text
        
        ui_lang_lookup = 'polish' if t.ui_lang.current_lang == 'pol' else 'english'
        provider = 'deepl' if t.translation_model == 'deepl_api' else 'gemini'
        
        source_code = self.source_lang_combo.currentData()
        if source_code: 
            t.source_lang = source_code
            if t.translation_model == 'deepl_api':
                t.deepl_source_lang = source_code
            else:
                t.gemini_source_lang = source_code
                
        target_code = self.target_lang_combo.currentData()
        if target_code: 
            t.target_lang = target_code
            if t.translation_model == 'deepl_api':
                t.deepl_target_lang = target_code
            else:
                t.gemini_target_lang = target_code

        t.gemini_ocr_model = self.ocr_model_combo.currentText()
        t.deepl_context_window = self.deepl_context_combo.currentData()
        t.gemini_context_window = self.gemini_context_combo.currentData()
        
        # Apply properties to backend translator
        t.source_colour = self._pending_colors.get("source_colour", t.source_colour)
        t.target_colour = self._pending_colors.get("target_colour", t.target_colour)
        t.target_text_colour = self._pending_colors.get("target_text_colour", t.target_text_colour)
        t.scan_interval = self.scan_interval_spin.value()
        t.clear_translation_timeout = self.clear_timeout_spin.value()
        t.discovery_timeout = self.discovery_timeout_spin.value()
        t.target_opacity = self.target_opacity_spin.value()
        t.target_text_opacity = self.target_text_opacity_spin.value()
        t.target_font_size = self.font_size_spin.value()
        t.target_font_type = self.font_type_combo.currentText()
        t.keep_linebreaks = self.keep_linebreaks_check.isChecked()
        t.auto_detect_enabled = self.auto_detect_check.isChecked()
        t.target_on_source_enabled = self.target_on_source_check.isChecked()
        t.capture_padding_enabled = self.capture_padding_check.isChecked()
        t.capture_padding = self.capture_padding_spin.value()
        
        # Target on Source alignment removed in open-source edition
                
        t.debug_logging_enabled = self.debug_log_check.isChecked()
        t.gui_language = self.gui_lang_combo.currentText()
        t.custom_prompt_enabled = self.custom_prompt_trans_enabled_check.isChecked()
        t.custom_ocr_prompt_enabled = self.custom_prompt_ocr_enabled_check.isChecked()

        # IMMEDIATE UPDATE: Sync properties to live overlays if they exist
        if t.source_overlay:
            t.source_overlay.update_color(t.source_colour, 0.7)
        if t.target_overlay:
            t.target_overlay.update_color(t.target_colour, t.target_opacity)
            t.target_overlay.update_text_color(t.target_text_colour)
        
        t.save_settings()
        
        if hasattr(t, 'ui_interaction_handler'):
            t.ui_interaction_handler.update_target_opacity()
            t.ui_interaction_handler.update_target_text_opacity()
            
        # Clear pending colors after successful save
        self._pending_colors.clear()
            
        if manual:
            self.show_status(t.ui_lang.get_label('status_settings_saved', "Settings saved."), 2000)
        else:
            self.show_status(t.ui_lang.get_label('status_settings_saved_auto', "Settings saved automatically."), 2000)

    def show_status(self, text, timeout=3000):
        """Display a message in the manual status label and reset it after a timeout."""
        if not hasattr(self, 'status_label'): return
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"font-size: {self.scaled_font_size}pt; color: #1565C0; font-weight: bold;") # Highlight message
        
        # Helper to reset to normal status display
        QTimer.singleShot(timeout, self.update_status_display)

    def update_status_display(self):
        """Update the status label and Start button based on the current application state."""
        if not self.translator: return
        lng = self.translator.ui_lang
        
        # 1. Update discrete status label
        if hasattr(self, 'status_label'):
            self.status_label.setStyleSheet(f"font-size: {self.scaled_font_size}pt; color: #555; font-weight: normal;")
            if self.translator.is_running:
                self.status_label.setText(lng.get_label('status_running', 'Running (Press ~ to Stop)'))
            else:
                self.status_label.setText(lng.get_label('status_ready', 'Status: Ready'))
                
        # 2. Update Start/Stop button appearance
        if hasattr(self, 'start_button'):
            is_running = self.translator.is_running
            btn_text = lng.get_label('stop_btn', 'Stop') if is_running else lng.get_label('start_btn', 'Start')
            btn_icon = "⏹" if is_running else "▶"
            self.start_button.setText(f"{btn_icon} {btn_text} (~)")
            
            # Dynamic styling: Green for Stop (ready to start), Red for Start (ready to stop)
            bg_color = "#f44336" if is_running else "#4CAF50" # Red vs Green
            hover_color = "#d32f2f" if is_running else "#45a049"
            border_color = "#b71c1c" if is_running else "#388E3C"
            
            self.start_button.setStyleSheet(f"""
                QPushButton#StartButton {{ 
                    background-color: {bg_color}; 
                    color: white; 
                    border-radius: {self.dp(6)}px; 
                    font-weight: bold; 
                    font-size: {self.scaled_font_size_large}pt; 
                    border: {self.dp(1)}px solid {border_color}; 
                }} 
                QPushButton#StartButton:hover {{ 
                    background-color: {hover_color}; 
                }}
            """)

    def dp(self, base_value):
        """Scale a base pixel value according to resolution and DPI."""
        return max(1, round(base_value * self.scale_factor))

    def dpt(self, base_pt):
        """Scale a font size in points according to resolution and DPI."""
        return max(1, round((base_pt * self.resolution_factor) / self.device_pixel_ratio))

    def init_dpi_scaling(self):
        screen = QApplication.primaryScreen()
        if not screen: 
            self.resolution_factor = 1.0
            self.device_pixel_ratio = 1.0
            self.scale_factor = 1.0
            self.scaled_font_size = 14
            self.scaled_font_size_large = 16
            return
            
        self.device_pixel_ratio = screen.devicePixelRatio()
        geom = screen.geometry()
        
        self.raw_screen_width = geom.width() * self.device_pixel_ratio
        self.resolution_factor = self.raw_screen_width / 1920.0
        self.scale_factor = self.resolution_factor / self.device_pixel_ratio
        
        self.BASE_FONT_SIZE = 14
        self.scaled_font_size = self.dpt(self.BASE_FONT_SIZE)
        self.scaled_font_size_large = self.dpt(self.BASE_FONT_SIZE + 2)
        
        self.base_width = self.dp(600)
        self.base_height = self.dp(750)
        self.setMinimumSize(self.dp(500), self.dp(500))
        self.resize(self.base_width, self.base_height)
        
        # Apply Startup Position and Geometry with a slight delay
        # This ensures the OS window manager allows the resize/move call
        QTimer.singleShot(100, self.apply_startup_geometry)

    def apply_startup_geometry(self):
        """Position window on 1/3 of screen width or restore last session state."""
        if not self.translator: return
        cfg = self.translator.config['Settings']
        
        # Get screen geometry
        screen = QApplication.primaryScreen()
        if not screen: return
        screen_geom = screen.availableGeometry()
        
        try:
            x_norm = int(cfg.get('window_x', '-1'))
            y_norm = int(cfg.get('window_y', '-1'))
            w_norm = int(cfg.get('window_width', '-1'))
            h_show_norm = int(cfg.get('window_height_show', '-1'))
            
            # Default width is 760 logical units
            target_w = round(760 * self.scale_factor)
            
            # Title bar correction: frameGeometry includes the title bar, geometry does not.
            # The Windows title bar is ~31 logical pixels regardless of DPI/resolution.
            # We must NOT scale this with dp() since availableGeometry() returns logical pixels.
            frame_correction = self.frameGeometry().height() - self.geometry().height()
            if frame_correction <= 0: frame_correction = 31  # Fixed logical pixels fallback
            
            target_h_full = screen_geom.height() - frame_correction
            
            if x_norm == -1:
                # First time placement logic - Force Left Flush (0,0) and default width
                self.move(screen_geom.topLeft())
                
                # Pre-populate config with target full height and width for future Show mode transitions
                self.translator.config['Settings']['window_height_show'] = str(round(target_h_full / self.scale_factor))
                self.translator.config['Settings']['window_width'] = str(round(target_w / self.scale_factor))
                
                if self.translator.ui_visibility_mode == 'Show':
                    self.resize(target_w, target_h_full)
                else:
                    self.resize(target_w, self.height())
                    self.apply_visibility_settings('Hide')
                
                # Immediately save these first-time values to INI
                self.translator.save_settings()
            else:
                # Denormalize values by multiplying with current scale_factor (using round)
                x = round(x_norm * self.scale_factor)
                y = round(y_norm * self.scale_factor)
                w = round(w_norm * self.scale_factor)
                h_show = round(h_show_norm * self.scale_factor)

                width_to_set = w if w > 0 else target_w
                self.move(x, y)
                
                if self.translator.ui_visibility_mode == 'Show':
                    height_to_set = h_show if h_show > 0 else target_h_full
                    self.resize(width_to_set, height_to_set)
                else:
                    self.resize(width_to_set, self.height())
                    self.apply_visibility_settings('Hide')
        except Exception as e:
            log_debug(f"Error applying startup geometry: {e}")

    def init_ui(self):
        self.app_font = self.font()
        self.app_font.setFamily('Segoe UI')
        self.app_font.setPointSize(self.scaled_font_size)
        self.setFont(self.app_font)
        
        self.setStyleSheet(f"""
            /* Tooltip style: black, non-bold */
            QToolTip {{ color: black; font-weight: normal; background-color: #f5f5f5; border: {self.dp(1)}px solid #ccc; }}
            
            QMainWindow, QWidget#centralWidget {{ background-color: #F0F8FF; }}
            QWidget {{ font-family: 'Segoe UI', sans-serif; font-size: {self.scaled_font_size}pt; }}
            
            /* Edits - clean background and highlight */
            QLineEdit {{ 
                background-color: #FFFFFF; 
                border: {self.dp(1)}px solid #B0C4DE; 
                border-radius: {self.dp(4)}px; 
                padding: {self.dp(5)}px; 
                font-size: {self.scaled_font_size}pt;
            }}
            QComboBox {{ 
                background-color: #FFFFFF; 
                border: {self.dp(1)}px solid #B0C4DE; 
                border-radius: {self.dp(4)}px; 
                padding: {self.dp(5)}px; 
                padding-right: {self.dp(30)}px; 
                font-size: {self.scaled_font_size}pt;
            }}
            QComboBox#ConfigModeCombo {{
                padding-right: {self.dp(5)}px;
            }}
            QComboBox QAbstractItemView::item {{
                padding: {self.dp(5)}px;
                padding-right: {self.dp(20)}px;
            }}
            QLineEdit:focus, QComboBox:focus {{ border: {self.dp(1)}px solid #2196F3; }}
            
            /* Disabled states for Simple mode */
            QComboBox:disabled {{ background-color: #E8E8E8; color: #999999; border: {self.dp(1)}px solid #D0D0D0; }}
            QComboBox#ConfigModeCombo:disabled {{
                padding-right: {self.dp(5)}px; 
            }}
            
            /* Remove QComboBox box */
            QComboBox::drop-down {{
                width: 0px;
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
            }}
            
            /* CheckBox */
            QCheckBox::indicator {{
                width: {self.dp(16)}px;
                height: {self.dp(16)}px;
                border: {self.dp(1)}px solid #B0C4DE;
                border-radius: {self.dp(3)}px;
                background-color: #FFFFFF;
            }}
            QCheckBox::indicator:checked {{
                background-color: #2196F3;
                border: {self.dp(1)}px solid #1E88E5;
                image: none;
            }}
            QCheckBox::indicator:hover {{ border: {self.dp(1)}px solid #2196F3; }}
            QCheckBox:disabled {{ color: #999999; }}
            QCheckBox::indicator:disabled {{ background-color: #E8E8E8; border: {self.dp(1)}px solid #D0D0D0; }}
            QCheckBox::indicator:disabled:checked {{ background-color: #B0B0B0; border: {self.dp(1)}px solid #999999; }}
            
            /* TABS */
            QTabWidget::pane {{ 
                border: {self.dp(1)}px solid #B0C4DE; 
                border-radius: {self.dp(6)}px; 
                background-color: #FFFFFF; 
            }}
            QTabBar::tab {{ 
                background-color: #2196F3; 
                color: #FFFFFF;
                border: {self.dp(1)}px solid #1E88E5; 
                padding: {self.dp(10)}px {self.dp(18)}px; 
                margin-right: {self.dp(2)}px; 
                border-top-left-radius: {self.dp(4)}px; 
                border-top-right-radius: {self.dp(4)}px; 
                font-size: {self.scaled_font_size}pt;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{ 
                background-color: #4CAF50; 
                border-bottom-color: #4CAF50; 
            }}
            QTabBar::tab:hover:!selected {{ background-color: #42A5F5; }}
            
            QTabWidget QWidget#scrollContent {{ background-color: #FFFFFF; }}
            QTabWidget QGroupBox {{ background-color: #F0F8FF; }}
            
            QScrollBar:vertical {{
                background: #E6F2FF;
                width: {self.dp(14)}px;
                margin: 0px 0px 0px 0px;
                border: {self.dp(1)}px solid #B0C4DE;
                border-radius: {self.dp(4)}px;
            }}
            QScrollBar::handle:vertical {{
                background: #87CEFA;
                min-height: {self.dp(20)}px;
                border-radius: {self.dp(4)}px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            
            QGroupBox {{ 
                font-weight: bold; 
                border: {self.dp(1)}px solid #B0C4DE; 
                border-radius: {self.dp(6)}px; 
                margin-top: {self.dp(15)}px; 
                font-size: {self.scaled_font_size}pt;
            }}
            QGroupBox::title {{ 
                subcontrol-origin: margin; 
                left: {self.dp(10)}px; 
                padding: 0 {self.dp(5)}px; 
                color: #1565C0;
            }}
            
            /* CustomSpinBox */
            CustomSpinBox QLabel {{
                background-color: #FFFFFF;
                border-top: {self.dp(1)}px solid #B0C4DE;
                border-bottom: {self.dp(1)}px solid #B0C4DE;
                padding: {self.dp(3)}px;
                font-size: {self.scaled_font_size}pt;
            }}
            CustomSpinBox QPushButton {{
                background-color: #E6F2FF;
                border: {self.dp(1)}px solid #B0C4DE;
                border-radius: 0px;
                font-weight: bold;
                color: #1565C0;
                font-size: {self.scaled_font_size}pt;
                padding: {self.dp(4)}px;
                width: {self.dp(26)}px;
            }}
            CustomSpinBox QPushButton:hover {{ background-color: #87CEFA; color: white; }}
            CustomSpinBox QPushButton:pressed {{ background-color: #2196F3; }}
            CustomSpinBox QPushButton:disabled {{ background-color: #E8E8E8; color: #999999; border: {self.dp(1)}px solid #D0D0D0; }}
            CustomSpinBox QLabel:disabled {{ background-color: #E8E8E8; color: #999999; border-top: {self.dp(1)}px solid #D0D0D0; border-bottom: {self.dp(1)}px solid #D0D0D0; }}
            
            /* Standard buttons */
            QPushButton {{
                background-color: #2196F3;
                color: #FFFFFF;
                border: {self.dp(1)}px solid #1E88E5;
                font-weight: bold;
                border-radius: {self.dp(4)}px;
                padding: {self.dp(6)}px {self.dp(12)}px;
                font-size: {self.scaled_font_size}pt;
            }}
            QPushButton:hover {{ background-color: #42A5F5; }}
            QPushButton:pressed {{ background-color: #1E88E5; }}
            QPushButton:disabled {{ background-color: #C0C0C0; color: #888888; border: {self.dp(1)}px solid #AAAAAA; }}
        """)
        
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        # Consistent icon scaling for standard QToolBar actions
        self.toolbar.setIconSize(QSize(self.dp(20), self.dp(20)))
        
        tb_style = f"""
            QToolBar {{ 
                background-color: #FFFFFF; 
                border-bottom: {self.dp(1)}px solid #B0C4DE; 
                padding: {self.dp(4)}px; 
            }}
            QToolButton {{
                font-size: {self.scaled_font_size}pt;
                padding: {self.dp(4)}px {self.dp(8)}px;
                border-radius: {self.dp(4)}px;
                color: #757575;
                font-weight: normal;
            }}
            QToolButton[active=true] {{
                font-weight: bold;
                color: #333333;
            }}
            QToolButton[active=false] {{
                font-weight: normal;
                color: #757575;
            }}
            QToolButton:hover {{
                background-color: #F0F0F0;
            }}
        """
        self.toolbar.setStyleSheet(tb_style)
        self.addToolBar(self.toolbar)
        self.action_source = self.toolbar.addAction("Source", self.toggle_source_overlay)
        self.action_target = self.toolbar.addAction("Target", self.toggle_target_overlay)
        
        # Config Mode toggle (Simple / Custom)
        self.toolbar.addSeparator()
        self.config_mode_btn = SegmentedToggle(self, active_color="#2196F3")
        self.config_mode_btn.valueChanged.connect(self.on_config_mode_changed)
        self.toolbar.addWidget(self.config_mode_btn)
        
        # Separator before Settings
        self.toolbar.addSeparator()
        
        # Settings button (Visibility Toggle)
        self.settings_visibility_btn = StatusToggleButton("Settings", active_color="#2196F3", parent=self)
        self.settings_visibility_btn.clicked.connect(self.on_settings_btn_clicked)
        self.toolbar.addWidget(self.settings_visibility_btn)
        
        # Separator before Help
        self.toolbar.addSeparator()
        
        # Top Visibility Toggle
        self.top_visibility_btn = QPushButton()
        self.top_visibility_btn.setFixedSize(self.dp(32), self.dp(32))
        self.top_visibility_btn.setIconSize(QSize(self.dp(20), self.dp(20)))
        self.top_visibility_btn.setCursor(Qt.PointingHandCursor)
        self.top_visibility_btn.setStyleSheet("""
            QPushButton { background-color: transparent; border: none; border-radius: 4px; }
            QPushButton:hover { background-color: #e5e7eb; }
            QPushButton:pressed { background-color: #d1d5db; }
        """)
        self.top_visibility_btn.clicked.connect(self.on_top_visibility_btn_clicked)
        self.toolbar.addWidget(self.top_visibility_btn)
        
        # Help Icon on Toolbar (Getting Started)
        self.toolbar_help_btn = HelpButton("getting_started", "info-icon.svg", parent=self, tooltip_key="tooltip_open_user_manual")
        # Adjust size for toolbar consistency (20x20 icon size as per line 1530)
        self.toolbar_help_btn.setFixedSize(self.dp(32), self.dp(32))
        self.toolbar_help_btn.setIconSize(QSize(self.dp(20), self.dp(20)))
        self.toolbar.addWidget(self.toolbar_help_btn)

        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")
        self.central_widget.setAttribute(Qt.WA_StyledBackground, True)
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(self.dp(15), self.dp(10), self.dp(15), self.dp(10))
        self.main_layout.setSpacing(self.dp(5))
        
        form_layout = QFormLayout()
        form_layout.setSpacing(self.dp(12))
        self.source_lang_combo = QComboBox(); self.source_lang_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.source_lang_combo.view().setTextElideMode(Qt.ElideNone)
        self.target_lang_combo = QComboBox(); self.target_lang_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.target_lang_combo.view().setTextElideMode(Qt.ElideNone)
        self.lbl_source_lang = QLabel("Source:")
        hbox_sl = QHBoxLayout(); hbox_sl.addWidget(self.source_lang_combo); hbox_sl.addStretch()
        form_layout.addRow(self.lbl_source_lang, hbox_sl)
        self.lbl_target_lang = QLabel("Target:")
        hbox_tl = QHBoxLayout(); hbox_tl.addWidget(self.target_lang_combo); hbox_tl.addStretch()
        form_layout.addRow(self.lbl_target_lang, hbox_tl)

        self.gemini_api_key_entry = QLineEdit(); self.gemini_api_key_entry.setEchoMode(QLineEdit.Password); self.gemini_api_key_entry.setMinimumWidth(self.dp(200))
        self.deepl_api_key_entry = QLineEdit(); self.deepl_api_key_entry.setEchoMode(QLineEdit.Password); self.deepl_api_key_entry.setMinimumWidth(self.dp(200))
        
        self.show_gemini_key_btn = QPushButton("Show")
        self.show_gemini_key_btn.clicked.connect(lambda: self.toggle_key_visibility(self.gemini_api_key_entry, self.show_gemini_key_btn))
        self.show_deepl_key_btn = QPushButton("Show")
        self.show_deepl_key_btn.clicked.connect(lambda: self.toggle_key_visibility(self.deepl_api_key_entry, self.show_deepl_key_btn))
        
        self.lbl_gemini_key = QLabel("Gemini Key:")
        hbox_gk = QHBoxLayout(); hbox_gk.addWidget(self.gemini_api_key_entry); hbox_gk.addWidget(self.show_gemini_key_btn)
        form_layout.addRow(self.lbl_gemini_key, hbox_gk)
        self.lbl_deepl_key = QLabel("DeepL Key:")
        hbox_dk = QHBoxLayout(); hbox_dk.addWidget(self.deepl_api_key_entry); hbox_dk.addWidget(self.show_deepl_key_btn)
        form_layout.addRow(self.lbl_deepl_key, hbox_dk)
        
        self.top_config_widget = QWidget()
        self.top_config_widget.setLayout(form_layout)
        self.main_layout.addWidget(self.top_config_widget)

        self.start_button = QPushButton("START TRANSLATION (~)")
        self.start_button.setObjectName("StartButton")
        self.start_button.setMinimumHeight(self.dp(50))
        start_font = QFont('Segoe UI', self.scaled_font_size_large, QFont.Weight.Bold)
        self.start_button.setFont(start_font)
        self.start_button.setStyleSheet(f"QPushButton#StartButton {{ background-color: #4CAF50; color: white; border-radius: {self.dp(6)}px; font-weight: bold; font-size: {self.scaled_font_size_large}pt; border: {self.dp(1)}px solid #388E3C; }} QPushButton#StartButton:hover {{ background-color: #45a049; }}")
        self.start_button.clicked.connect(self.toggle_translation)
        self.main_layout.addWidget(self.start_button)

        self.tab_widget = QTabWidget()
        tab_font = QFont('Segoe UI', self.scaled_font_size + 1, QFont.Weight.Bold)
        self.tab_widget.tabBar().setFont(tab_font)
        self.main_layout.addWidget(self.tab_widget)
        
        self.init_tabs()

        self.save_settings_btn = QPushButton("Save Settings")
        self.save_settings_btn.setMinimumHeight(self.dp(40))
        save_font = QFont('Segoe UI', self.scaled_font_size, QFont.Weight.Bold)
        self.save_settings_btn.setFont(save_font)
        self.save_settings_btn.setStyleSheet(f"QPushButton {{ font-weight: bold; background-color: #2196F3; color: #FFFFFF; border: {self.dp(1)}px solid #1E88E5; border-radius: {self.dp(6)}px; font-size: {self.scaled_font_size}pt; }} QPushButton:hover {{ background-color: #42A5F5; }}")
        self.save_settings_btn.clicked.connect(lambda: self.save_all_settings(manual=True))
        
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet(f"font-size: {self.scaled_font_size}pt; color: #555;")
        
        self.licence_status_label = QLabel("Licence: FREE")
        self.licence_status_label.setStyleSheet(f"font-size: {self.scaled_font_size}pt; color: #555;")
        
        hbox_bottom = QHBoxLayout()
        hbox_bottom.addWidget(self.save_settings_btn)
        hbox_bottom.addSpacing(self.dp(20))
        hbox_bottom.addWidget(self.licence_status_label)
        hbox_bottom.addSpacing(self.dp(20))
        hbox_bottom.addWidget(self.status_label)
        hbox_bottom.addStretch()
        self.main_layout.addLayout(hbox_bottom)
        
        # Spacer at the very bottom that expands only in Hide mode
        self.bottom_stretch = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.main_layout.addSpacerItem(self.bottom_stretch)
        
        self.setStatusBar(QStatusBar(self))

    def init_tabs(self):
        # 1. Settings
        self.tab_settings = QScrollArea()
        self.tab_settings.setWidgetResizable(True)
        self.tab_settings.setFrameShape(QFrame.NoFrame)
        self.settings_content = QWidget()
        self.settings_content.setObjectName("scrollContent")
        
        main_settings_layout = QVBoxLayout(self.settings_content)
        main_settings_layout.setContentsMargins(self.dp(15), self.dp(15), self.dp(15), self.dp(15))
        main_settings_layout.setSpacing(self.dp(15))
        
        # -- GROUP 1: Models & API --
        self.grp_models = QGroupBox("Models and Context")
        self.models_form_layout = QFormLayout(self.grp_models)
        self.models_form_layout.setContentsMargins(self.dp(15), self.dp(20), self.dp(15), self.dp(15))
        self.models_form_layout.setSpacing(self.dp(12))
        
        # Models row 1 with help
        self.translation_model_combo = QComboBox(); self.translation_model_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.translation_model_combo.view().setTextElideMode(Qt.ElideNone)
        self.translation_model_combo.currentIndexChanged.connect(self.on_translation_model_changed)
        self.lbl_translation_model = QLabel()
        
        container_tm = QWidget(); container_tm.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        hbox_tm = QHBoxLayout(container_tm); hbox_tm.setContentsMargins(0,0,0,0)
        hbox_tm.addWidget(self.translation_model_combo); hbox_tm.addStretch()
        hbox_tm.addWidget(HelpButton("settings-models", "info", parent=self))
        self.models_form_layout.addRow(self.lbl_translation_model, container_tm)
        
        self.ocr_model_combo = QComboBox(); self.ocr_model_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.ocr_model_combo.view().setTextElideMode(Qt.ElideNone)
        self.lbl_ocr_model = QLabel()
        hbox_om = QHBoxLayout(); hbox_om.addWidget(self.ocr_model_combo); hbox_om.addStretch()
        self.models_form_layout.addRow(self.lbl_ocr_model, hbox_om)
        
        # Gemini Context row (Index 2)
        self.gemini_context_combo = QComboBox(); self.gemini_context_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.gemini_context_combo.view().setTextElideMode(Qt.ElideNone)
        self.lbl_gemini_context = QLabel()
        hbox_gc = QHBoxLayout(); hbox_gc.addWidget(self.gemini_context_combo); hbox_gc.addStretch()
        self.models_form_layout.addRow(self.lbl_gemini_context, hbox_gc)
        
        # DeepL Context row (Index 3)
        self.deepl_context_combo = QComboBox(); self.deepl_context_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.deepl_context_combo.view().setTextElideMode(Qt.ElideNone)
        self.lbl_deepl_context = QLabel()
        hbox_dc = QHBoxLayout(); hbox_dc.addWidget(self.deepl_context_combo); hbox_dc.addStretch()
        self.models_form_layout.addRow(self.lbl_deepl_context, hbox_dc)
        
        main_settings_layout.addWidget(self.grp_models)
        
        # -- GROUP 2: Behavior --
        self.grp_behavior = QGroupBox("App Behavior")
        l_beh = QFormLayout(self.grp_behavior)
        l_beh.setContentsMargins(self.dp(15), self.dp(20), self.dp(15), self.dp(15))
        l_beh.setSpacing(self.dp(12))
        
        self.auto_detect_check = QCheckBox()
        self.auto_detect_check.toggled.connect(self.update_auto_detect_label)
        self.lbl_auto_detect_text = QLabel()

        self.lbl_auto_detect_text.mousePressEvent = lambda e: self.auto_detect_check.toggle()
        self.lbl_discovery_time = QLabel()
        self.lbl_discovery_time.setFixedWidth(self.dp(45))
        self.lbl_discovery_time.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_discovery_unit = QLabel()
        self.discovery_timeout_spin = CustomSpinBox(10, 600, 10)
        self.discovery_timeout_spin.btn_minus.setStyleSheet(f"border-top-left-radius: {self.dp(4)}px; border-bottom-left-radius: {self.dp(4)}px;")
        self.discovery_timeout_spin.btn_plus.setStyleSheet(f"border-top-right-radius: {self.dp(4)}px; border-bottom-right-radius: {self.dp(4)}px;")
        self.discovery_timeout_spin.setMinimumWidth(self.dp(160))
        self.discovery_timeout_spin.setMaximumWidth(self.dp(160))
        
        # Helper: small info icon label with tooltip
        info_style = f"color: black; font-size: {self.dp(13)}px;"
        
        self.info_find_subtitles = HelpButton(anchor="find-subtitles", icon_name="info", parent=self)
        
        # Row 1: Find Subtitles  ?  |  Time:  [spin] seconds
        hbox_ad_label = QHBoxLayout(); hbox_ad_label.setContentsMargins(0,0,0,0)
        hbox_ad_label.setSpacing(self.dp(8))
        hbox_ad_label.addWidget(self.auto_detect_check)
        hbox_ad_label.addWidget(self.lbl_auto_detect_text)
        hbox_ad_label.addWidget(self.info_find_subtitles)
        hbox_ad_label.addStretch()
        ad_label_widget = QWidget(); ad_label_widget.setLayout(hbox_ad_label)
        ad_label_widget.setFixedWidth(self.dp(320))
        
        # Row 1: Find Subtitles (Label) | Spinbox + Help Icons (Field)
        self.discovery_timeout_container = QWidget()
        self.discovery_timeout_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        hbox_ad_field = QHBoxLayout(self.discovery_timeout_container)
        hbox_ad_field.setContentsMargins(0, 0, 0, 0)
        hbox_ad_field.setSpacing(self.dp(10))
        hbox_ad_field.addWidget(self.lbl_discovery_time)
        hbox_ad_field.addWidget(self.discovery_timeout_spin)
        hbox_ad_field.addWidget(self.lbl_discovery_unit)
        
        ad_field_wrapper = QWidget()
        hbox_ad_wrapper = QHBoxLayout(ad_field_wrapper)
        hbox_ad_wrapper.setContentsMargins(0, 0, 0, 0)
        hbox_ad_wrapper.setSpacing(self.dp(10))
        hbox_ad_wrapper.addWidget(self.discovery_timeout_container)
        hbox_ad_wrapper.addStretch()
        hbox_ad_wrapper.addWidget(HelpButton("settings-behaviour", "info", parent=self))
        hbox_beh_top_lightbulb = HelpButton("premium-features", "lightbulb", parent=self)
        hbox_ad_wrapper.addWidget(hbox_beh_top_lightbulb)
        
        l_beh.addRow(ad_label_widget, ad_field_wrapper)
        
        # Row 2: Scan Wider  ℹ  |  [spin] 25%
        self.info_scan_wider = HelpButton(anchor="scan-wider", icon_name="info", parent=self)
        
        self.capture_padding_check = QCheckBox()
        self.capture_padding_check.toggled.connect(self.update_capture_padding_label)
        self.lbl_capture_padding_text = QLabel()

        self.lbl_capture_padding_text.mousePressEvent = lambda e: self.capture_padding_check.toggle()
        self.capture_padding_spin = CustomSpinBox(50, 1000, 50)
        self.capture_padding_spin.btn_minus.setStyleSheet(f"border-top-left-radius: {self.dp(4)}px; border-bottom-left-radius: {self.dp(4)}px;")
        self.capture_padding_spin.btn_plus.setStyleSheet(f"border-top-right-radius: {self.dp(4)}px; border-bottom-right-radius: {self.dp(4)}px;")
        self.capture_padding_spin.setMinimumWidth(self.dp(160))
        self.capture_padding_spin.setMaximumWidth(self.dp(160))
        self.capture_padding_value_label = QLabel()
        self.capture_padding_spin.valueChanged.connect(self._on_capture_padding_changed)
        
        hbox_cp_label = QHBoxLayout(); hbox_cp_label.setContentsMargins(0,0,0,0)
        hbox_cp_label.setSpacing(self.dp(8))
        hbox_cp_label.addWidget(self.capture_padding_check)
        hbox_cp_label.addWidget(self.lbl_capture_padding_text)
        hbox_cp_label.addWidget(self.info_scan_wider)
        hbox_cp_label.addStretch()
        cp_label_widget = QWidget(); cp_label_widget.setLayout(hbox_cp_label)
        cp_label_widget.setFixedWidth(self.dp(320))
        
        self.capture_padding_container = QWidget()
        hbox_cp_field = QHBoxLayout(self.capture_padding_container); hbox_cp_field.setContentsMargins(0,0,0,0)
        hbox_cp_field.setSpacing(self.dp(10))
        hbox_cp_field.addSpacing(self.dp(55))
        hbox_cp_field.addWidget(self.capture_padding_spin)
        hbox_cp_field.addWidget(self.capture_padding_value_label)
        hbox_cp_field.addStretch()
        
        l_beh.addRow(cp_label_widget, self.capture_padding_container)
        
        # Row 3: Target Area on Source Area  ℹ
        self.info_target_on_source = HelpButton(anchor="target-on-source", icon_name="info", parent=self)
        
        self.target_on_source_check = QCheckBox()
        self.target_on_source_check.toggled.connect(self.update_target_on_source_label)
        self.lbl_target_on_source_text = QLabel()

        self.lbl_target_on_source_text.mousePressEvent = lambda e: self.target_on_source_check.toggle()
        
        hbox_tos = QHBoxLayout(); hbox_tos.setContentsMargins(0,0,0,0)
        hbox_tos.setSpacing(self.dp(8))
        hbox_tos.addWidget(self.target_on_source_check)
        hbox_tos.addWidget(self.lbl_target_on_source_text)
        hbox_tos.addWidget(self.info_target_on_source)
        hbox_tos.addStretch()
        tos_widget = QWidget(); tos_widget.setLayout(hbox_tos)
        tos_widget.setFixedWidth(self.dp(320))
        l_beh.addRow(tos_widget)
        
        self.keep_linebreaks_check = QCheckBox()
        l_beh.addRow(self.keep_linebreaks_check)
        
        self.scan_interval_spin = CustomSpinBox(500, 5000, 50)
        self.scan_interval_spin.btn_minus.setStyleSheet(f"border-top-left-radius: {self.dp(4)}px; border-bottom-left-radius: {self.dp(4)}px;")
        self.scan_interval_spin.btn_plus.setStyleSheet(f"border-top-right-radius: {self.dp(4)}px; border-bottom-right-radius: {self.dp(4)}px;")
        self.scan_interval_spin.setMinimumWidth(self.dp(160))
        self.scan_interval_spin.setMaximumWidth(self.dp(160))
        self.lbl_scan_interval = QLabel()
        hbox_si = QHBoxLayout(); hbox_si.setContentsMargins(0,0,0,0)
        hbox_si.addSpacing(self.dp(55))
        hbox_si.addWidget(self.scan_interval_spin); hbox_si.addStretch()
        l_beh.addRow(self.lbl_scan_interval, hbox_si)
        
        self.clear_timeout_spin = CustomSpinBox(0, 60, 1)
        self.clear_timeout_spin.btn_minus.setStyleSheet(f"border-top-left-radius: {self.dp(4)}px; border-bottom-left-radius: {self.dp(4)}px;")
        self.clear_timeout_spin.btn_plus.setStyleSheet(f"border-top-right-radius: {self.dp(4)}px; border-bottom-right-radius: {self.dp(4)}px;")
        self.clear_timeout_spin.setMinimumWidth(self.dp(160))
        self.clear_timeout_spin.setMaximumWidth(self.dp(160))
        self.lbl_clear_timeout = QLabel()
        hbox_ct = QHBoxLayout(); hbox_ct.setContentsMargins(0,0,0,0)
        hbox_ct.addSpacing(self.dp(55))
        hbox_ct.addWidget(self.clear_timeout_spin); hbox_ct.addStretch()
        l_beh.addRow(self.lbl_clear_timeout, hbox_ct)
        
        main_settings_layout.addWidget(self.grp_behavior)
        
        # -- GROUP 3: Appearance & Formatting --
        self.grp_appearance = QGroupBox("Appearance & Formatting")
        l_app = QFormLayout(self.grp_appearance)
        l_app.setContentsMargins(self.dp(15), self.dp(20), self.dp(15), self.dp(15))
        l_app.setSpacing(self.dp(12))
        
        # Colours Row 1: Source Color
        self.source_color_preview = QFrame(); self.source_color_preview.setFixedSize(self.dp(20), self.dp(20))
        self.source_color_btn = QPushButton(); self.source_color_btn.clicked.connect(lambda: self.pick_color("source"))
        self.lbl_source_color = QLabel()
        
        container_sc = QWidget(); container_sc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        hbox_sc = QHBoxLayout(container_sc); hbox_sc.setContentsMargins(0,0,0,0)
        hbox_sc.setSpacing(self.dp(10))
        hbox_sc.setSpacing(self.dp(10))
        hbox_sc.addWidget(self.source_color_preview)
        hbox_sc.addWidget(self.source_color_btn)
        hbox_sc.addStretch()
        hbox_sc.addWidget(HelpButton("appearance", "info", parent=self))
        l_app.addRow(self.lbl_source_color, container_sc)
        
        self.target_color_preview = QFrame(); self.target_color_preview.setFixedSize(self.dp(20), self.dp(20))
        self.target_color_btn = QPushButton(); self.target_color_btn.clicked.connect(lambda: self.pick_color("target"))
        self.lbl_target_color = QLabel()
        hbox_tc = QHBoxLayout()
        hbox_tc.setContentsMargins(0,0,0,0)
        hbox_tc.setSpacing(self.dp(10))
        hbox_tc.setSpacing(self.dp(10))
        hbox_tc.addWidget(self.target_color_preview)
        hbox_tc.addWidget(self.target_color_btn)
        hbox_tc.addStretch()
        l_app.addRow(self.lbl_target_color, hbox_tc)
        
        self.target_text_color_preview = QFrame(); self.target_text_color_preview.setFixedSize(self.dp(20), self.dp(20))
        self.target_text_color_btn = QPushButton(); self.target_text_color_btn.clicked.connect(lambda: self.pick_color("target_text"))
        self.lbl_target_text_color = QLabel()
        hbox_ttc = QHBoxLayout()
        hbox_ttc.setContentsMargins(0,0,0,0)
        hbox_ttc.setSpacing(self.dp(10))
        hbox_ttc.setSpacing(self.dp(10))
        hbox_ttc.addWidget(self.target_text_color_preview)
        hbox_ttc.addWidget(self.target_text_color_btn)
        hbox_ttc.addStretch()
        l_app.addRow(self.lbl_target_text_color, hbox_ttc)
        
        self.font_type_combo = QComboBox(); self.font_type_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.font_type_combo.view().setTextElideMode(Qt.ElideNone)
        self.lbl_font_type = QLabel()
        hbox_ft = QHBoxLayout(); hbox_ft.addWidget(self.font_type_combo); hbox_ft.addStretch()
        l_app.addRow(self.lbl_font_type, hbox_ft)

        self.font_size_spin = CustomSpinBox(8, 72, 1)
        self.font_size_spin.btn_minus.setStyleSheet(f"border-top-left-radius: {self.dp(4)}px; border-bottom-left-radius: {self.dp(4)}px;")
        self.font_size_spin.btn_plus.setStyleSheet(f"border-top-right-radius: {self.dp(4)}px; border-bottom-right-radius: {self.dp(4)}px;")
        self.font_size_spin.setMinimumWidth(self.dp(160))
        self.font_size_spin.setMaximumWidth(self.dp(160))
        self.lbl_font_size = QLabel()
        hbox_fs = QHBoxLayout(); hbox_fs.setContentsMargins(0,0,0,0)
        hbox_fs.addWidget(self.font_size_spin); hbox_fs.addStretch()
        l_app.addRow(self.lbl_font_size, hbox_fs)
        
        # Opacity
        self.target_opacity_spin = CustomSpinBox(0.0, 1.0, 0.05, is_double=True, decimals=2)
        self.target_text_opacity_spin = CustomSpinBox(0.0, 1.0, 0.05, is_double=True, decimals=2)
        
        self.target_opacity_spin.setMinimumWidth(self.dp(160))
        self.target_opacity_spin.setMaximumWidth(self.dp(160))
        self.target_text_opacity_spin.setMinimumWidth(self.dp(160))
        self.target_text_opacity_spin.setMaximumWidth(self.dp(160))
        
        self.target_opacity_spin.btn_minus.setStyleSheet(f"border-top-left-radius: {self.dp(4)}px; border-bottom-left-radius: {self.dp(4)}px;")
        self.target_opacity_spin.btn_plus.setStyleSheet(f"border-top-right-radius: {self.dp(4)}px; border-bottom-right-radius: {self.dp(4)}px;")
        self.target_text_opacity_spin.btn_minus.setStyleSheet(f"border-top-left-radius: {self.dp(4)}px; border-bottom-left-radius: {self.dp(4)}px;")
        self.target_text_opacity_spin.btn_plus.setStyleSheet(f"border-top-right-radius: {self.dp(4)}px; border-bottom-right-radius: {self.dp(4)}px;")
        
        self.lbl_opacity_bg = QLabel(); self.lbl_opacity_text = QLabel()
        hbox_op_bg = QHBoxLayout(); hbox_op_bg.addWidget(self.target_opacity_spin); hbox_op_bg.addStretch()
        hbox_op_txt = QHBoxLayout(); hbox_op_txt.addWidget(self.target_text_opacity_spin); hbox_op_txt.addStretch()
        l_app.addRow(self.lbl_opacity_bg, hbox_op_bg)
        l_app.addRow(self.lbl_opacity_text, hbox_op_txt)
        
        main_settings_layout.addWidget(self.grp_appearance)
        
        # -- GROUP 4: Performance & Caching --
        self.grp_performance = QGroupBox("Performance & Cache")
        l_perf = QVBoxLayout(self.grp_performance)
        l_perf.setContentsMargins(self.dp(15), self.dp(20), self.dp(15), self.dp(15))
        l_perf.setSpacing(self.dp(12))
        
        self.lbl_file_cache_desc = QLabel()
        self.lbl_file_cache_desc.setWordWrap(True)
        self.lbl_file_cache_desc.setText("File caching saves translations to disk to reduce API costs, and improves performance.")
        
        hbox_perf_help = QHBoxLayout()
        hbox_perf_help.setContentsMargins(0, 0, 0, 0)
        hbox_perf_help.addWidget(self.lbl_file_cache_desc, stretch=1, alignment=Qt.AlignTop)
        hbox_perf_help.addWidget(HelpButton("settings-caching", "info", parent=self), alignment=Qt.AlignTop | Qt.AlignRight)
        l_perf.addLayout(hbox_perf_help)
        
        self.deepl_cache_check = QCheckBox()
        self.gemini_cache_check = QCheckBox()
        self.debug_log_check = QCheckBox()
        self.debug_log_check.toggled.connect(self.update_debug_log_label)
        
        l_perf.addWidget(self.deepl_cache_check)
        l_perf.addWidget(self.gemini_cache_check)
        l_perf.addWidget(self.debug_log_check)
        
        self.clear_caches_btn = QPushButton(); self.clear_caches_btn.clicked.connect(self.do_clear_file_caches)
        self.clear_cache_btn = QPushButton(); self.clear_cache_btn.clicked.connect(self.do_clear_translation_cache)
        self.clear_debug_log_btn = QPushButton(); self.clear_debug_log_btn.clicked.connect(self.do_clear_debug_log)
        
        cache_btn_w = self.dp(320)
        for btn in [self.clear_caches_btn, self.clear_cache_btn, self.clear_debug_log_btn]:
            btn.setMinimumWidth(cache_btn_w)
            hb = QHBoxLayout()
            hb.setContentsMargins(0, 0, 0, 0)
            hb.addWidget(btn)
            hb.addStretch()
            l_perf.addLayout(hb)
        
        main_settings_layout.addWidget(self.grp_performance)
        
        # -- GROUP 5: Interface Language --
        self.grp_lang = QGroupBox("Interface Language")
        l_lang = QFormLayout(self.grp_lang)
        l_lang.setContentsMargins(self.dp(15), self.dp(20), self.dp(15), self.dp(15))
        l_lang.setSpacing(self.dp(12))
        
        self.gui_lang_combo = QComboBox(); self.gui_lang_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.gui_lang_combo.view().setTextElideMode(Qt.ElideNone)
        self.gui_lang_combo.currentIndexChanged.connect(self.on_gui_language_changed)
        self.lbl_gui_lang = QLabel("Language:")
        
        hbox_lang_top = QHBoxLayout()
        hbox_lang_top.setContentsMargins(0, 0, 0, 0)
        hbox_lang_top.addWidget(self.lbl_gui_lang)
        hbox_lang_top.addWidget(self.gui_lang_combo)
        hbox_lang_top.addStretch()
        hbox_lang_top.addWidget(HelpButton("settings-language", "info", parent=self))
        l_lang.addRow(hbox_lang_top)
        
        main_settings_layout.addWidget(self.grp_lang)

        self.tab_settings.setWidget(self.settings_content)
        
        # 2. Costs (API Usage)
        # 2. Costs (API Usage)
        self.tab_costs = QScrollArea()
        self.tab_costs.setWidgetResizable(True)
        self.tab_costs.setFrameShape(QFrame.NoFrame)
        self.costs_content = QWidget()
        self.costs_content.setObjectName("scrollContent")
        
        l_stats = QVBoxLayout(self.costs_content)
        l_stats.setContentsMargins(self.dp(20), self.dp(20), self.dp(20), self.dp(20))
        l_stats.setSpacing(self.dp(15))

        def create_stats_section_qt(provider, type, keys, group_key, group_fallback):
            # Safe localization check during early initialization
            group_title = group_fallback
            if self.translator and hasattr(self.translator, 'ui_lang'):
                group_title = self.translator.ui_lang.get_label(group_key, group_fallback)
            
            group = QGroupBox(group_title)
            layout = QFormLayout(group)
            layout.setContentsMargins(self.dp(15), self.dp(20), self.dp(15), self.dp(15))
            layout.setSpacing(self.dp(8))
            
            labels = {}
            row_widgets = [] # To allow retranslation later
            first_row = True
            for key, lang_key, fallback in keys:
                # Safe localization
                label_text = fallback
                if self.translator and hasattr(self.translator, 'ui_lang'):
                    label_text = self.translator.ui_lang.get_label(lang_key, fallback)
                
                row_label = QLabel(label_text)
                
                val_text = "No data"
                if self.translator and hasattr(self.translator, 'ui_lang'):
                    val_text = self.translator.ui_lang.get_label("api_usage_no_data", "No data")
                
                val_lbl = QLabel(val_text)
                val_lbl.setStyleSheet("color: blue; font-weight: normal;")
                
                if first_row and group_key == "api_usage_section_gemini_translation":
                    hb_row = QHBoxLayout()
                    hb_row.setContentsMargins(0, 0, 0, 0)
                    hb_row.addWidget(val_lbl)
                    hb_row.addStretch()
                    hb_row.addWidget(HelpButton("api-usage", "info", parent=self))
                    layout.addRow(row_label, hb_row)
                    first_row = False
                else:
                    layout.addRow(row_label, val_lbl)
                
                labels[key] = val_lbl
                row_widgets.append((row_label, lang_key, fallback))
            
            # Store metadata for retranslation
            attr_name = f"gui_{provider.lower()}_{type.lower()}_labels"
            setattr(self, attr_name, labels)
            setattr(self, f"{attr_name}_metadata", row_widgets)
            setattr(self, f"{attr_name}_group", group)
            setattr(self, f"{attr_name}_group_key", group_key)
            setattr(self, f"{attr_name}_group_fallback", group_fallback)
            return group

        trans_keys = [
            ("total_calls", "api_usage_total_translation_calls", "Total Translation Calls:"),
            ("total_words", "api_usage_total_words_translated", "Total Words Translated:"),
            ("median_duration", "api_usage_median_duration_translation", "Median Duration:"),
            ("words_per_minute", "api_usage_words_per_minute", "Average Words per Minute:"),
            ("avg_cost_per_word", "api_usage_avg_cost_per_word", "Average Cost per Word:"),
            ("avg_cost_per_call", "api_usage_avg_cost_per_call", "Average Cost per Call:"),
            ("avg_cost_per_minute", "api_usage_avg_cost_per_minute", "Average Cost per Minute:"),
            ("avg_cost_per_hour", "api_usage_avg_cost_per_hour", "Average Cost per Hour:"),
            ("total_cost", "api_usage_total_translation_cost", "Total Translation Cost:")
        ]
        ocr_keys = [
            ("total_calls", "api_usage_total_ocr_calls", "Total OCR Calls:"),
            ("median_duration", "api_usage_median_duration_ocr", "Median Duration:"),
            ("avg_cost_per_call", "api_usage_avg_cost_per_call", "Average Cost per Call:"),
            ("avg_cost_per_minute", "api_usage_avg_cost_per_minute", "Average Cost per Minute:"),
            ("avg_cost_per_hour", "api_usage_avg_cost_per_hour", "Average Cost per Hour:"),
            ("total_cost", "api_usage_total_ocr_cost", "Total OCR Cost:")
        ]
        combined_keys = [
            ("combined_cost_per_minute", "api_usage_combined_cost_per_minute", "Combined Cost per Minute:"),
            ("combined_cost_per_hour", "api_usage_combined_cost_per_hour", "Combined Cost per Hour:"),
            ("total_cost", "api_usage_total_api_cost", "Total API Cost:")
        ]

        l_stats.addWidget(create_stats_section_qt("Gemini", "Translation", trans_keys, "api_usage_section_gemini_translation", "Gemini Translation Statistics"))
        l_stats.addWidget(create_stats_section_qt("Gemini", "OCR", ocr_keys, "api_usage_section_gemini_ocr", "Gemini OCR Statistics"))
        l_stats.addWidget(create_stats_section_qt("Gemini", "Combined", combined_keys, "api_usage_section_gemini_combined", "Combined Gemini Statistics"))

        # DeepL Section
        deepl_title = "DeepL Usage Tracker"
        deepl_usage_label = "DeepL Usage:"
        deepl_usage_loading = "Loading..."
        if self.translator and hasattr(self.translator, 'ui_lang'):
            deepl_title = self.translator.ui_lang.get_label("api_usage_section_deepl", deepl_title)
            deepl_usage_label = self.translator.ui_lang.get_label("deepl_usage_label", deepl_usage_label)
            deepl_usage_loading = self.translator.ui_lang.get_label("deepl_usage_loading", deepl_usage_loading)

        self.grp_deepl_stats = QGroupBox(deepl_title)
        l_deepl = QFormLayout(self.grp_deepl_stats)
        l_deepl.setContentsMargins(self.dp(15), self.dp(20), self.dp(15), self.dp(15))
        self.gui_deepl_usage_lbl = QLabel(deepl_usage_loading)
        self.gui_deepl_usage_lbl.setStyleSheet("color: blue; font-weight: normal;")
        self.lbl_deepl_usage_title = QLabel(deepl_usage_label)
        
        hbox_deepl = QHBoxLayout()
        hbox_deepl.setContentsMargins(0, 0, 0, 0)
        hbox_deepl.addWidget(self.gui_deepl_usage_lbl, stretch=1)
        hbox_deepl.addWidget(HelpButton("deepl-usage", "info", parent=self))
        
        l_deepl.addRow(self.lbl_deepl_usage_title, hbox_deepl)
        l_stats.addWidget(self.grp_deepl_stats)

        # Buttons
        button_layout = QHBoxLayout()
        refresh_stats_btn_text = "Refresh Statistics"
        export_csv_btn_text = "Export (CSV)"
        export_text_btn_text = "Export (Text)"
        copy_stats_btn_text = "Copy"
        if self.translator and hasattr(self.translator, 'ui_lang'):
            refresh_stats_btn_text = self.translator.ui_lang.get_label("api_usage_refresh_btn", refresh_stats_btn_text)
            export_csv_btn_text = self.translator.ui_lang.get_label("api_usage_export_csv_btn", export_csv_btn_text)
            export_text_btn_text = self.translator.ui_lang.get_label("api_usage_export_text_btn", export_text_btn_text)
            copy_stats_btn_text = self.translator.ui_lang.get_label("api_usage_copy_btn", copy_stats_btn_text)

        self.refresh_stats_btn = QPushButton(refresh_stats_btn_text)
        self.refresh_stats_btn.clicked.connect(self.refresh_stats)
        self.export_csv_btn = QPushButton(export_csv_btn_text)
        self.export_csv_btn.clicked.connect(self.export_stats_csv)
        self.export_text_btn = QPushButton(export_text_btn_text)
        self.export_text_btn.clicked.connect(self.export_stats_text)
        self.copy_stats_btn = QPushButton(copy_stats_btn_text)
        self.copy_stats_btn.clicked.connect(self.copy_stats)

        
        btns = [self.refresh_stats_btn, self.export_csv_btn, self.export_text_btn, self.copy_stats_btn]
        fm = self.refresh_stats_btn.fontMetrics()
        max_btn_w = max(fm.boundingRect(btn.text()).width() for btn in btns) + self.dp(40)
        
        for btn in btns:
            btn.setFixedWidth(max_btn_w)
            button_layout.addWidget(btn)
        button_layout.addStretch()
        l_stats.addLayout(button_layout)
        
        l_stats.addSpacing(self.dp(10))
        self.lbl_api_usage_note = QLabel()
        self.lbl_api_usage_note.setStyleSheet("color: gray; font-size: 10pt;")
        self.lbl_api_usage_note.setWordWrap(True)
        self.lbl_api_usage_note.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        l_stats.addWidget(self.lbl_api_usage_note)

        l_stats.addStretch()
        self.tab_costs.setWidget(self.costs_content)


        
        # 3. Shortcuts
        self.tab_shortcuts = QScrollArea()
        self.tab_shortcuts.setWidgetResizable(True)
        self.tab_shortcuts.setFrameShape(QFrame.NoFrame)
        self.shortcuts_content = QWidget()
        self.shortcuts_content.setObjectName("scrollContent")
        
        l_outer_short = QVBoxLayout(self.shortcuts_content)
        l_outer_short.setContentsMargins(self.dp(15), self.dp(15), self.dp(15), self.dp(15))
        
        self.grp_shortcuts = QGroupBox()
        l_short = QVBoxLayout(self.grp_shortcuts)
        l_short.setContentsMargins(self.dp(15), self.dp(20), self.dp(15), self.dp(15))
        l_short.setSpacing(self.dp(12))
        
        self.lbl_sc_start = QLabel()
        self.lbl_sc_start.setMinimumHeight(self.dp(24))
        self.lbl_sc_start.setStyleSheet("font-size: 11pt;")
        
        hbox_sc_start = QHBoxLayout()
        hbox_sc_start.setContentsMargins(0, 0, 0, 0)
        hbox_sc_start.addWidget(self.lbl_sc_start, stretch=1, alignment=Qt.AlignTop)
        hbox_sc_start.addWidget(HelpButton("shortcuts", "info", parent=self), alignment=Qt.AlignTop | Qt.AlignRight)
        l_short.addLayout(hbox_sc_start)

        self.lbl_sc_src = QLabel()
        self.lbl_sc_tgt = QLabel()
        self.lbl_sc_save = QLabel()
        self.lbl_sc_file = QLabel()
        self.lbl_sc_cache = QLabel()
        self.lbl_sc_log = QLabel()
        self.lbl_sc_reset = QLabel()
        self.lbl_sc_screenshot = QLabel()
        
        for lbl in [self.lbl_sc_src, self.lbl_sc_tgt, self.lbl_sc_save, 
                    self.lbl_sc_file, self.lbl_sc_cache, self.lbl_sc_log, self.lbl_sc_reset,
                    self.lbl_sc_screenshot]:
            lbl.setMinimumHeight(self.dp(24))
            lbl.setStyleSheet("font-size: 11pt;") # Slightly larger for readability
            l_short.addWidget(lbl)
            
        l_outer_short.addWidget(self.grp_shortcuts)
        l_outer_short.addStretch()
        
        self.tab_shortcuts.setWidget(self.shortcuts_content)
        
        # 4. About
        self.tab_about = QScrollArea()
        self.tab_about.setWidgetResizable(True)
        self.tab_about.setFrameShape(QFrame.NoFrame)
        self.about_content = QWidget()
        self.about_content.setObjectName("scrollContent")
        
        l_outer_about = QVBoxLayout(self.about_content)
        l_outer_about.setContentsMargins(self.dp(15), self.dp(15), self.dp(15), self.dp(15))
        
        self.grp_about = QGroupBox()
        l_info = QVBoxLayout(self.grp_about)
        l_info.setContentsMargins(self.dp(15), self.dp(20), self.dp(15), self.dp(15))
        l_info.setSpacing(self.dp(12))
        
        hbox_about_rel = QHBoxLayout()
        self.lbl_about_release = QLabel()
        self.lbl_about_release.setStyleSheet("color: #555;")
        hbox_about_rel.addWidget(self.lbl_about_release); hbox_about_rel.addStretch()
        hbox_about_rel.addWidget(HelpButton("about", "info", parent=self))
        l_info.addLayout(hbox_about_rel)
        
        self.lbl_about_copyright = QLabel()
        l_info.addWidget(self.lbl_about_copyright)
        
        self.lbl_about_app_desc = QLabel()
        self.lbl_about_app_desc.setWordWrap(True)
        l_info.addWidget(self.lbl_about_app_desc)

        self.lbl_about_models_desc = QLabel()
        self.lbl_about_models_desc.setWordWrap(True)
        l_info.addWidget(self.lbl_about_models_desc)

        self.lbl_about_manual = QLabel()
        self.lbl_about_manual.setWordWrap(True)
        l_info.addWidget(self.lbl_about_manual)

        # Larger gap after manual info as requested
        l_info.addSpacing(self.dp(15))

        self.lbl_about_tool_header = QLabel()
        self.lbl_about_tool_header.setWordWrap(True)
        l_info.addWidget(self.lbl_about_tool_header)

        self.lbl_about_tool_desc = QLabel()
        self.lbl_about_tool_desc.setWordWrap(True)
        self.lbl_about_tool_desc.setTextFormat(Qt.RichText)
        self.lbl_about_tool_desc.setOpenExternalLinks(True)
        l_info.addWidget(self.lbl_about_tool_desc)
        
        self.check_updates_btn = QPushButton()
        self.check_updates_btn.clicked.connect(self.check_updates_manual)
        self.check_updates_btn.setMinimumWidth(self.dp(200))
        hbox_up = QHBoxLayout(); hbox_up.addWidget(self.check_updates_btn); hbox_up.addStretch()
        l_info.addLayout(hbox_up)
        
        l_outer_about.addWidget(self.grp_about)
        
        # -- GROUP 2: Open-Source Link --
        self.grp_pro = QGroupBox()
        l_pro = QVBoxLayout(self.grp_pro)
        l_pro.setContentsMargins(self.dp(15), self.dp(20), self.dp(15), self.dp(15))
        l_pro.setSpacing(self.dp(12))
        
        self.about_label = QLabel()
        self.about_label.setWordWrap(True)
        self.about_label.setTextFormat(Qt.RichText)
        self.about_label.setOpenExternalLinks(True)
        l_pro.addWidget(self.about_label)
        
        l_outer_about.addWidget(self.grp_pro)

        l_outer_about.addStretch()
        
        self.tab_about.setWidget(self.about_content)
        
        self.tab_widget.addTab(self.tab_settings, "")
        self.init_custom_prompt_tab()
        self.tab_widget.addTab(self.tab_custom_prompt, "")
        self.tab_widget.addTab(self.tab_costs, "")
        self.tab_widget.addTab(self.tab_shortcuts, "")
        self.tab_widget.addTab(self.tab_about, "")

    def init_custom_prompt_tab(self):
        self.tab_custom_prompt = QScrollArea()
        self.tab_custom_prompt.setWidgetResizable(True)
        self.tab_custom_prompt.setFrameShape(QFrame.NoFrame)
        self.custom_prompt_content = QWidget()
        self.custom_prompt_content.setObjectName("scrollContent")
        
        main_l_cp = QVBoxLayout(self.custom_prompt_content)
        main_l_cp.setContentsMargins(self.dp(15), self.dp(15), self.dp(15), self.dp(15))
        main_l_cp.setSpacing(self.dp(15))
        
        # -- GROUP 1: Translation Prompt --
        self.grp_custom_trans = QGroupBox("Translation Prompt")
        l_trans = QVBoxLayout(self.grp_custom_trans)
        l_trans.setContentsMargins(self.dp(15), self.dp(20), self.dp(15), self.dp(15))
        l_trans.setSpacing(self.dp(12))
        
        hbox_cp_trans_info = QHBoxLayout()
        hbox_cp_trans_info.setContentsMargins(0, 0, 0, 0)
        self.lbl_cp_trans_info = QLabel()
        self.lbl_cp_trans_info.setWordWrap(True)
        self.lbl_cp_trans_info.setStyleSheet("color: #555; font-style: italic;")
        hbox_cp_trans_info.addWidget(self.lbl_cp_trans_info, stretch=1, alignment=Qt.AlignTop)
        hbox_cp_trans_info.addWidget(HelpButton("prompts", "info", parent=self), alignment=Qt.AlignTop | Qt.AlignRight)
        l_trans.addLayout(hbox_cp_trans_info)
        
        self.custom_prompt_trans_edit = QTextEdit()
        self.custom_prompt_trans_edit.setMinimumHeight(self.dp(80))
        self.custom_prompt_trans_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        self.custom_prompt_trans_edit.setStyleSheet(f"QTextEdit {{ background-color: #FFFFFF; border: {self.dp(1)}px solid #B0C4DE; border-radius: {self.dp(6)}px; }} "
                                                   f"QTextEdit:disabled {{ background-color: #E8E8E8; color: #999999; border: {self.dp(1)}px solid #D0D0D0; }}")
        l_trans.addWidget(self.custom_prompt_trans_edit, stretch=1)
        
        hb_trans_btns = QHBoxLayout()
        self.custom_prompt_trans_enabled_check = QCheckBox("Enabled")
        hb_trans_btns.addWidget(self.custom_prompt_trans_enabled_check)
        hb_trans_btns.addStretch()
        
        self.save_cp_btn = QPushButton("Save")
        self.save_cp_btn.setMinimumWidth(self.dp(120))
        self.save_cp_btn.clicked.connect(self.save_custom_translation_prompt)
        
        self.reload_cp_btn = QPushButton("Reload")
        self.reload_cp_btn.setMinimumWidth(self.dp(120))
        self.reload_cp_btn.clicked.connect(self.reload_custom_translation_prompt)
        
        hb_trans_btns.addWidget(self.save_cp_btn)
        hb_trans_btns.addWidget(self.reload_cp_btn)
        l_trans.addLayout(hb_trans_btns)
        
        main_l_cp.addWidget(self.grp_custom_trans)
        
        # -- GROUP 2: OCR Prompt --
        self.grp_custom_ocr = QGroupBox("OCR Prompt")
        l_ocr = QVBoxLayout(self.grp_custom_ocr)
        l_ocr.setContentsMargins(self.dp(15), self.dp(20), self.dp(15), self.dp(15))
        l_ocr.setSpacing(self.dp(12))
        
        hbox_cp_ocr_info = QHBoxLayout()
        hbox_cp_ocr_info.setContentsMargins(0, 0, 0, 0)
        self.lbl_cp_ocr_info = QLabel()
        self.lbl_cp_ocr_info.setWordWrap(True)
        self.lbl_cp_ocr_info.setStyleSheet("color: #555; font-style: italic;")
        hbox_cp_ocr_info.addWidget(self.lbl_cp_ocr_info, stretch=1, alignment=Qt.AlignTop)
        hbox_cp_ocr_info.addWidget(HelpButton("ocr-prompt", "info", parent=self), alignment=Qt.AlignTop | Qt.AlignRight)
        hbox_cp_ocr_info.addWidget(HelpButton("ocr-prompt-depth", "lightbulb", parent=self), alignment=Qt.AlignTop)
        l_ocr.addLayout(hbox_cp_ocr_info)
        
        self.custom_prompt_ocr_edit = QTextEdit()
        self.custom_prompt_ocr_edit.setMinimumHeight(self.dp(80))
        self.custom_prompt_ocr_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        self.custom_prompt_ocr_edit.setStyleSheet(f"QTextEdit {{ background-color: #FFFFFF; border: {self.dp(1)}px solid #B0C4DE; border-radius: {self.dp(6)}px; }} "
                                                  f"QTextEdit:disabled {{ background-color: #E8E8E8; color: #999999; border: {self.dp(1)}px solid #D0D0D0; }}")
        l_ocr.addWidget(self.custom_prompt_ocr_edit, stretch=1)
        
        hb_ocr_btns = QHBoxLayout()
        self.custom_prompt_ocr_enabled_check = QCheckBox("Enabled")
        hb_ocr_btns.addWidget(self.custom_prompt_ocr_enabled_check)
        hb_ocr_btns.addStretch()
        
        self.save_ocr_cp_btn = QPushButton("Save")
        self.save_ocr_cp_btn.setMinimumWidth(self.dp(120))
        self.save_ocr_cp_btn.clicked.connect(self.save_custom_ocr_prompt_manual)
        
        self.reload_ocr_cp_btn = QPushButton("Reload")
        self.reload_ocr_cp_btn.setMinimumWidth(self.dp(120))
        self.reload_ocr_cp_btn.clicked.connect(self.reload_custom_ocr_prompt_manual)
        
        hb_ocr_btns.addWidget(self.save_ocr_cp_btn)
        hb_ocr_btns.addWidget(self.reload_ocr_cp_btn)
        l_ocr.addLayout(hb_ocr_btns)
        
        main_l_cp.addWidget(self.grp_custom_ocr)
        
        self.tab_custom_prompt.setWidget(self.custom_prompt_content)

    @Slot()
    def do_clear_file_caches(self):
        if self.translator:
            try:
                self.translator.clear_file_caches()
                self.show_status(self.translator.ui_lang.get_label('status_cache_cleared', "File caches cleared."), 3000)
            except Exception as e:
                log_debug(f"Error clear_file_caches: {e}")

    @Slot()
    def do_clear_translation_cache(self):
        if self.translator:
            try:
                self.translator.clear_cache()
                self.show_status(self.translator.ui_lang.get_label('status_trans_cache_cleared', "Translation cache cleared."), 3000)
            except Exception as e:
                log_debug(f"Error clear_translation_cache: {e}")
                
    @Slot()
    def do_clear_debug_log(self):
        if self.translator:
            try:
                self.translator.clear_debug_log()
                self.show_status(self.translator.ui_lang.get_label('status_debug_log_cleared', "Debug log cleared."), 3000)
            except Exception as e:
                log_debug(f"Error clear_debug_log: {e}")

    def refresh_stats(self):
        if not self.translator: return
        self.translator.refresh_api_statistics()
        self.reload_custom_prompts()
        stats = self.translator.statistics_handler.get_statistics()
        
        # Mapping stats to UI labels
        def update_labels(labels_dict, stat_data):
            for key, lbl in labels_dict.items():
                val = stat_data.get(key, "N/A")
                if "cost" in key:
                    lbl.setText(self.translator.format_currency_for_display(val))
                elif "calls" in key or "words" in key:
                    lbl.setText(self.translator.format_number_with_separators(val))
                elif "duration" in key:
                    suffix = " s" if self.translator.ui_lang.current_lang == 'pol' else "s"
                    val_str = f"{val:.3f}"
                    if self.translator.ui_lang.current_lang == 'pol':
                        val_str = val_str.replace('.', ',')
                    lbl.setText(f"{val_str}{suffix}")

                else:
                    lbl.setText(str(val))

        if hasattr(self, "gui_gemini_translation_labels"):
            update_labels(self.gui_gemini_translation_labels, stats['gemini_translation'])
        if hasattr(self, "gui_gemini_ocr_labels"):
            update_labels(self.gui_gemini_ocr_labels, stats['gemini_ocr'])
        if hasattr(self, "gui_gemini_combined_labels"):
            update_labels(self.gui_gemini_combined_labels, stats['gemini_combined'])
        
        # DeepL
        if hasattr(self, "gui_deepl_usage_lbl"):
            self.gui_deepl_usage_lbl.setText(getattr(self.translator, 'deepl_usage', "N/A"))


    def export_stats_csv(self):
        if self.translator: self.translator.export_statistics_csv()
        
    def export_stats_text(self):
        if self.translator: self.translator.export_statistics_text()

        
    def copy_stats(self):
        if self.translator: self.translator.copy_statistics_to_clipboard()
        
    def check_updates_manual(self):
        if self.translator: self.translator.check_for_updates(auto_check=False)

    def save_custom_translation_prompt(self):
        if not self.translator: return
        text = self.custom_prompt_trans_edit.toPlainText()
        if self.translator.save_custom_prompt(text):
            self.show_status(self.translator.ui_lang.get_label('custom_prompt_saved', 'Custom prompt saved successfully!'), 3000)
        else:
            self.show_status(self.translator.ui_lang.get_label('custom_prompt_save_error', 'Failed to save custom prompt.'), 5000)

    def reload_custom_translation_prompt(self):
        if not self.translator: return
        self.translator.load_custom_prompt() # Loads both
        self.custom_prompt_trans_edit.setPlainText(self.translator.custom_prompt_text)

    def save_custom_ocr_prompt_manual(self):
        if not self.translator: return
        text = self.custom_prompt_ocr_edit.toPlainText()
        if self.translator.save_custom_ocr_prompt(text):
            self.show_status(self.translator.ui_lang.get_label('custom_prompt_saved', 'Custom prompt saved successfully!'), 3000)
        else:
            self.show_status(self.translator.ui_lang.get_label('custom_prompt_save_error', 'Failed to save custom prompt.'), 5000)

    def reload_custom_ocr_prompt_manual(self):
        if not self.translator: return
        self.translator.load_custom_prompt() # Loads both
        self.custom_prompt_ocr_edit.setPlainText(self.translator.custom_ocr_prompt_text)

    def save_custom_prompts(self):
        # Legacy method if still called somewhere, though now we use split methods
        self.save_custom_translation_prompt()
        self.save_custom_ocr_prompt_manual()

    def reload_custom_prompts(self):
        if not self.translator: return
        self.translator.load_custom_prompt()
        self.custom_prompt_trans_edit.setPlainText(self.translator.custom_prompt_text)
        self.custom_prompt_ocr_edit.setPlainText(self.translator.custom_ocr_prompt_text)

    def pick_color(self, color_type):
        if not self.translator: return
        attr = f"{color_type}_colour" if color_type in ["source", "target"] else "target_text_colour"
        initial = getattr(self.translator, attr)
        title = self.translator.ui_lang.get_label(f"choose_{color_type}_color_title", f"Choose {color_type.replace('_',' ')} Colour")
        color_tuple, hex_color = askcolor(initial, title=title)
        if hex_color:
            self._pending_colors[attr] = hex_color
            getattr(self, f"{color_type}_color_preview").setStyleSheet(f"background-color: {hex_color}; border: {self.dp(1)}px solid #8b949e;")
            self._on_setting_changed()

    @Slot()
    def reset_window_geometry(self):
        """Reset window dimensions and position to factory defaults (0,0 with standard width)."""
        if not self.translator: return
        
        # Use Windows API SW_RESTORE to atomically exit any maximize/Ghost-Maximized state
        # without visible flickering. Safe to call even if window is already in Normal state.
        ctypes.windll.user32.ShowWindow(int(self.winId()), 9)  # SW_RESTORE = 9
        QApplication.processEvents()
        
        # Get screen geometry
        screen = QApplication.primaryScreen()
        if not screen: return
        screen_geom = screen.availableGeometry()
        
        # Recalculate frame correction in Normal state for precision
        frame_correction = self.frameGeometry().height() - self.geometry().height()
        if frame_correction <= 0: frame_correction = 31
        
        # Default width calculation matching apply_startup_geometry
        target_w = round(760 * self.scale_factor)
        target_h_full = screen_geom.height() - frame_correction
        
        # Apply reset positioning (Top-Left of primary screen)
        self.move(screen_geom.topLeft())
        
        # Update config with these defaults
        cfg = self.translator.config['Settings']
        cfg['window_x'] = "-1"
        cfg['window_y'] = "-1"
        cfg['window_width'] = str(round(target_w / self.scale_factor))
        cfg['window_height_show'] = str(round(target_h_full / self.scale_factor))
        
        if self.translator.ui_visibility_mode == 'Show':
            self.resize(target_w, target_h_full)
        else:
            self.resize(target_w, self.height())
            
        # Persist reset values
        self.translator.save_settings()
        log_debug("Window geometry reset to defaults via Alt+R.")

    @Slot()
    def toggle_source_overlay(self):
        if self.translator: 
            self.translator.toggle_source_visibility()
            self.update_visibility_btns()

    @Slot()
    def toggle_target_overlay(self):
        if self.translator: 
            self.translator.toggle_target_visibility()
            self.update_visibility_btns()

    @Slot()
    def toggle_translation(self):
        if not self.translator: return
        lng = self.translator.ui_lang
        try:
            self.translator.toggle_translation()
            if self.translator.is_running:
                self.update_status_display()
            else:
                self.update_status_display()
        except Exception as e: 
            if hasattr(self, 'status_label'): self.status_label.setText(f"Error: {e}")

    @Slot()
    def trigger_screenshot(self):
        """Slot invoked by Alt+L hotkey via QMetaObject.invokeMethod."""
        if self.translator:
            self.translator.perform_marketing_screenshot()

    def show_screenshot_toast(self, filename):
        """Display a transient toast notification confirming the screenshot save."""
        prefix = "📸 Screenshot saved:"
        if self.translator:
            prefix = self.translator.ui_lang.get_label('screenshot_saved_toast', prefix)
        self._screenshot_toast = ScreenshotToast(f"{prefix}\n{filename}")
        self._screenshot_toast.show_and_fade()

    def closeEvent(self, event):
        """Standard window close handler — saves all settings automatically."""
        self.save_all_settings()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv); window = MainWindowV4(); window.show(); sys.exit(app.exec())
