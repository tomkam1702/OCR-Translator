# handlers/statistics_handler.py
import os
import re
import time
from datetime import datetime
from logger import log_debug

class StatisticsHandler:
    """Handles parsing API usage logs and calculating statistics for cost monitoring."""
    
    def __init__(self, app):
        self.app = app
        
        import nuitka_compat
        base_dir = nuitka_compat.get_base_dir()
        
        self.gemini_ocr_log_file = os.path.join(base_dir, "Gemini_OCR_Short_Log.txt")
        self.gemini_translation_log_file = os.path.join(base_dir, "Gemini_Translation_Short_Log.txt")
        
        log_debug("Statistics handler initialized with provider-specific log file paths.")
        
        self._cache_timestamp = 0
        self._cached_stats = None
    
    def parse_log_file(self, file_path):
        """Parse a short log file and extract data only from completed sessions."""
        if not os.path.exists(file_path):
            return []
        
        sessions = []
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            
            # Find all session start markers
            starts = list(re.finditer(r'SESSION (\d+) STARTED (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)', content))
            
            for i, start_match in enumerate(starts):
                session_id = start_match.group(1)
                start_time_str = start_match.group(2)
                start_pos = start_match.end()
                
                # Find matching session end marker for THIS specific session ID
                # Search only from the end of this start marker to the beginning of the NEXT start marker (or EOF)
                next_start_pos = starts[i+1].start() if i + 1 < len(starts) else len(content)
                block = content[start_pos:next_start_pos]
                
                # Check for ENDED marker with the SAME session ID
                end_match = re.search(f'SESSION {session_id} ENDED (\\d{{4}}-\\d{{2}}-\\d{{2}} \\d{{2}}:\\d{{2}}:\\d{{2}}\\.\\d+)', block)
                
                if end_match:
                    end_time_str = end_match.group(1)
                    session_data = self._parse_session_block(block, start_time_str, end_time_str)
                    if session_data:
                        sessions.append(session_data)
                    
        except Exception as e:
            log_debug(f"Error parsing log file {file_path}: {e}")
        
        return sessions
    
    def _parse_session_block(self, block, session_start, session_end):
        """Parse a single session block and extract calls data."""
        try:
            try:
                start_time = datetime.strptime(session_start, "%Y-%m-%d %H:%M:%S.%f")
                end_time = datetime.strptime(session_end, "%Y-%m-%d %H:%M:%S.%f")
                duration_seconds = (end_time - start_time).total_seconds()
            except ValueError:
                duration_seconds = 0
            
            calls = []
            
            # Use strict call markers but allow them to be at the end of the block
            ocr_calls = re.finditer(r'========= OCR CALL ===========.*?(?========== OCR CALL ===========|===== TRANSLATION CALL =======|SESSION \d+ ENDED|$)', block, re.DOTALL)
            for call_match in ocr_calls:
                call_text = call_match.group(0)
                call_data = self._parse_call_data(call_text)
                if call_data:
                    call_data['type'] = 'ocr'
                    calls.append(call_data)
            
            trans_calls = re.finditer(r'===== TRANSLATION CALL =======.*?(?========== OCR CALL ===========|===== TRANSLATION CALL =======|SESSION \d+ ENDED|$)', block, re.DOTALL)
            for call_match in trans_calls:
                call_text = call_match.group(0)
                call_data = self._parse_call_data(call_text)
                if call_data:
                    call_data['type'] = 'translation'
                    # Accurate word counting from Result block if it exists
                    result_match = re.search(r'Result:\s*-+\s*(.*?)\s*-+', call_text, re.DOTALL)
                    if result_match:
                        result_text = result_match.group(1)
                        call_data['word_count'] = self._count_words_in_translation(result_text)
                    else:
                        call_data['word_count'] = 0
                    calls.append(call_data)
            
            return {
                'start_time': session_start,
                'end_time': session_end,
                'duration_seconds': duration_seconds,
                'calls': calls
            }
            
        except Exception as e:
            log_debug(f"Error parsing session block: {e}")
            return None
    
    def _parse_call_data(self, call_text):
        """Parse individual call data from call block."""
        try:
            duration_match = re.search(r'Duration: ([\d\.]+)s', call_text)
            duration = float(duration_match.group(1)) if duration_match else 0.0
            
            cost_match = re.search(r'Tokens:.*?Cost: \$([0-9\.]+)', call_text)
            cost = float(cost_match.group(1)) if cost_match else 0.0
            
            return {
                'duration': duration,
                'cost': cost
            }
        except Exception as e:
            log_debug(f"Error parsing call data: {e}")
            return None
    
    def _count_words_in_translation(self, result_text):
        """Count words in translation result text."""
        try:
            lines = result_text.strip().split('\n')
            
            target_text = ""
            for line in lines:
                if ':' in line and len(line.split(':', 1)) > 1:
                    potential_target = line.split(':', 1)[1].strip()
                    if potential_target and potential_target != '<EMPTY>':
                        target_text = potential_target
                        break
            
            if not target_text:
                return 0
            
            words = target_text.split()
            return len(words)
            
        except Exception as e:
            log_debug(f"Error counting words: {e}")
            return 0
    
    def get_statistics(self):
        """Get comprehensive API usage statistics, separated by provider."""
        if self._cached_stats and (time.time() - self._cache_timestamp) < 5.0:
            return self._cached_stats
        
        try:
            gemini_ocr_sessions = self.parse_log_file(self.gemini_ocr_log_file)
            gemini_translation_sessions = self.parse_log_file(self.gemini_translation_log_file)
            
            gemini_ocr_stats = self._calculate_ocr_statistics(gemini_ocr_sessions)
            gemini_translation_stats = self._calculate_translation_statistics(gemini_translation_sessions)
            
            gemini_combined_stats = self._calculate_combined_statistics(gemini_ocr_stats, gemini_translation_stats)
            
            stats = {
                'gemini_ocr': gemini_ocr_stats,
                'gemini_translation': gemini_translation_stats,
                'gemini_combined': gemini_combined_stats,
            }
            
            self._cached_stats = stats
            self._cache_timestamp = time.time()
            
            return stats
            
        except Exception as e:
            log_debug(f"Error calculating statistics: {e}")
            return self._get_empty_statistics()
    
    def _calculate_ocr_statistics(self, sessions):
        """Calculate OCR-specific statistics."""
        total_cost = 0.0
        total_calls = 0
        total_duration = 0.0
        call_durations = []
        
        for session in sessions:
            for call in session['calls']:
                if call.get('type') == 'ocr':
                    total_cost += call.get('cost', 0.0)
                    total_calls += 1
                    duration = call.get('duration', 0.0)
                    call_durations.append(duration)
            total_duration += session.get('duration_seconds', 0.0)
        
        median_duration = 0.0
        if call_durations:
            call_durations.sort()
            n = len(call_durations)
            if n % 2 == 0:
                median_duration = (call_durations[n//2 - 1] + call_durations[n//2]) / 2.0
            else:
                median_duration = call_durations[n//2]
        
        avg_cost_per_call = total_cost / total_calls if total_calls > 0 else 0.0
        avg_cost_per_minute = (total_cost / (total_duration / 60.0)) if total_duration > 0 else 0.0
        avg_cost_per_minute_rounded = round(avg_cost_per_minute, 8)
        avg_cost_per_hour = avg_cost_per_minute_rounded * 60.0
        
        return {
            'total_cost': total_cost,
            'total_calls': total_calls,
            'median_duration': median_duration,
            'avg_cost_per_call': avg_cost_per_call,
            'avg_cost_per_minute': avg_cost_per_minute,
            'avg_cost_per_hour': avg_cost_per_hour,
            'total_duration_seconds': total_duration
        }
    
    def _calculate_translation_statistics(self, sessions):
        """Calculate translation-specific statistics."""
        total_cost = 0.0
        total_calls = 0
        total_words = 0
        total_duration = 0.0
        call_durations = []
        
        for session in sessions:
            for call in session['calls']:
                if call.get('type') == 'translation':
                    total_cost += call.get('cost', 0.0)
                    total_calls += 1
                    total_words += call.get('word_count', 0)
                    duration = call.get('duration', 0.0)
                    call_durations.append(duration)
            total_duration += session.get('duration_seconds', 0.0)
        
        median_duration = 0.0
        if call_durations:
            call_durations.sort()
            n = len(call_durations)
            if n % 2 == 0:
                median_duration = (call_durations[n//2 - 1] + call_durations[n//2]) / 2.0
            else:
                median_duration = call_durations[n//2]
        
        avg_cost_per_word = total_cost / total_words if total_words > 0 else 0.0
        avg_cost_per_call = total_cost / total_calls if total_calls > 0 else 0.0
        avg_cost_per_minute = (total_cost / (total_duration / 60.0)) if total_duration > 0 else 0.0
        avg_cost_per_minute_rounded = round(avg_cost_per_minute, 8)
        avg_cost_per_hour = avg_cost_per_minute_rounded * 60.0
        words_per_minute = (total_words / (total_duration / 60.0)) if total_duration > 0 else 0.0
        
        return {
            'total_cost': total_cost,
            'total_calls': total_calls,
            'total_words': total_words,
            'median_duration': median_duration,
            'avg_cost_per_word': avg_cost_per_word,
            'avg_cost_per_call': avg_cost_per_call,
            'avg_cost_per_minute': avg_cost_per_minute,
            'avg_cost_per_hour': avg_cost_per_hour,
            'words_per_minute': words_per_minute,
            'total_duration_seconds': total_duration
        }
    
    def _calculate_combined_statistics(self, ocr_stats, translation_stats):
        """Calculate combined OCR + Translation statistics for a SINGLE provider."""
        total_cost = ocr_stats['total_cost'] + translation_stats['total_cost']
        
        combined_cost_per_minute = ocr_stats['avg_cost_per_minute'] + translation_stats['avg_cost_per_minute']
        combined_cost_per_minute_rounded = round(combined_cost_per_minute, 8)
        # combined_cost_per_hour = combined_cost_per_minute_rounded * 60.0
        combined_cost_per_hour = ocr_stats['avg_cost_per_hour'] + translation_stats['avg_cost_per_hour']
        combined_cost_per_hour_rounded = round(combined_cost_per_hour, 8)
        
        return {
            'total_cost': total_cost,
            'combined_cost_per_minute': combined_cost_per_minute_rounded,
            'combined_cost_per_hour': combined_cost_per_hour_rounded
        }
    
    def _get_empty_statistics(self):
        """Return empty statistics structure for the new layout."""
        empty_ocr = {
            'total_cost': 0.0, 'total_calls': 0, 'median_duration': 0.0, 'avg_cost_per_call': 0.0,
            'avg_cost_per_minute': 0.0, 'avg_cost_per_hour': 0.0, 'total_duration_seconds': 0.0
        }
        empty_trans = {
            'total_cost': 0.0, 'total_calls': 0, 'total_words': 0, 'median_duration': 0.0,
            'avg_cost_per_word': 0.0, 'avg_cost_per_call': 0.0, 'avg_cost_per_minute': 0.0, 
            'avg_cost_per_hour': 0.0, 'words_per_minute': 0.0, 'total_duration_seconds': 0.0
        }
        empty_combined = {'total_cost': 0.0, 'combined_cost_per_minute': 0.0, 'combined_cost_per_hour': 0.0}

        return {
            'gemini_ocr': empty_ocr.copy(),
            'gemini_translation': empty_trans.copy(),
            'gemini_combined': empty_combined.copy(),
        }
    
    def _format_currency_for_export(self, amount, use_polish_format=False):
        """Format currency for export files with proper localization."""
        try:
            if use_polish_format:
                amount_str = f"{amount:.8f}".replace('.', ',')
                return f"{amount_str} USD"
            else:
                return f"${amount:.8f}"
        except Exception as e:
            log_debug(f"Error formatting currency for export: {e}")
            return f"${amount:.8f}"
    
    def _format_number_with_separators_for_export(self, number, use_polish_format=False):
        """Format integer numbers with thousand separators for export files."""
        try:
            num = int(number)
            if use_polish_format:
                return f"{num:,}".replace(',', ' ')
            else:
                return f"{num:,}"
        except Exception as e:
            log_debug(f"Error formatting number with separators for export: {e}")
            return str(number)
    
    def export_statistics_csv(self, file_path, ui_lang=None, deepl_usage=None):
        """Export statistics to CSV format with the new structure."""
        try:
            stats = self.get_statistics()
            use_polish_format = ui_lang and hasattr(ui_lang, 'current_lang') and ui_lang.current_lang == 'pol'
            
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                import csv
                writer = csv.writer(f)
                
                # Use externalized labels for CSV headers
                headers = [
                    ui_lang.get_label("csv_header_provider", "Provider") if ui_lang else "Provider",
                    ui_lang.get_label("csv_header_type", "Type") if ui_lang else "Type",
                    ui_lang.get_label("csv_header_metric", "Metric") if ui_lang else "Metric",
                    ui_lang.get_label("csv_header_value", "Value") if ui_lang else "Value"
                ]
                writer.writerow(headers)
                
                self._write_csv_section(writer, "Gemini", "Translation", stats['gemini_translation'], use_polish_format)
                self._write_csv_section(writer, "Gemini", "OCR", stats['gemini_ocr'], use_polish_format)
                self._write_csv_section(writer, "Gemini", "Combined", stats['gemini_combined'], use_polish_format)

                deepl_value = deepl_usage if deepl_usage else "N/A"
                free_limit_label = ui_lang.get_label("csv_metric_free_monthly_limit", "Free Monthly Limit") if ui_lang else "Free Monthly Limit"
                writer.writerow(["DeepL", "Usage", free_limit_label, deepl_value])
            
            log_debug(f"Statistics exported to CSV: {file_path}")
            return True
        except Exception as e:
            log_debug(f"Error exporting statistics to CSV: {e}")
            return False

    def _write_csv_section(self, writer, provider, type, data, use_polish_format):
        """Helper to write a section to the CSV file."""
        for key, value in data.items():
            metric_name = key.replace('_', ' ').title()
            formatted_value = value
            if 'cost' in key:
                formatted_value = self._format_currency_for_export(value, use_polish_format)
            elif 'calls' in key or 'words' in key:
                formatted_value = self._format_number_with_separators_for_export(value, use_polish_format)
            elif 'duration' in key:
                formatted_value = f"{value:.3f}s".replace('.', ',') if use_polish_format else f"{value:.3f}s"
            elif 'per_minute' in key and 'cost' not in key:
                formatted_value = f"{value:.2f}".replace('.', ',') if use_polish_format else f"{value:.2f}"
            
            writer.writerow([provider, type, metric_name, formatted_value])

    def export_statistics_text(self, file_path, ui_lang=None, deepl_usage=None):
        """Export statistics to text summary format with the new structure."""
        try:
            report_content = self._generate_text_report(ui_lang, deepl_usage)
            with open(file_path, 'w', encoding='utf-8-sig') as f:
                f.write(report_content)
            
            log_debug(f"Statistics exported to text: {file_path}")
            return True
        except Exception as e:
            log_debug(f"Error exporting statistics to text: {e}")
            return False

    def _generate_text_report(self, ui_lang=None, deepl_usage=None):
        """Generate the full text report as a string."""
        from io import StringIO
        string_buffer = StringIO()
        
        stats = self.get_statistics()
        use_polish_format = ui_lang and hasattr(ui_lang, 'current_lang') and ui_lang.current_lang == 'pol'
        
        # Use externalized header
        header = ui_lang.get_label("stats_clipboard_header", "Game-Changing Translator - API Usage Statistics") if ui_lang else "Game-Changing Translator - API Usage Statistics"
        string_buffer.write(f"{header}\n")
        string_buffer.write("=" * 50 + "\n\n")

        self._write_text_section(string_buffer, "Gemini", stats, ui_lang, use_polish_format)

        # Use externalized DeepL section
        deepl_header = ui_lang.get_label("stats_text_deepl_header", "📈 DeepL Usage Monitor") if ui_lang else "📈 DeepL Usage Monitor"
        string_buffer.write(f"{deepl_header}\n")
        string_buffer.write("-" * 25 + "\n")
        deepl_value = deepl_usage if deepl_usage else (ui_lang.get_label("stats_not_available", "N/A") if ui_lang else "N/A")
        free_limit_label = ui_lang.get_label("stats_deepl_free_limit", "Free Monthly Limit:") if ui_lang else "Free Monthly Limit:"
        string_buffer.write(f"{free_limit_label} {deepl_value}\n\n")

        # Use externalized report generation text
        report_gen_label = ui_lang.get_label("stats_report_generated", "Report generated:") if ui_lang else "Report generated:"
        string_buffer.write(f"{report_gen_label} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        content = string_buffer.getvalue()
        string_buffer.close()
        return content

    def _write_text_section(self, f, provider, stats, ui_lang, use_polish_format):
        """Helper to write a provider's section to the text file buffer."""
        ocr_stats = stats[f'{provider.lower()}_ocr']
        trans_stats = stats[f'{provider.lower()}_translation']
        combined_stats = stats[f'{provider.lower()}_combined']
        
        provider_lower = provider.lower()
        duration_suffix = " s" if use_polish_format else "s"
        
        # Translation Section FIRST (Matches GUI)
        trans_header = ui_lang.get_label(f"stats_text_trans_header_{provider_lower}", f"🔄 {provider} Translation Statistics") if ui_lang else f"🔄 {provider} Translation Statistics"
        f.write(f"{trans_header}\n")
        f.write("-" * len(trans_header) + "\n")
        
        total_trans_calls_label = ui_lang.get_label("stats_text_total_trans_calls", "Total Translation Calls") if ui_lang else "Total Translation Calls"
        f.write(f"{total_trans_calls_label}: {self._format_number_with_separators_for_export(trans_stats['total_calls'], use_polish_format)}\n")
        
        total_words_label = ui_lang.get_label("stats_text_total_words", "Total Words Translated") if ui_lang else "Total Words Translated"
        f.write(f"{total_words_label}: {self._format_number_with_separators_for_export(trans_stats['total_words'], use_polish_format)}\n")
        
        median_duration_label = ui_lang.get_label("stats_text_median_duration", "Median Duration") if ui_lang else "Median Duration"
        f.write(f"{median_duration_label}: {f'{trans_stats['median_duration']:.3f}{duration_suffix}'.replace('.', ',') if use_polish_format else f'{trans_stats['median_duration']:.3f}{duration_suffix}'}\n")
        
        words_per_minute_label = ui_lang.get_label("stats_text_words_per_minute", "Average Words per Minute") if ui_lang else "Average Words per Minute"
        f.write(f"{words_per_minute_label}: {int(round(trans_stats['words_per_minute']))}\n")
        
        avg_cost_per_word_label = ui_lang.get_label("stats_text_avg_cost_per_word", "Average Cost per Word") if ui_lang else "Average Cost per Word"
        f.write(f"{avg_cost_per_word_label}: {self._format_currency_for_export(trans_stats['avg_cost_per_word'], use_polish_format)}\n")
        
        avg_cost_per_call_label = ui_lang.get_label("stats_text_avg_cost_per_call", "Average Cost per Call") if ui_lang else "Average Cost per Call"
        f.write(f"{avg_cost_per_call_label}: {self._format_currency_for_export(trans_stats['avg_cost_per_call'], use_polish_format)}\n")
        
        avg_cost_per_minute_label = ui_lang.get_label("stats_text_avg_cost_per_minute", "Average Cost per Minute") if ui_lang else "Average Cost per Minute"
        f.write(f"{avg_cost_per_minute_label}: {self._format_currency_for_export(trans_stats['avg_cost_per_minute'], use_polish_format)}\n")
        
        avg_cost_per_hour_label = ui_lang.get_label("stats_text_avg_cost_per_hour", "Average Cost per Hour") if ui_lang else "Average Cost per Hour"
        f.write(f"{avg_cost_per_hour_label}: {self._format_currency_for_export(trans_stats['avg_cost_per_hour'], use_polish_format)}\n")
        
        total_trans_cost_label = ui_lang.get_label("stats_text_total_trans_cost", "Total Translation Cost") if ui_lang else "Total Translation Cost"
        f.write(f"{total_trans_cost_label}: {self._format_currency_for_export(trans_stats['total_cost'], use_polish_format)}\n\n")

        # OCR Section SECOND
        ocr_header = ui_lang.get_label(f"stats_text_ocr_header_{provider_lower}", f"📊 {provider} OCR Statistics") if ui_lang else f"📊 {provider} OCR Statistics"
        f.write(f"{ocr_header}\n")
        f.write("-" * len(ocr_header) + "\n")
        
        total_ocr_calls_label = ui_lang.get_label("stats_text_total_ocr_calls", "Total OCR Calls") if ui_lang else "Total OCR Calls"
        f.write(f"{total_ocr_calls_label}: {self._format_number_with_separators_for_export(ocr_stats['total_calls'], use_polish_format)}\n")
        
        f.write(f"{median_duration_label}: {f'{ocr_stats['median_duration']:.3f}{duration_suffix}'.replace('.', ',') if use_polish_format else f'{ocr_stats['median_duration']:.3f}{duration_suffix}'}\n")
        
        f.write(f"{avg_cost_per_call_label}: {self._format_currency_for_export(ocr_stats['avg_cost_per_call'], use_polish_format)}\n")
        f.write(f"{avg_cost_per_minute_label}: {self._format_currency_for_export(ocr_stats['avg_cost_per_minute'], use_polish_format)}\n")
        f.write(f"{avg_cost_per_hour_label}: {self._format_currency_for_export(ocr_stats['avg_cost_per_hour'], use_polish_format)}\n")
        
        total_ocr_cost_label = ui_lang.get_label("stats_text_total_ocr_cost", "Total OCR Cost") if ui_lang else "Total OCR Cost"
        f.write(f"{total_ocr_cost_label}: {self._format_currency_for_export(ocr_stats['total_cost'], use_polish_format)}\n\n")

        # Combined Section
        combined_header = ui_lang.get_label(f"stats_text_combined_header_{provider_lower}", f"💰 Combined {provider} Statistics") if ui_lang else f"💰 Combined {provider} Statistics"
        f.write(f"{combined_header}\n")
        f.write("-" * len(combined_header) + "\n")
        
        combined_cost_per_minute_label = ui_lang.get_label("stats_text_combined_cost_per_minute", "Combined Cost per Minute") if ui_lang else "Combined Cost per Minute"
        f.write(f"{combined_cost_per_minute_label}: {self._format_currency_for_export(combined_stats['combined_cost_per_minute'], use_polish_format)}\n")
        
        combined_cost_per_hour_label = ui_lang.get_label("stats_text_combined_cost_per_hour", "Combined Cost per Hour") if ui_lang else "Combined Cost per Hour"
        f.write(f"{combined_cost_per_hour_label}: {self._format_currency_for_export(combined_stats['combined_cost_per_hour'], use_polish_format)}\n")
        
        total_api_cost_label = ui_lang.get_label("stats_text_total_api_cost", "Total API Cost") if ui_lang else "Total API Cost"
        f.write(f"{total_api_cost_label}: {self._format_currency_for_export(combined_stats['total_cost'], use_polish_format)}\n\n")