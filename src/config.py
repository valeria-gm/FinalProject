"""
Configuration Module
Contains application settings, debug flags, and constants
"""

# Debug and Feature Flags
DEBUG_MODE = True
USE_LOGIN = True
USE_SESSION_MANAGER = True
USE_CANVAS_SCROLL = True
USE_HOVER_EFFECTS = True

# Application Constants
APP_TITLE = "Management System"
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700
WINDOW_BG_COLOR = "#f5f5f5"

# Color Scheme
COLORS = {
    'header_bg': '#2C3E50',
    'header_text': 'white',
    'header_subtitle': '#BDC3C7',
    'logout_btn': '#E74C3C',
    'exit_btn': '#E74C3C',
    'button_text': 'white'
}

def debug_print(message):
    """Print debug messages if debug mode is enabled"""
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")

def get_app_config():
    """Get current application configuration"""
    return {
        'debug_mode': DEBUG_MODE,
        'use_login': USE_LOGIN,
        'use_session_manager': USE_SESSION_MANAGER,
        'use_canvas_scroll': USE_CANVAS_SCROLL,
        'use_hover_effects': USE_HOVER_EFFECTS,
        'window_width': WINDOW_WIDTH,
        'window_height': WINDOW_HEIGHT,
        'window_bg': WINDOW_BG_COLOR,
        'app_title': APP_TITLE,
        'colors': COLORS
    }