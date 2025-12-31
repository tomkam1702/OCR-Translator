# handlers/gemini_models_manager.py
import csv
import os
from logger import log_debug
from resource_handler import get_resource_path

class GeminiModelsManager:
    """Manages Gemini model information from CSV file."""
    
    def __init__(self):
        self.models = []
        self.translation_models = []
        self.ocr_models = []
        self.model_costs = {}
        self.load_models()
    
    def load_models(self):
        """Load Gemini models from CSV file."""
        try:
            csv_path = get_resource_path("resources/gemini_models.csv")
            
            if not os.path.exists(csv_path):
                log_debug(f"Gemini models CSV file not found: {csv_path}")
                return
            
            self.models = []
            self.translation_models = []
            self.ocr_models = []
            self.model_costs = {}
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                # Skip BOM if present
                content = f.read()
                if content.startswith('\ufeff'):
                    content = content[1:]
                
                reader = csv.DictReader(content.splitlines())
                
                for row in reader:
                    model_name = row.get('Model Name', '').strip()
                    api_name = row.get('API Name', '').strip()
                    input_cost = float(row.get('Input Cost per 1M', '0'))
                    output_cost = float(row.get('Output Cost per 1M', '0'))
                    translation_enabled = row.get('Translation', '').strip().lower() == 'yes'
                    ocr_enabled = row.get('OCR', '').strip().lower() == 'yes'
                    
                    if model_name and api_name:
                        model_info = {
                            'display_name': model_name,
                            'api_name': api_name,
                            'input_cost': input_cost,
                            'output_cost': output_cost,
                            'translation_enabled': translation_enabled,
                            'ocr_enabled': ocr_enabled
                        }
                        
                        self.models.append(model_info)
                        
                        # Store cost information
                        self.model_costs[api_name] = {
                            'input_cost': input_cost,
                            'output_cost': output_cost
                        }
                        
                        # Store media resolution (default to MEDIUM if missing)
                        media_resolution = row.get('Media Resolution', 'MEDIUM').strip().upper()
                        if media_resolution not in ['LOW', 'MEDIUM', 'HIGH', 'ULTRA_HIGH']:
                            media_resolution = 'MEDIUM'
                        model_info['media_resolution'] = media_resolution
                        
                        # Add to appropriate lists
                        if translation_enabled:
                            self.translation_models.append(model_info)
                        
                        if ocr_enabled:
                            self.ocr_models.append(model_info)
            
            log_debug(f"Loaded {len(self.models)} Gemini models from CSV")
            log_debug(f"Translation models: {len(self.translation_models)}")
            log_debug(f"OCR models: {len(self.ocr_models)}")
            
        except Exception as e:
            log_debug(f"Error loading Gemini models from CSV: {e}")
    
    def get_translation_model_names(self):
        """Get list of display names for translation-enabled models."""
        return [model['display_name'] for model in self.translation_models]
    
    def get_ocr_model_names(self):
        """Get list of display names for OCR-enabled models.""" 
        return [model['display_name'] for model in self.ocr_models]
    
    def get_api_name_by_display_name(self, display_name):
        """Get API name for a given display name."""
        for model in self.models:
            if model['display_name'] == display_name:
                return model['api_name']
        return None
    
    def get_display_name_by_api_name(self, api_name):
        """Get display name for a given API name."""
        for model in self.models:
            if model['api_name'] == api_name:
                return model['display_name'] 
        return None
    
    def get_model_costs(self, api_name):
        """Get input and output costs for a model."""
        return self.model_costs.get(api_name, {'input_cost': 0.1, 'output_cost': 0.4})
        
    def get_model_media_resolution(self, display_name):
        """Get configured media resolution for a model by display name."""
        model = self.get_model_info_by_display_name(display_name)
        if model:
            return model.get('media_resolution', 'MEDIUM')
        return 'MEDIUM'
    
    def get_model_info_by_api_name(self, api_name):
        """Get complete model info by API name."""
        for model in self.models:
            if model['api_name'] == api_name:
                return model
        return None
    
    def get_model_info_by_display_name(self, display_name):
        """Get complete model info by display name."""
        for model in self.models:
            if model['display_name'] == display_name:
                return model
        return None
    
    def is_valid_translation_model(self, display_name):
        """Check if display name is a valid translation model."""
        return display_name in self.get_translation_model_names()
    
    def is_valid_ocr_model(self, display_name):
        """Check if display name is a valid OCR model."""
        return display_name in self.get_ocr_model_names()
    
    def reload_models(self):
        """Reload models from CSV file."""
        self.load_models()
