#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PySide6 Overlays Module - Unified Architecture v4
-------------------------------------------------
Unified Source/Target overlays based on a common base class.
Supports native dragging, resizing, and anti-recording (OBS).
"""

import sys
import os
import ctypes
if sys.platform == "win32":
    import ctypes.wintypes

from PySide6.QtWidgets import (QApplication, QTextEdit, QVBoxLayout, QMainWindow,
                             QWidget, QFrame)
from PySide6.QtCore import Qt, QRect, QPoint, QSize
from PySide6.QtGui import QIcon, QAction, QFont, QColor, QTextBlockFormat, QTextCursor
from constants import RTL_LANGUAGES

try:
    import arabic_reshaper
    RESHAPER_AVAILABLE = True
except ImportError:
    RESHAPER_AVAILABLE = False

try:
    from logger import log_debug
except ImportError:
    def log_debug(msg): print(f"DEBUG: {msg}")

# -----------------------
# Helper Components
# -----------------------

class VisualTopBar(QWidget):
    """Bar enabling the dragging of the overlay."""
    def __init__(self, parent=None, height: int = 15):
        super().__init__(parent)
        self.setFixedHeight(int(height))
        self.setCursor(Qt.SizeAllCursor)
        self.setMouseTracking(True)
        self._dragging = False
        self._drag_offset = QPoint()

    def _global_pos(self, event):
        try:
            return event.globalPosition().toPoint()
        except AttributeError:
            return event.globalPos()

    def enterEvent(self, event):
        self.setCursor(Qt.SizeAllCursor)
        super().enterEvent(event)

    def leaveEvent(self, event):
        try:
            self.window().unsetCursor()
        except Exception:
            pass
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            used_system_move = False
            win = self.window().windowHandle()
            if win is not None:
                try:
                    used_system_move = win.startSystemMove()
                except Exception:
                    used_system_move = False
            if not used_system_move:
                self._dragging = True
                self._drag_offset = self._global_pos(event) - self.window().frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.setCursor(Qt.SizeAllCursor)
        if self._dragging and (event.buttons() & Qt.LeftButton):
            self.window().move(self._global_pos(event) - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        was_dragging = self._dragging
        self._dragging = False
        super().mouseReleaseEvent(event)
        if was_dragging:
            try:
                win = self.window()
                win._user_moved_flag = True
            except Exception:
                pass

class RTLTextDisplay(QTextEdit):
    """Text component supporting multiple languages including RTL."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("background: transparent; border: none;")
        self._last_text = ""
        self._last_lang = "en"
        self._last_color = "#FFFFFF"
        self._last_font = "Arial"
        self._last_size = 12

    def set_text(self, text, lang_code, color=None, font_family=None, font_size=None, bg_color=None):
        self._last_text = text
        self._last_lang = lang_code
        if color: self._last_color = color
        if font_family: self._last_font = font_family
        if font_size: self._last_size = font_size
        self._refresh_html()

    def set_rtl_text(self, text, lang_code, bg_color="#2c3e50", text_color="#FFFFFF", font_size=12):
        # Adapter for the backend display manager
        self.set_text(text, lang_code, color=text_color, font_size=font_size, bg_color=bg_color)

    def update_text_style(self, color=None, font_family=None, font_size=None):
        if color: self._last_color = color
        if font_family: self._last_font = font_family
        if font_size: self._last_size = font_size
        self._refresh_html()

    def _is_rtl_language(self, lang_code: str) -> bool:
        if not lang_code:
            return False
        # Normalize and check against the central RTL_LANGUAGES set
        normalized_code = lang_code.lower().strip()
        # Direct match or starts with (for variants like ar-SA)
        return any(normalized_code.startswith(l) for l in RTL_LANGUAGES)

    def _detect_rtl_text(self, text: str) -> bool:
        import re
        rtl_pattern = r'[\u0590-\u05FF\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
        return bool(re.search(rtl_pattern, text))

    def _refresh_html(self):
        try:
            lang_code = self._last_lang or "en"
            text = self._last_text or ""
            color = self._last_color or "#FFFFFF"
            font_family = self._last_font or "Arial"
            font_size = self._last_size or 12

            # Calculate resolution-based scale factor (1920 logical baseline)
            # We use logical width here because Qt's HTML 'px' unit is already DPI-aware.
            screen = QApplication.primaryScreen()
            res_factor = 1.0
            if screen:
                # Use logical width to correctly calculate the font-to-frame ratio
                logical_w = screen.geometry().width()
                res_factor = logical_w / 1920.0
            
            # Convert points to scaled pixels (1pt = 1.3333px at 96dpi baseline)
            # This ensures the font takes up the same percentage of the overlay at any resolution.
            scaled_font_px = int(font_size * res_factor * 1.3333)

            is_rtl = False
            if lang_code:
                is_rtl = self._is_rtl_language(lang_code)
            else:
                is_rtl = self._detect_rtl_text(text)

            processed_text = text
            if RESHAPER_AVAILABLE and is_rtl:
                try:
                    processed_text = arabic_reshaper.reshape(text)
                except Exception:
                    pass

            self.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)

            clean_text = "<br>".join([' '.join(line.split()) for line in processed_text.split('\n')])
            align = "right" if is_rtl else "left"
            direction = "rtl" if is_rtl else "ltr"

            # Use 'px' for font-size to ensure consistency
            html = f"""
            <div style="text-align: {align}; direction: {direction}; color: {color};
                        font-family: '{font_family}'; font-size: {scaled_font_px}px;">
                {clean_text}
            </div>
            """

            from logger import log_debug
            log_debug(f"Refreshing HTML in PySide: {text[:20]}... Font: {font_family} -> {scaled_font_px}px, RTL: {is_rtl}")

            self.setHtml(html)

            # Hard override of alignment with AlignAbsolute flag
            cursor = self.textCursor()
            cursor.select(QTextCursor.Document)
            block_fmt = QTextBlockFormat()
            if is_rtl:
                block_fmt.setAlignment(Qt.AlignRight | Qt.AlignAbsolute)
            else:
                block_fmt.setAlignment(Qt.AlignLeft | Qt.AlignAbsolute)
            cursor.mergeBlockFormat(block_fmt)
            cursor.clearSelection()
            cursor.movePosition(QTextCursor.Start)
            self.setTextCursor(cursor)

        except Exception as e:
            from logger import log_debug
            log_debug(f"CRITICAL ERROR IN _refresh_html (RTLTextDisplay): {e}")

    @staticmethod
    def get_dpi_scale_factor():
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if not app: return 1.0
        screen = app.primaryScreen()
        return screen.devicePixelRatio() if screen else 1.0

# -----------------------
# BASE OVERLAY CLASS
# -----------------------

class BasePySideOverlay(QMainWindow):
    """Unified base for Source and Target Overlay."""
    def __init__(self, resolution_factor=1.0, title="GCT Overlay"):
        super().__init__()
        self.resolution_factor = resolution_factor
        self.setWindowTitle(title)

        # UI Configuration
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Draggable Top Bar
        self._top_bar_height = int(15 * self.resolution_factor)
        self.top_bar = VisualTopBar(self.central_widget, height=self._top_bar_height)
        self.layout.addWidget(self.top_bar)

        self.HIT_MARGIN = 5

        # Screenshot freeze support
        self.is_frozen = False
        self.pending_text_update = None

    def apply_anti_feedback(self):
        """No-op in open-source edition (no display affinity manipulation)."""
        pass

    def freeze_for_screenshot(self):
        """Freeze the overlay: block text updates."""
        self.is_frozen = True
        self.pending_text_update = None

    def unfreeze_after_screenshot(self):
        """Unfreeze the overlay: allow text updates."""
        self.is_frozen = False

    def update_style(self, bg_color, opacity, border_px=None):
        self._bg_color = bg_color
        self._opacity = opacity
        if border_px is not None:
            self._border_px = border_px

        b_px = getattr(self, '_border_px', 0)
        c = QColor(bg_color)
        rgba = f"rgba({c.red()}, {c.green()}, {c.blue()}, {opacity})"
        border_rgba = f"rgba({c.red()}, {c.green()}, {c.blue()}, 1.0)"

        style = f"""
            QWidget#CentralWidget {{
                background-color: {rgba};
                border: {b_px}px solid {border_rgba};
            }}
        """
        self.central_widget.setObjectName("CentralWidget")
        self.central_widget.setStyleSheet(style)

    def update_color(self, hex_color, opacity=None):
        """Adapter for backend compatibility - changes color preserving transparency and border."""
        op = opacity if opacity is not None else getattr(self, '_opacity', 0.85)
        self.update_style(hex_color, op)

    def update_text_color(self, color):
        """Adapter for compatibility - overridden in TargetOverlay."""
        pass

    # --- Adapters for backend (app_logic) ---

    def get_scale_factor(self):
        screen = QApplication.primaryScreen()
        if not screen: return 1.0
        dpr = screen.devicePixelRatio()
        geom = screen.geometry()
        raw_w = geom.width() * dpr
        res_factor = raw_w / 1920.0
        return res_factor / dpr

    def get_geometry(self):
        """Returns geometry in [x1, y1, x2, y2] normalized to 1920x1080 resolution."""
        sf = self.get_scale_factor()
        return [
            round(self.x() / sf),
            round(self.y() / sf),
            round((self.x() + self.width()) / sf),
            round((self.y() + self.height()) / sf)
        ]

    def get_capture_geometry(self):
        """Returns geometry in physical pixels (for mss/OCR)."""
        scale = self.devicePixelRatioF()
        return [
            round(self.x() * scale),
            round(self.y() * scale),
            round((self.x() + self.width()) * scale),
            round((self.y() + self.height()) * scale)
        ]

    def move_to_physical_pixels(self, px1, py1, px2, py2):
        """Moves and resizes the overlay using physical coordinate values.
        Converts physical pixels to logical pixels for PySide6.
        """
        try:
            scale = self.devicePixelRatioF()
            if scale <= 0: scale = 1.0
            
            # Convert physical to logical
            lx = round(px1 / scale)
            ly = round(py1 / scale)
            lw = round((px2 - px1) / scale)
            lh = round((py2 - py1) / scale)
            
            # Ensure minimum size
            lw = max(lw, 80)
            lh = max(lh, 40)
            
            # Update window geometry (logical pixels)
            self.setGeometry(lx, ly, lw, lh)
        except Exception as e:
            if "log_debug" in globals():
                log_debug(f"BasePySideOverlay: Error in move_to_physical_pixels: {e}")

    def get_physical_pixels(self):
        """Returns the current window geometry in physical pixels [x1, y1, x2, y2]."""
        return self.get_capture_geometry()
    def winfo_x(self): return self.x()
    def winfo_y(self): return self.y()
    def winfo_width(self): return self.width()
    def winfo_height(self): return self.height()
    def show(self):
        super().show()

    def toggle_visibility(self):
        if self.isVisible(): self.hide()
        else: self.show()

    def nativeEvent(self, eventType, message):
        """Native Windows resize handling with DPI conversion."""
        if sys.platform == "win32" and eventType == "windows_generic_MSG":
            try:
                msg = ctypes.wintypes.MSG.from_address(message.__int__())
                if msg.message == 0x0232:  # WM_EXITSIZEMOVE
                    self._user_moved_flag = True
                if msg.message == 0x0084:  # WM_NCHITTEST
                    x_phys = ctypes.c_short(msg.lParam & 0xFFFF).value
                    y_phys = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                    dpr = self.devicePixelRatio()
                    p = self.mapFromGlobal(QPoint(int(x_phys / dpr), int(y_phys / dpr)))

                    m = self.HIT_MARGIN
                    w, h = self.width(), self.height()

                    # Top corners
                    if p.x() <= m and p.y() <= m: return True, 13  # TOPLEFT
                    if p.x() >= w - m and p.y() <= m: return True, 14  # TOPRIGHT
                    # Bottom corners
                    if p.x() <= m and p.y() >= h - m: return True, 16  # BOTTOMLEFT
                    if p.x() >= w - m and p.y() >= h - m: return True, 17  # BOTTOMRIGHT

                    # Edges
                    if p.y() <= m: return True, 12  # TOP
                    if p.y() >= h - m: return True, 15  # BOTTOM
                    if p.x() <= m: return True, 10  # LEFT
                    if p.x() >= w - m: return True, 11  # RIGHT
            except Exception:
                pass
        return super().nativeEvent(eventType, message)

# -----------------------
# IMPLEMENTATIONS
# -----------------------

class SourceOverlay(BasePySideOverlay):
    def __init__(self, resolution_factor=1.0, initial_color="#FFFF99", initial_opacity=0.70):
        super().__init__(resolution_factor, "Source Area")
        # Empty widget filling space under the top bar (like RTLTextDisplay in TargetOverlay)
        self.body = QWidget(self.central_widget)
        self.body.setStyleSheet("background: transparent;")
        self.layout.addWidget(self.body)
        self.update_style(initial_color, initial_opacity, border_px=0)

class TargetOverlay(BasePySideOverlay):
    def __init__(self, resolution_factor=1.0, initial_color="#663399", initial_opacity=0.85):
        super().__init__(resolution_factor, "Target Area")
        self.text_display = RTLTextDisplay(self.central_widget)
        self.layout.addWidget(self.text_display)
        self.update_style(initial_color, initial_opacity, border_px=0)

    def update_text_color(self, color):
        """Updates text color in PySide6 overlay."""
        self.text_display.update_text_style(color=color)

# -----------------------
# Utility Functions
# -----------------------

def ensure_qapp():
    import sys
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    return app