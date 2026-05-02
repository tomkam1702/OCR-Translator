# unified_translation_cache.py
import threading
import time
import hashlib
from logger import log_debug

class UnifiedTranslationCache:
    """
    Unified translation cache for all translation providers.
    Replaces multiple overlapping LRU caches with a single, efficient cache system.
    Thread-safe, configurable, and integrates with existing file caches.
    """
    
    def __init__(self, max_size=1000):
        """
        Initialize the unified translation cache.
        
        Args:
            max_size: Maximum number of entries in the LRU cache
        """
        self.max_size = max_size
        self.lock = threading.RLock()
        
        # Unified cache storage
        # Key format: (text_hash, source_lang, target_lang, provider, params_hash)
        self._cache = {}
        self._access_times = {}  # For LRU eviction
        
        log_debug(f"Initialized unified translation cache with max_size={max_size}")
    
    def _generate_cache_key(self, text, source_lang, target_lang, provider, **kwargs):
        """Generate a unique cache key for the translation request."""
        # Create deterministic hash of text to handle large inputs efficiently
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        
        # Include provider-specific parameters in the key
        params_str = ""
        if provider == "deepl_api" and "model_type" in kwargs:
            params_str = f"_model{kwargs['model_type']}"
        
        params_hash = hashlib.md5(params_str.encode('utf-8')).hexdigest()[:8] if params_str else ""
        
        return (text_hash, source_lang.lower(), target_lang.lower(), provider.lower(), params_hash)
    
    def get(self, text, source_lang, target_lang, provider, **kwargs):
        """
        Get translation from cache. Returns None if not found.
        
        Args:
            text: Source text to translate
            source_lang: Source language code
            target_lang: Target language code  
            provider: Translation provider ('deepl_api', 'gemini_api')
            **kwargs: Provider-specific parameters (e.g., model_type for DeepL)
            
        Returns:
            Cached translation if found, None otherwise
        """
        cache_key = self._generate_cache_key(text, source_lang, target_lang, provider, **kwargs)
        
        with self.lock:
            if cache_key in self._cache:
                # Update access time for LRU
                self._access_times[cache_key] = time.time()
                translation = self._cache[cache_key]
                
                # Enhanced debug logging for DeepL model types
                if provider.lower() == "deepl_api" and "model_type" in kwargs:
                    log_debug(f"Unified cache HIT: {provider} {source_lang}->{target_lang} (model_type={kwargs['model_type']})")
                else:
                    log_debug(f"Unified cache HIT: {provider} {source_lang}->{target_lang}")
                return translation
            
            # Enhanced debug logging for DeepL model types
            if provider.lower() == "deepl_api" and "model_type" in kwargs:
                log_debug(f"Unified cache MISS: {provider} {source_lang}->{target_lang} (model_type={kwargs['model_type']})")
            else:
                log_debug(f"Unified cache MISS: {provider} {source_lang}->{target_lang}")
            return None
    
    def store(self, text, source_lang, target_lang, provider, translation, **kwargs):
        """
        Store translation in cache.
        
        Args:
            text: Source text that was translated
            source_lang: Source language code
            target_lang: Target language code
            provider: Translation provider ('deepl_api', 'gemini_api')
            translation: The translated text
            **kwargs: Provider-specific parameters (e.g., model_type for DeepL)
        """
        cache_key = self._generate_cache_key(text, source_lang, target_lang, provider, **kwargs)
        
        with self.lock:
            # Evict old entries if cache is full
            if len(self._cache) >= self.max_size:
                self._evict_lru_entries()
            
            # Store the translation
            self._cache[cache_key] = translation
            self._access_times[cache_key] = time.time()
            
            # Enhanced debug logging for DeepL model types
            if provider.lower() == "deepl_api" and "model_type" in kwargs:
                log_debug(f"Unified cache STORE: {provider} {source_lang}->{target_lang} (model_type={kwargs['model_type']})")
            else:
                log_debug(f"Unified cache STORE: {provider} {source_lang}->{target_lang}")
    
    def _evict_lru_entries(self):
        """Evict least recently used entries (10% of cache size)."""
        evict_count = max(1, self.max_size // 10)
        
        # Sort by access time and remove oldest
        sorted_items = sorted(self._access_times.items(), key=lambda x: x[1])
        for cache_key, _ in sorted_items[:evict_count]:
            self._cache.pop(cache_key, None)
            self._access_times.pop(cache_key, None)
        
        log_debug(f"Evicted {evict_count} LRU cache entries")
    
    def clear_all(self):
        """Clear all cached translations."""
        with self.lock:
            entries_cleared = len(self._cache)
            self._cache.clear()
            self._access_times.clear()
            log_debug(f"Cleared unified translation cache ({entries_cleared} entries)")
    
    def clear_provider(self, provider):
        """Clear cache entries for a specific provider."""
        with self.lock:
            provider_lower = provider.lower()
            keys_to_remove = [k for k in self._cache.keys() if k[3] == provider_lower]
            
            for key in keys_to_remove:
                self._cache.pop(key, None)
                self._access_times.pop(key, None)
            
            log_debug(f"Cleared {len(keys_to_remove)} cache entries for provider: {provider}")
    
    def get_stats(self):
        """Get cache statistics."""
        with self.lock:
            provider_counts = {}
            for key in self._cache.keys():
                provider = key[3]  # provider is at index 3
                provider_counts[provider] = provider_counts.get(provider, 0) + 1
            
            return {
                "total_entries": len(self._cache),
                "max_size": self.max_size,
                "utilization": f"{len(self._cache) / self.max_size * 100:.1f}%",
                "provider_breakdown": provider_counts
            }
