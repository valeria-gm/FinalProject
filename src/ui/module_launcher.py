"""
Module Launcher
Handles module definitions, launching, and management
"""

import os
import sys
import subprocess
from tkinter import messagebox
from src.config import debug_print, USE_SESSION_MANAGER

class ModuleLauncher:
    """Class for managing and launching application modules"""
    
    def __init__(self):
        self.modules = self._get_module_definitions()
        
        # Calculate absolute path to project root
        # This file is in src/ui/module_launcher.py
        # So we need to go up 2 levels: src/ui/ -> src/ -> project_root/
        current_file = os.path.abspath(__file__)
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        self.launcher_script_path = os.path.join(self.project_root, "launch_module.py")
        
        debug_print(f"ModuleLauncher initialized:")
        debug_print(f"  Current file: {current_file}")
        debug_print(f"  Project root: {self.project_root}")
        debug_print(f"  Launcher script: {self.launcher_script_path}")
        debug_print(f"  Launcher exists: {os.path.exists(self.launcher_script_path)}")
    
    def _get_module_definitions(self):
        """Get all module definitions"""
        return [
            {
                'title': 'Generate Receipts',
                'description': 'Create customer receipts\nand manage invoicing',
                'module_key': 'receipts',
                'bg_color': '#3498DB',
                'hover_color': '#2980B9',
                'requires_admin': False
            },
            {
                'title': 'Price Editor',
                'description': 'Manage products\nand prices by client type',
                'module_key': 'pricing',
                'bg_color': '#E74C3C',
                'hover_color': '#C0392B',
                'requires_admin': True
            },
            {
                'title': 'Purchase Registry',
                'description': 'Record purchases\nand manage inventory',
                'module_key': 'inventory',
                'bg_color': '#2ECC71',
                'hover_color': '#27AE60',
                'requires_admin': False
            },
            {
                'title': 'Profit Analysis',
                'description': 'View detailed reports\non profits and losses',
                'module_key': 'analytics',
                'bg_color': '#9B59B6',
                'hover_color': '#8E44AD',
                'requires_admin': True
            },
            {
                'title': 'Manage Clients',
                'description': 'Manage clients\nand client types',
                'module_key': 'clients',
                'bg_color': '#F39C12',
                'hover_color': '#E67E22',
                'requires_admin': True
            },
            {
                'title': 'Manage Users',
                'description': 'Manage system users\nand access permissions',
                'module_key': 'users',
                'bg_color': '#34495E',
                'hover_color': '#2C3E50',
                'requires_admin': True
            },
            {
                'title': 'Debt Management',
                'description': 'Accounts receivable control\nand payment tracking',
                'module_key': 'debts',
                'bg_color': '#E67E22',
                'hover_color': '#D35400',
                'requires_admin': True
            }
        ]
    
    def get_available_modules(self, user_role):
        """Get modules available for the given user role"""
        available_modules = []
        
        for module in self.modules:
            if module['requires_admin'] and user_role != 'admin':
                continue
            available_modules.append(module)
        
        debug_print(f"Available modules for role '{user_role}': {len(available_modules)}")
        return available_modules
    
    def launch_module(self, module_key, user_data=None):
        """Launch a module using the proper launcher"""
        debug_print(f"Launching module: {module_key}")
        
        try:
            # Update session activity if session manager is enabled
            if USE_SESSION_MANAGER:
                try:
                    from src.auth.session_manager import session_manager
                    session_manager.update_activity()
                except ImportError:
                    debug_print("Session manager not available")
            
            # Check if launcher script exists using absolute path
            if not os.path.exists(self.launcher_script_path):
                error_msg = f"Launcher not found: {self.launcher_script_path}"
                debug_print(f"ERROR: {error_msg}")
                messagebox.showerror("Error", error_msg)
                return False
            
            # Prepare user data as JSON string
            user_data_json = ""
            if user_data:
                import json
                user_data_json = json.dumps(user_data, ensure_ascii=False)
            
            # Prepare command with absolute paths
            cmd = [sys.executable, self.launcher_script_path, module_key]
            if user_data_json:
                cmd.append(user_data_json)
            
            debug_print(f"Command: {' '.join(cmd[:3])}{'[USER_DATA]' if len(cmd) > 3 else ''}")
            
            # Change to project root directory before launching
            old_cwd = os.getcwd()
            os.chdir(self.project_root)
            debug_print(f"Changed working directory to: {self.project_root}")
            
            # Launch module
            try:
                if sys.platform.startswith('win'):
                    process = subprocess.Popen(
                        cmd, 
                        cwd=self.project_root,
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                else:
                    process = subprocess.Popen(cmd, cwd=self.project_root)
                
                debug_print(f"Module {module_key} launched successfully (PID: {process.pid})")
                return True
                
            finally:
                # Always restore original working directory
                os.chdir(old_cwd)
                debug_print(f"Restored working directory to: {old_cwd}")
                
        except FileNotFoundError as e:
            error_msg = f"File not found: {str(e)}"
            debug_print(f"FileNotFoundError: {error_msg}")
            messagebox.showerror("Error", error_msg)
            return False
            
        except subprocess.SubprocessError as e:
            error_msg = f"Error launching module: {str(e)}"
            debug_print(f"SubprocessError: {error_msg}")
            messagebox.showerror("Error", error_msg)
            return False
            
        except Exception as e:
            error_msg = f"Could not open module '{module_key}': {str(e)}"
            debug_print(f"Unexpected error: {error_msg}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", error_msg)
            return False
    
    def validate_module_launcher(self):
        """Validate that the module launcher exists"""
        if not os.path.exists(self.launcher_script_path):
            debug_print(f"Missing module launcher: {self.launcher_script_path}")
            return False, [self.launcher_script_path]
        
        debug_print("Module launcher validated successfully")
        return True, []
    
    def get_module_by_key(self, module_key):
        """Get module definition by module key"""
        for module in self.modules:
            if module['module_key'] == module_key:
                return module
        return None
    
    def get_launcher_status(self):
        """Get detailed status information for debugging"""
        return {
            "launcher_exists": os.path.exists(self.launcher_script_path),
            "launcher_path": self.launcher_script_path,
            "project_root": self.project_root,
            "current_working_directory": os.getcwd(),
            "python_executable": sys.executable
        }