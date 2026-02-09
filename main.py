#!/usr/bin/env python3
"""
DISFRULEG - Sistema de Gestión Comercial
Refactored modular version - Entry Point
"""

import sys
from tkinter import messagebox

from src.config import debug_print, get_app_config
from src.main_application import MainApplication

def main():
    """Main function - Entry point"""
    try:
        config = get_app_config()
        
        debug_print("=== PROGRAM START ===")
        debug_print(f"Debug mode: {config['debug_mode']}")
        debug_print(f"Use login: {config['use_login']}")
        debug_print(f"Use session manager: {config['use_session_manager']}")
        debug_print(f"Use canvas scroll: {config['use_canvas_scroll']}")
        debug_print(f"Use hover effects: {config['use_hover_effects']}")
        
        # Create and start application
        app = MainApplication()
        app.start()
        
    except Exception as e:
        debug_print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Error Fatal", f"Error inesperado: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()