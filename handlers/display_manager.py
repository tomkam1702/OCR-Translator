from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap, QTextCursor, QTextBlockFormat
import time
import cv2
import numpy as np
import os
from PIL import Image
from logger import log_debug

class DisplayManager:
    """Handles display and UI updates for overlays and debug information using PySide6"""
    
    def __init__(self, app):
        """Initialize with a reference to the main application
        
        Args:
            app: The main GameChangingTranslator application instance
        """
        self.app = app
        self.last_widget_width = 0
        self.current_logical_text = ""
        self.current_language_code = None
        self.last_topmost_reassertion_time = 0 # Track to reduce Z-order noise
    
    def update_translation_text(self, text_to_display):
        """Updates the translation text overlay with new content
        
        Args:
            text_to_display: Text content to display in the overlay
        """
        # Check if the target overlay and text widget references are valid
        if not self.app.target_overlay or not self.app.translation_text:
            return
            
        # Schedule the actual update via the main thread's event loop
        QTimer.singleShot(0, lambda: self._update_translation_text_on_main_thread(text_to_display))

    def _update_translation_text_on_main_thread(self, text_content_main_thread):
        """Updates the translation text widget on the main thread with proper BiDi support
        
        Args:
            text_content_main_thread: Text content to display
        """
        if not self.app.target_overlay or not self.app.translation_text:
            return

        # Screenshot freeze guard: defer text update instead of discarding it
        if getattr(self.app.target_overlay, 'is_frozen', False):
            log_debug("DisplayManager: Overlay frozen for screenshot — deferring text update.")
            self.app.target_overlay.pending_text_update = text_content_main_thread
            return

        try:
            if self.app.is_running:
                if not self.app.target_overlay.isVisible():
                    self.app.target_overlay.show() 
                else:
                    # Only re-assert topmost/lift every 5 seconds to reduce 'Z-order noise'
                    now = time.monotonic()
                    if now - self.last_topmost_reassertion_time > 5.0:
                        self.app.target_overlay.raise_()
                        self.last_topmost_reassertion_time = now

            new_text_to_display = text_content_main_thread.strip() if text_content_main_thread else ""
            log_debug(f"DisplayManager: Processing text for display: '{new_text_to_display}'")

            # Convert <br> tags to newlines for display
            new_text_to_display = new_text_to_display.replace('<br>', '\n')

            # Get the target language code
            target_lang_code = self.app.target_lang
            log_debug(f"DisplayManager: Target language code is '{target_lang_code}'")

            # Store current text and language
            self.current_logical_text = new_text_to_display
            self.current_language_code = target_lang_code
            
            # Update PySide text widget
            log_debug(f"DisplayManager: Using PySide RTL text display for language: {target_lang_code}")
            text_color = self.app.target_text_colour
            font_size = self.app.target_font_size
            font_type = self.app.target_font_type
            bg_color = self.app.target_colour
            
            self.app.translation_text.set_rtl_text(
                new_text_to_display, 
                target_lang_code, 
                bg_color, 
                text_color, 
                font_size
            )
            # Apply font type and size
            self.app.translation_text.update_text_style(font_family=font_type, font_size=font_size)
                
        except Exception as e_uttomt_gen:
            log_debug(f"Unexpected error updating translation text: {type(e_uttomt_gen).__name__} - {e_uttomt_gen}")

    def update_debug_display(self, original_img_pil_udd, processed_img_cv_udd, ocr_text_content_udd):
        """Updates the debug display with current images and OCR text using PySide6
        
        Args:
            original_img_pil_udd: Original screenshot as PIL Image
            processed_img_cv_udd: Processed image as OpenCV numpy array
            ocr_text_content_udd: OCR extracted text content
        """
        # Check for existence of all required UI elements for the debug tab
        required_debug_widgets = ['original_image_label', 'processed_image_label', 'ocr_results_text']
        for widget_name in required_debug_widgets:
            widget_ref = getattr(self.app, widget_name, None)
            if not widget_ref:
                return
                
        try:
            display_width_udd = 250 # Max width for display images in the tab

            # Helper to convert PIL Image to QPixmap
            def pil_to_pixmap(pil_img):
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                data = pil_img.tobytes("raw", "RGB")
                from PySide6.QtGui import QImage
                qimage = QImage(data, pil_img.width, pil_img.height, QImage.Format_RGB888)
                return QPixmap.fromImage(qimage)

            # Original Image
            if original_img_pil_udd:
                try:
                    img_copy_udd = original_img_pil_udd.copy() 
                    h_udd, w_udd = img_copy_udd.height, img_copy_udd.width
                    aspect_ratio_udd = h_udd / w_udd if w_udd > 0 else 1
                    display_height_udd = max(20, int(display_width_udd * aspect_ratio_udd))
                    
                    resample_filter_udd = Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS
                    img_resized_udd = img_copy_udd.resize((display_width_udd, display_height_udd), resample_filter_udd)
                    
                    pixmap = pil_to_pixmap(img_resized_udd)
                    self.app.original_image_label.setPixmap(pixmap)
                except Exception as img_err_udd:
                     log_debug(f"Error processing original image for debug display: {img_err_udd}")
                     self.app.original_image_label.setText("Error Original")

            # Processed Image
            if isinstance(processed_img_cv_udd, np.ndarray):
                try:
                    pil_processed_udd = None
                    if len(processed_img_cv_udd.shape) == 2: # Grayscale
                        pil_processed_udd = Image.fromarray(processed_img_cv_udd)
                    elif len(processed_img_cv_udd.shape) == 3: # Color (BGR from OpenCV)
                        pil_processed_udd = Image.fromarray(cv2.cvtColor(processed_img_cv_udd, cv2.COLOR_BGR2RGB))
                    
                    if pil_processed_udd:
                        h_proc_udd, w_proc_udd = pil_processed_udd.height, pil_processed_udd.width
                        aspect_ratio_proc_udd = h_proc_udd / w_proc_udd if w_proc_udd > 0 else 1
                        display_height_proc_udd = max(20, int(display_width_udd * aspect_ratio_proc_udd))
                        
                        resample_filter_nearest_udd = Image.Resampling.NEAREST if hasattr(Image, 'Resampling') else Image.NEAREST
                        processed_resized_udd = pil_processed_udd.resize((display_width_udd, display_height_proc_udd), resample_filter_nearest_udd)
                        
                        pixmap = pil_to_pixmap(processed_resized_udd)
                        self.app.processed_image_label.setPixmap(pixmap)
                    else:
                        self.app.processed_image_label.setText("Invalid Processed Format")
                except Exception as img_err_proc_udd:
                    log_debug(f"Error processing processed image for debug display: {img_err_proc_udd}")
                    self.app.processed_image_label.setText("Error Processed")

            # Update OCR Results Text (QTextEdit)
            debug_info_text = (f"Timestamp: {time.strftime('%H:%M:%S')}<br>"
                               f"OCR Model: {self.app.get_ocr_model_setting()}<br>"
                               f"Target Lang (API): {self.app.target_lang}<br>"
                               f"{'-'*20}<br>"
                               f"{ocr_text_content_udd.replace('\n', '<br>')}<br>")
            
            self.app.ocr_results_text.setHtml(debug_info_text)
            # Scroll to top
            cursor = self.app.ocr_results_text.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self.app.ocr_results_text.setTextCursor(cursor)

        except Exception as e_udd_gen:
            log_debug(f"Unexpected error updating debug display: {type(e_udd_gen).__name__} - {str(e_udd_gen)}")
