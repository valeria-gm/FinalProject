"""
Main Application Module
Contains the core application class and logic
"""

import tkinter as tk
from tkinter import messagebox
import sys

from src.config import (
    debug_print, get_app_config, USE_LOGIN, USE_SESSION_MANAGER, 
    USE_CANVAS_SCROLL, WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_BG_COLOR
)
from src.ui.ui_components import UIComponents
from src.ui.module_launcher import ModuleLauncher

class MainApplication:
    """Main application class"""
    
    def __init__(self):
        self.root = None
        self.user_data = None
        self.ui_components = None
        self.module_launcher = None
        self.config = get_app_config()
        
    def start(self):
        """Start the application"""
        debug_print("Starting application...")
        
        # Initialize module launcher
        self.module_launcher = ModuleLauncher()
        
        # Handle login
        if USE_LOGIN:
            if not self._handle_login():
                debug_print("Login cancelled")
                sys.exit(0)
        else:
            # Simulated user
            self.user_data = {
                'nombre_completo': 'Usuario de Prueba',
                'rol': 'admin',
                'username': 'test'
            }
            debug_print("Using simulated user")
        
        # Create main window
        self.create_main_window()
        self.run_main_loop()
    
    def _handle_login(self):
        """Handle user login"""
        try:
            debug_print("Importing login system...")
            from src.auth.login_window import show_login
            success, user_data = show_login(self.on_login_success)
            
            if success and user_data:
                self.user_data = user_data
                debug_print(f"Login successful: {user_data}")
                return True
            else:
                return False
        except Exception as e:
            debug_print(f"Login error: {e}")
            messagebox.showerror("Error", f"Login system error: {e}")
            return False
    
    def on_login_success(self, user_data):
        """Callback executed when login is successful"""
        self.user_data = user_data
        debug_print(f"Login callback successful: {user_data['nombre_completo']}")
    
    def create_main_window(self):
        """Create main window"""
        debug_print("Creating main window...")
        
        try:
            self.root = tk.Tk()
            self.root.title(self.config['app_title'])
            
            # Configure window size
            debug_print("Configuring geometry...")
            self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
            self.root.configure(bg=WINDOW_BG_COLOR)
            
            # Configure close protocol
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            # Initialize UI components
            self.ui_components = UIComponents(self.root, self.user_data)
            
            # Initialize session manager
            if USE_SESSION_MANAGER:
                self._init_session_manager()
            
            # Create interface
            debug_print("Creating interface...")
            self.create_interface()
            
            # Center window
            debug_print("Centering window...")
            self.root.after(100, self.center_window)
            
        except Exception as e:
            debug_print(f"Error creating main window: {e}")
            raise
    
    def _init_session_manager(self):
        """Initialize session manager"""
        try:
            debug_print("Initializing session manager...")
            from src.auth.session_manager import session_manager
            session_manager.add_callback(self.handle_session_event)
            session_manager.start_session(self.user_data)
        except Exception as e:
            debug_print(f"Session manager error: {e}")
            messagebox.showwarning("Warning", f"Session manager not available: {e}")
    
    def center_window(self):
        """Center window on screen"""
        try:
            debug_print("Executing safe centering...")
            self.root.update_idletasks()
            
            # Get screen dimensions
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            debug_print(f"Screen: {screen_width}x{screen_height}")
            debug_print(f"Window: {WINDOW_WIDTH}x{WINDOW_HEIGHT}")
            
            # Calculate centered position
            x = max(0, int((screen_width - WINDOW_WIDTH) / 2))
            y = max(0, int((screen_height - WINDOW_HEIGHT) / 2))
            
            debug_print(f"Calculated position: x={x}, y={y}")
            
            # Apply geometry
            geometry_string = f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}"
            self.root.geometry(geometry_string)
            debug_print("Centering completed successfully")
            
        except Exception as e:
            debug_print(f"Centering error: {e}")
            # Not critical if centering fails
    
    def create_interface(self):
        """Create main interface"""
        debug_print("Creating interface components...")
        
        try:
            # Header
            debug_print("Creating header...")
            self.ui_components.create_header(self.logout)
            
            # Main content
            debug_print("Creating main content...")
            self.create_main_content()
            
            # Status bar
            debug_print("Creating status bar...")
            self.ui_components.create_status_bar(self.on_closing)
            
            debug_print("Interface created successfully")
            
        except Exception as e:
            debug_print(f"Error creating interface: {e}")
            raise
    
    def create_main_content(self):
        """Create main content area"""
        try:
            if USE_CANVAS_SCROLL:
                # Version with canvas and scroll
                debug_print("Using canvas scroll version...")
                self.create_main_content_with_scroll()
            else:
                # Simple version without scroll
                debug_print("Using simple version without scroll...")
                self.create_main_content_simple()
                
        except Exception as e:
            debug_print(f"Error creating main content: {e}")
            raise
    
    def create_main_content_simple(self):
        """Create simple main content"""
        main_frame = tk.Frame(self.root, bg=WINDOW_BG_COLOR)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.create_modules_grid(main_frame)
    
    def create_main_content_with_scroll(self):
        """Create main content with scroll"""
        main_frame = tk.Frame(self.root, bg=WINDOW_BG_COLOR)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        scrollable_frame = self.ui_components.create_scrollable_content(main_frame)
        self.create_modules_grid(scrollable_frame)
    
    def create_modules_grid(self, parent):
        """Create modules grid"""
        debug_print("Creating modules grid...")
        
        try:
            # Get available modules for user role
            user_role = self.user_data.get('rol', 'usuario')
            available_modules = self.module_launcher.get_available_modules(user_role)
            
            # Create cards
            row = 0
            col = 0
            max_cols = 2
            
            for i, module in enumerate(available_modules):
                debug_print(f"Creating module {i+1}: {module['title']}")
                self.ui_components.create_module_card(
                    parent, module, row, col, self.launch_module
                )
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
            
            # Configure columns
            for i in range(max_cols):
                parent.grid_columnconfigure(i, weight=1, uniform="column")
                
            debug_print("Modules grid created successfully")
            
        except Exception as e:
            debug_print(f"Error creating modules grid: {e}")
            raise
    
    def launch_module(self, module_key):
        """Launch a module"""
        return self.module_launcher.launch_module(module_key, self.user_data)
    
    def handle_session_event(self, event_type, user_data):
        """Handle session events"""
        debug_print(f"Session event: {event_type}")
        
        if event_type == 'session_timeout':
            messagebox.showwarning("Session Expired", 
                                 "Your session has expired due to inactivity.")
            self.force_logout()
        elif event_type == 'session_ended':
            self.close_application()
    
    def logout(self):
        """Logout user"""
        if messagebox.askyesno("Log Out", 
                             "Are you sure you want to log out?"):
            self.force_logout()
    
    def force_logout(self):
        """Force logout"""
        debug_print("Forcing logout...")
        
        if USE_SESSION_MANAGER:
            try:
                from src.auth.session_manager import session_manager
                session_manager.end_session()
            except:
                pass
        
        if USE_LOGIN:
            try:
                from src.database.db_manager import db_manager
                db_manager.close_connection()
            except:
                pass
        
        self.close_application()
    
    def close_application(self):
        """Close application"""
        debug_print("Closing application...")
        
        try:
            if self.root:
                self.root.quit()
                self.root.destroy()
        except:
            pass
        
        sys.exit(0)
    
    def on_closing(self):
        """Handle window closing"""
        if messagebox.askyesno("Exit", "Are you sure you want to exit the system?"):
            self.force_logout()
    
    def run_main_loop(self):
        """Run main application loop"""
        debug_print("Starting main loop...")
        
        if self.root:
            self.root.mainloop()