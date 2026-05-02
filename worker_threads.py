# worker_threads.py (Stage III — PySide6 Signals Edition)

import time
import os
import queue
import numpy as np
import cv2
import pyautogui
import hashlib
import random
import re
import traceback 
from datetime import datetime

from logger import log_debug

from translation_utils import post_process_translation_text
from PIL import Image # For hashing in capture_thread

# Fast screen capture using mss (native OS APIs, 3-10x faster than pyautogui)
try:
    import mss
    _mss_available = True
    log_debug("mss library available - using fast native screen capture")
except ImportError:
    _mss_available = False
    log_debug("mss library not available - falling back to pyautogui for screen capture")



def run_capture_thread(app):
    log_debug("WT: Capture thread started.")
    last_cap_time = 0.0
    last_cap_hash = None
    min_interval = 0.05  # 50ms minimum safety floor - user can control via Settings tab
    similar_frames = 0
    current_scan_interval_sec = min_interval # Initialize
    
    # Initialize mss inside the capture thread (mss uses thread-local handles)
    sct = None
    if _mss_available:
        try:
            sct = mss.mss()
            log_debug("WT: Initialized mss screen capture instance in capture thread")
        except Exception as mss_init_err:
            log_debug(f"WT: Failed to initialize mss: {mss_init_err}, falling back to pyautogui")
            sct = None

    while app.is_running:
        # Screenshot freeze: pause capture to prevent new OCR tasks during photo mode
        if getattr(app, 'is_photo_mode_active', False):
            time.sleep(0.1)
            continue
        now = time.monotonic()
        try:
            # Update adaptive scan interval based on OCR load
            app.update_adaptive_scan_interval()
            
            # Use dynamic interval instead of static setting
            scan_interval_ms = app.current_scan_interval  # ← Use adaptive value
            base_scan_interval = max(min_interval, scan_interval_ms / 1000.0)
            
            # DEBUG: Log when using adaptive interval (every 20 seconds to avoid spam)
            if not hasattr(app, '_last_adaptive_debug') or now - app._last_adaptive_debug > 20.0:
                app._last_adaptive_debug = now
                log_debug(f"ADAPTIVE: Capture thread using scan interval: {scan_interval_ms}ms (base: {app.scan_interval}ms)")
            
            ocr_model = app.get_ocr_model_setting()
            # Use a simpler, more adaptive logic for all API-based OCR models
            if app.is_api_based_ocr_model(ocr_model):
                # For API-based OCR: Simple, strict interval - no complex adaptive logic
                if now - last_cap_time < base_scan_interval:
                    sleep_duration = base_scan_interval - (now - last_cap_time)
                    slept_time = 0
                    while slept_time < sleep_duration and app.is_running:
                        chunk = min(0.05, sleep_duration - slept_time)
                        time.sleep(chunk)
                        slept_time += chunk
                    if not app.is_running: break
                    continue
                current_scan_interval_sec = base_scan_interval
            
            overlay = app.source_overlay
            if not overlay:
                if app.is_running: time.sleep(max(current_scan_interval_sec, 0.5))
                continue
            
            # Prefer capture geometry directly from overlay (includes DPI scaling)
            try:
                area = overlay.get_capture_geometry()
            except Exception:
                area = getattr(app, 'source_area', None)
            
            if not area:
                if app.is_running: time.sleep(max(current_scan_interval_sec, 0.5))
                continue
            if not area:
                if app.is_running: time.sleep(max(current_scan_interval_sec, 0.2))
                continue

            x1, y1, x2, y2 = map(int, area); width, height = x2-x1, y2-y1
            if width <=0 or height <=0: continue

            # Scan Wider (capture_padding) disabled in open-source edition
            # Capture exactly the source overlay area, no expansion

            capture_moment = time.monotonic()
            # Use mss for fast native screen capture (3-10x faster than pyautogui)
            if sct is not None:
                monitor = {"top": y1, "left": x1, "width": width, "height": height}
                mss_img = sct.grab(monitor)
                screenshot = Image.frombytes("RGB", mss_img.size, mss_img.bgra, "raw", "BGRX")
            else:
                screenshot = pyautogui.screenshot(region=(x1,y1,width,height))
            last_cap_time = capture_moment

            img_small = screenshot.resize((max(1, width//4), max(1, height//4)), Image.Resampling.NEAREST if hasattr(Image, "Resampling") else Image.NEAREST)
            img_hash = hashlib.md5(img_small.tobytes()).hexdigest()

            if img_hash == last_cap_hash:
                continue
            last_cap_hash = img_hash

            try:
                if not app.ocr_queue.full():
                    app.ocr_queue.put_nowait(screenshot)
            except queue.Full:
                pass # Skip frame if queue is full
            except Exception as q_err_wt_put:
                log_debug(f"WT: Capture: Error putting to OCR queue - {type(q_err_wt_put).__name__}: {q_err_wt_put}")

        except Exception as loop_err_wt_capture:
            log_debug(f"WT: Capture thread error: {type(loop_err_wt_capture).__name__} - {loop_err_wt_capture}\n{traceback.format_exc()}")
            if not app.is_running: break
            sleep_after_error = current_scan_interval_sec if 'current_scan_interval_sec' in locals() else 0.5
            time.sleep(max(sleep_after_error, 0.5))
    log_debug("WT: Capture thread finished.")


def run_ocr_thread(app):
    log_debug("WT: OCR thread started.")
    

    
    last_lang_check = time.monotonic()
    last_ocr_proc_time = 0
    min_ocr_interval = 0.1
    similar_texts_count = 0
    prev_ocr_text = ""

    while app.is_running:
        now = time.monotonic()
        try:
            if now - last_lang_check > 5.0:
                last_lang_check = now
            
            ocr_model = app.get_ocr_model_setting()
            

            
            try:
                screenshot_pil = app.ocr_queue.get(timeout=0.5)
            except queue.Empty:
                time.sleep(0.05)
                continue

            ocr_proc_start_time = time.monotonic()
            last_ocr_proc_time = ocr_proc_start_time
            app.last_screenshot = screenshot_pil

            # ==================== OCR MODEL ROUTING ====================
            if app.is_api_based_ocr_model(ocr_model):
                run_api_ocr(app, screenshot_pil)
                continue # Skip to the next loop iteration
            
            time.sleep(0.1)
        except Exception as e_ocr_loop_wt:
            log_debug(f"WT: OCR thread error: {type(e_ocr_loop_wt).__name__} - {e_ocr_loop_wt}\n{traceback.format_exc()}")
            app.text_stability_counter=0
            app.previous_text=""
            time.sleep(0.2)
    log_debug("WT: OCR thread finished.")

def run_translation_thread(app):
    """Simplified translation thread."""
    log_debug("WT: Translation thread started (simplified for async processing).")
    thread_local_last_translation_display_time = time.monotonic() 

    while app.is_running:
        now = time.monotonic()
        try:
            ocr_model = app.get_ocr_model_setting()
            
            if not app.is_api_based_ocr_model(ocr_model):
                inactive_duration = now - thread_local_last_translation_display_time
                if app.clear_translation_timeout > 0 and inactive_duration > app.clear_translation_timeout:
                    if not app.previous_text or app.previous_text == "":
                        app.update_translation_text("")
                        log_debug(f"WT: Cleared translation after {inactive_duration:.1f}s of inactivity with no source text (timeout: {app.clear_translation_timeout}s)")
                    else:
                        log_debug(f"WT: Not clearing translation despite {inactive_duration:.1f}s inactivity because source area still has text")
                    thread_local_last_translation_display_time = now

            if app.last_successful_translation_time > thread_local_last_translation_display_time:
                thread_local_last_translation_display_time = app.last_successful_translation_time

            try:
                text_to_translate = app.translation_queue.get(timeout=0.1)
                if text_to_translate and not app.is_placeholder_text(text_to_translate):
                    log_debug(f"WT: Processing legacy queue item: '{text_to_translate}'")
                    start_async_translation(app, text_to_translate, 0)
            except queue.Empty:
                pass
            
            time.sleep(0.1)

        except Exception as e_trans_loop_wt:
            log_debug(f"WT: Translation thread error: {type(e_trans_loop_wt).__name__} - {e_trans_loop_wt}\n{traceback.format_exc()}")
            if not app.is_running: break
            time.sleep(0.2)
    log_debug("WT: Translation thread finished.")


# ==================== GENERIC ASYNC API OCR WORKFLOW ====================

def run_api_ocr(app, screenshot_pil):
    """Start API-based OCR processing for a screenshot using the currently selected provider."""
    try:
        provider_name = app.get_ocr_model_setting()
        
        if not hasattr(app, 'batch_sequence_counter'):
            app.batch_sequence_counter = 0
        
        is_auto_detect = False  # Find Subtitles disabled in open-source edition
        
        webp_image_data = app.convert_to_webp_for_api(screenshot_pil)
        if not webp_image_data:
            log_debug(f"Failed to convert image to WebP for {provider_name} OCR")
            return
        
        active_translation_model = app.translation_model
        if app.is_gemini_model(active_translation_model):
            source_lang = getattr(app, 'gemini_source_lang', 'en')
        else:
            source_lang = app.source_lang

        app.batch_sequence_counter += 1
        sequence_number = app.batch_sequence_counter
        
        if len(app.active_ocr_calls) >= app.max_concurrent_ocr_calls:
            log_debug(f"Max concurrent OCR calls ({app.max_concurrent_ocr_calls}) reached, skipping {provider_name} batch {sequence_number}")
            return
        
        app.active_ocr_calls.add(sequence_number)
        app.ocr_thread_pool.submit(
            process_api_ocr_async,
            app, webp_image_data, source_lang, sequence_number, provider_name, is_auto_detect
        )
        log_debug(f"Started {provider_name} OCR batch {sequence_number} (Auto-Detect: {is_auto_detect}, active calls: {len(app.active_ocr_calls)})")
        
    except Exception as e:
        log_debug(f"Error starting API OCR batch: {type(e).__name__} - {e}")

def process_api_ocr_async(app, webp_image_data, source_lang, sequence_number, provider_name, is_auto_detect=False):
    """Process an API OCR call asynchronously. This is the generic worker function."""
    try:
        log_debug(f"Processing {provider_name} OCR batch {sequence_number} (Auto-Detect: {is_auto_detect})")
        
        ocr_result = app.translation_handler.perform_ocr(webp_image_data, source_lang, is_auto_detect=is_auto_detect)
        
        log_debug(f"{provider_name} OCR batch {sequence_number} completed: '{ocr_result}', scheduling response")
        app.signals.ocr_response.emit(ocr_result, sequence_number, source_lang, provider_name, is_auto_detect)
        
    except Exception as e:
        log_debug(f"Error in async {provider_name} OCR batch {sequence_number}: {type(e).__name__} - {e}")
        error_msg = f"<e>: OCR batch {sequence_number} error: {str(e)}"
        app.signals.ocr_response.emit(error_msg, sequence_number, source_lang, provider_name, False)
    
    finally:
        app.active_ocr_calls.discard(sequence_number)
        log_debug(f"{provider_name} OCR batch {sequence_number} finished (active calls: {len(app.active_ocr_calls)})")

def process_api_ocr_response(app, ocr_result, sequence_number, source_lang, provider_name, is_auto_detect=False):
    """Process any API OCR response with chronological order enforcement. This is the generic callback."""
    if not app.is_running:
        log_debug(f"API OCR {sequence_number}: Program stopped, discarding response to prevent stale processing.")
        return
        
    try:
        log_debug(f"Processing {provider_name} OCR response for batch {sequence_number} (Auto-Detect: {is_auto_detect}): '{ocr_result}'")
        
        if not hasattr(app, 'last_displayed_batch_sequence'):
            app.last_displayed_batch_sequence = 0
        
        if sequence_number <= app.last_displayed_batch_sequence:
            log_debug(f"{provider_name} OCR batch {sequence_number}: Sequence too old, discarding")
            return
            
        log_debug(f"{provider_name} OCR batch {sequence_number}: Processing newer sequence")
        
        if isinstance(ocr_result, str) and ocr_result.startswith("<e>:"):
            log_debug(f"OCR error in {provider_name} batch {sequence_number}: {ocr_result}")
            app.last_displayed_batch_sequence = sequence_number
            return
        # Auto-detect / Find Subtitles disabled in open-source edition
        pass

        if ocr_result == "<EMPTY>":
            app.handle_empty_ocr_result()
            app.last_displayed_batch_sequence = sequence_number
            return
        
        if hasattr(app, 'last_processed_subtitle') and ocr_result == app.last_processed_subtitle:
            app.reset_clear_timeout()
            log_debug(f"Keeping existing translation for successive identical {provider_name} OCR: '{ocr_result}'")
            app.last_displayed_batch_sequence = sequence_number
            return
        
        app.last_processed_subtitle = ocr_result
        app.reset_clear_timeout()
        start_async_translation(app, ocr_result, sequence_number)
        app.last_displayed_batch_sequence = sequence_number
        
    except Exception as e:
        log_debug(f"Error processing {provider_name} OCR response for batch {sequence_number}: {type(e).__name__} - {e}")


# ==================== ASYNC TRANSLATION PROCESSING (Phase 2) ====================

def start_async_translation(app, text_to_translate, ocr_sequence_number):
    """Start async translation processing to eliminate queue bottlenecks."""
    try:
        app.initialize_async_translation_infrastructure()
        
        app.translation_sequence_counter += 1
        translation_sequence = app.translation_sequence_counter
        
        if len(app.active_translation_calls) >= app.max_concurrent_translation_calls:
            log_debug(f"Max concurrent translation calls ({app.max_concurrent_translation_calls}) reached, skipping translation {translation_sequence}")
            return
        
        app.active_translation_calls.add(translation_sequence)
        
        future = app.translation_thread_pool.submit(
            process_translation_async,
            app, text_to_translate, translation_sequence, ocr_sequence_number
        )
        
        log_debug(f"Started async translation {translation_sequence} for OCR batch {ocr_sequence_number} (active calls: {len(app.active_translation_calls)}): '{text_to_translate}'")
        
    except Exception as e:
        log_debug(f"Error starting async translation: {type(e).__name__} - {e}")


def process_translation_async(app, text_to_translate, translation_sequence, ocr_sequence_number):
    """Process translation API call asynchronously with timeout and staleness handling."""
    start_time = time.monotonic()
    
    try:
        log_debug(f"Processing async translation {translation_sequence}")
        
        translation_result = app.translation_handler.translate_text_with_timeout(text_to_translate, timeout_seconds=10.0, ocr_batch_number=ocr_sequence_number)
        
        elapsed_time = time.monotonic() - start_time
        if elapsed_time > 5.0:
            log_debug(f"Translation {translation_sequence} took {elapsed_time:.1f}s, may be stale but will attempt display")
        
        log_debug(f"Translation {translation_sequence} completed in {elapsed_time:.3f}s: '{translation_result}'")
        
        app.signals.translation_response.emit(
            translation_result if translation_result else "",
            translation_sequence, text_to_translate, ocr_sequence_number
        )
        
    except Exception as e:
        elapsed_time = time.monotonic() - start_time
        log_debug(f"Error in async translation {translation_sequence} after {elapsed_time:.2f}s: {type(e).__name__} - {e}")
        
        error_msg = f"Translation error: {str(e)}"
        app.signals.translation_response.emit(
            error_msg, translation_sequence, text_to_translate, ocr_sequence_number
        )
    
    finally:
        try:
            app.active_translation_calls.discard(translation_sequence)
            log_debug(f"Translation {translation_sequence} finished (active calls: {len(app.active_translation_calls)})")
        except Exception as cleanup_error:
            log_debug(f"Error cleaning up translation {translation_sequence}: {cleanup_error}")


def process_translation_response(app, translation_result, translation_sequence, original_text, ocr_sequence_number):
    """Process translation response with chronological order enforcement - same logic as OCR."""
    if not app.is_running:
        log_debug(f"Translation {translation_sequence}: Program stopped, discarding response to prevent UI overwrite.")
        return

    try:
        log_debug(f"Processing translation response for sequence {translation_sequence}: '{translation_result}'")
        
        if translation_result is None:
            log_debug(f"Translation {translation_sequence}: Timeout occurred, no message displayed (suppressed)")
            return
        
        if not hasattr(app, 'last_displayed_translation_sequence'):
            app.last_displayed_translation_sequence = 0
        
        if translation_sequence <= app.last_displayed_translation_sequence:
            log_debug(f"Translation {translation_sequence}: Sequence too old (last displayed: {app.last_displayed_translation_sequence}), discarding but caching result")
            return
        
        log_debug(f"Translation {translation_sequence}: Processing newer sequence (last displayed: {app.last_displayed_translation_sequence})")
        
        error_prefixes = ("Err:", "DeepL API error:", 
                          "DeepL API key missing:", "DeepL Client init error:", "Translation error:", 
                          "DeepL API client not initialized")
        
        if isinstance(translation_result, str) and any(translation_result.startswith(p) for p in error_prefixes):
            log_debug(f"Translation error in sequence {translation_sequence}: {translation_result}")
            app.update_translation_text(f"Translation Error:\n{translation_result}")
            app.last_displayed_translation_sequence = translation_sequence
            app.last_successful_translation_time = time.monotonic()
            return
        
        if isinstance(translation_result, str) and translation_result.strip():
            final_processed_translation = post_process_translation_text(translation_result)
            app.update_translation_text(final_processed_translation)
            log_debug(f"Translation {translation_sequence} displayed: '{final_processed_translation}' (from OCR batch {ocr_sequence_number})")
            app.last_displayed_translation_sequence = translation_sequence
            app.last_successful_translation_time = time.monotonic()
        else:
            log_debug(f"Translation {translation_sequence}: Empty or invalid result, not displaying")
            
    except Exception as e:
        log_debug(f"Error processing translation response for sequence {translation_sequence}: {type(e).__name__} - {e}")
        try:
            app.update_translation_text(f"Translation Processing Error:\n{type(e).__name__}")
        except:
            pass
