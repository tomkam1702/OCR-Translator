# Right-to-Left (RTL) languages that require special text direction handling
RTL_LANGUAGES = {
    'ar',     # Arabic
    'fa',     # Persian/Farsi
    'he',     # Hebrew
    'ur',     # Urdu
    'ku',     # Kurdish
    'sd',     # Sindhi
    'ps',     # Pashto
    'yi',     # Yiddish
    'ckb',    # Kurdish (Sorani) - DeepL Beta
    'prs'     # Dari - DeepL Beta
}

# DeepL Beta Languages (require enable_beta_languages=True and model_type="quality_optimized")
DEEPL_BETA_LANGUAGES = {
    'ACE', 'AF', 'AN', 'AS', 'AY', 'AZ', 'BA', 'BE', 'BHO', 'BN', 'BR', 'BS', 
    'CA', 'CEB', 'CKB', 'CY', 'EO', 'EU', 'FA', 'GA', 'GL', 'GN', 
    'GOM', 'GU', 'HA', 'HI', 'HR', 'HT', 'HY', 'IG', 'IS', 'JV', 'KA', 'KK', 
    'KMR', 'KY', 'LA', 'LB', 'LMO', 'LN', 'MAI', 'MG', 'MI', 'MK', 'MN', 'MR', 
    'MS', 'MT', 'MY', 'NE', 'OC', 'PAG', 'PAM', 'PRS', 'PS', 'QU', 'SA', 'SCN', 
    'SQ', 'SR', 'SU', 'SW', 'TA', 'TE', 'TG', 'TK', 'TL', 'TN', 'TS', 'TT', 
    'UR', 'UZ', 'WO', 'XH', 'YUE'
}

# Version Management - Centralized version control
APP_VERSION = "v3.7.0"
APP_RELEASE_DATE = "4 October 2025"
APP_RELEASE_DATE_POLISH = "4 października 2025"
GITHUB_API_URL = "https://api.github.com/repos/tomkam1702/OCR-Translator/releases/latest"

def parse_version(version_str):
    """Parse version string like 'v3.5.7' into comparable tuple (3, 5, 7)"""
    try:
        # Remove 'v' prefix if present and split by '.'
        clean_version = version_str.lstrip('v')
        return tuple(map(int, clean_version.split('.')))
    except (ValueError, AttributeError):
        # Fallback for invalid version strings
        return (0, 0, 0)

def is_newer_version(current, latest):
    """Compare two version strings and return True if latest > current"""
    try:
        current_tuple = parse_version(current)
        latest_tuple = parse_version(latest)
        return latest_tuple > current_tuple
    except Exception:
        # If comparison fails, assume no update needed
        return False

def get_current_version():
    """Get the current application version"""
    return APP_VERSION
