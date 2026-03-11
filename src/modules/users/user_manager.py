import os
import tkinter as tk
from tkinter import messagebox, ttk
import mysql.connector
from datetime import datetime
import re
from typing import Any, List
from src.auth.auth_manager import AuthManager
from src.auth.session_manager import session_manager
from src.database.conexion import conectar

class UserManagerApp:
    def __init__(self, root, user_data=None):
        self.root = root
        self.root.title("User Manager - Market")
        self.root.geometry("900x700")
        self.root.configure(bg="#f5f5f5")
        
        # User data and permissions
        self.user_data = user_data if isinstance(user_data, dict) else {}
        self.current_user_is_admin = (self.user_data.get('rol', '') == 'admin')
        
        # Initialize AuthManager
        self.auth_manager = AuthManager()
        
        # Connect to database
        try:
            self.conn: Any = conectar()
            self.cursor: Any = self.conn.cursor(dictionary=True)
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to the database: {e}")
            self.root.destroy()
            return
        
        # Variables
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_users)
        
        # Check admin permissions
        if not self.current_user_is_admin:
            messagebox.showerror("Access Denied", "This module requires administrator permissions.")
            self.root.destroy()
            return
        
        # Setup interface
        self.setup_interface()
        self.load_users()
        
        # Protocol for window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_interface(self):
        """Setup the main interface"""
        # Title frame
        title_frame = tk.Frame(self.root, bg="#2C3E50", height=80)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        
        tk.Label(title_frame, 
                text="USER MANAGER", 
                font=("Arial", 18, "bold"),
                fg="white", 
                bg="#2C3E50").pack(expand=True)
        
        # User info frame
        info_frame = tk.Frame(self.root, bg="#34495E", height=40)
        info_frame.pack(fill="x")
        info_frame.pack_propagate(False)
        
        user_info = f"User: {self.user_data.get('nombre_completo', '')} | Role: {self.user_data.get('rol', '').upper()}"
        tk.Label(info_frame, 
                text=user_info,
                font=("Arial", 10),
                fg="white", 
                bg="#34495E").pack(pady=10)
        
        # Main content frame
        main_frame = tk.Frame(self.root, bg="#f5f5f5")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Search and controls frame
        self.create_search_controls(main_frame)
        
        # Users table frame
        self.create_users_table(main_frame)
        
        # Action buttons frame
        self.create_action_buttons(main_frame)
    
    def create_search_controls(self, parent):
        """Create search and filter controls"""
        search_frame = tk.Frame(parent, bg="#f5f5f5")
        search_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(search_frame, 
                text="Search User:", 
                font=("Arial", 12, "bold"),
                bg="#f5f5f5").pack(side="left")
        
        search_entry = tk.Entry(search_frame, 
                               textvariable=self.search_var,
                               font=("Arial", 11),
                               width=30)
        search_entry.pack(side="left", padx=(10, 20))
        
        # Refresh button
        tk.Button(search_frame,
                 text="🔄 Refresh",
                 command=self.load_users,
                 font=("Arial", 10),
                 bg="#3498DB",
                 fg="white",
                 cursor="hand2").pack(side="right")
    
    def create_users_table(self, parent):
        """Create users table with scrollbars"""
        table_frame = tk.Frame(parent, bg="#f5f5f5")
        table_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Scrollbars
        v_scrollbar = tk.Scrollbar(table_frame)
        v_scrollbar.pack(side="right", fill="y")
        
        h_scrollbar = tk.Scrollbar(table_frame, orient="horizontal")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Treeview for users
        columns = ("ID", "Username", "Full Name", "Role", "Status", "Last Access", "Failed Attempts")
        self.users_tree = ttk.Treeview(table_frame,
                                      columns=columns,
                                      show="headings",
                                      yscrollcommand=v_scrollbar.set,
                                      xscrollcommand=h_scrollbar.set)
        
        # Configure columns
        column_widths = {"ID": 50, "Username": 120, "Full Name": 200, "Role": 80, 
                        "Status": 80, "Last Access": 150, "Failed Attempts": 120}
        
        for col in columns:
            self.users_tree.heading(col, text=col)
            self.users_tree.column(col, width=column_widths.get(col, 100), minwidth=50)
        
        self.users_tree.pack(fill="both", expand=True)
        
        # Configure scrollbars
        v_scrollbar.config(command=self.users_tree.yview)
        h_scrollbar.config(command=self.users_tree.xview)
        
        # Bind double-click for editing
        self.users_tree.bind("<Double-1>", self.edit_selected_user)
    
    def create_action_buttons(self, parent):
        """Create action buttons"""
        button_frame = tk.Frame(parent, bg="#f5f5f5")
        button_frame.pack(fill="x")
        
        # Button styling
        button_config = {
            "font": ("Arial", 11, "bold"),
            "cursor": "hand2",
            "relief": "flat",
            "padx": 15,
            "pady": 8
        }
        
        # Create User button
        tk.Button(button_frame,
                 text="👤 Create User",
                 command=self.create_new_user,
                 bg="#27AE60",
                 fg="white",
                 **button_config).pack(side="left", padx=(0, 10))
        
        # Edit User button
        tk.Button(button_frame,
                 text="✏️ Edit User",
                 command=self.edit_selected_user,
                 bg="#3498DB",
                 fg="white",
                 **button_config).pack(side="left", padx=(0, 10))
        
        # Toggle Status button
        tk.Button(button_frame,
                 text="🔄 Toggle Status",
                 command=self.toggle_user_status,
                 bg="#F39C12",
                 fg="white",
                 **button_config).pack(side="left", padx=(0, 10))
        
        # Reset Failed Attempts button
        tk.Button(button_frame,
                 text="🔓 Reset Lock",
                 command=self.reset_failed_attempts,
                 bg="#9B59B6",
                 fg="white",
                 **button_config).pack(side="left", padx=(0, 10))
        
        # Delete User button
        tk.Button(button_frame,
                 text="🗑️ Delete User",
                 command=self.delete_user,
                 bg="#E74C3C",
                 fg="white",
                 **button_config).pack(side="right")
    
    def load_users(self):
        """Load all users from database"""
        try:
            # Clear existing items
            for item in self.users_tree.get_children():
                self.users_tree.delete(item)
            
            # Fetch users
            self.cursor.execute("""
                SELECT id_usuario, username, nombre_completo, rol, activo, 
                       ultimo_acceso, intentos_fallidos, bloqueado_hasta
                FROM usuarios_sistema
                ORDER BY username
            """)
            
            users: List[Any] = self.cursor.fetchall()
            
            for user in users:
                # Format last access
                ultimo_acceso = "Never"
                if user['ultimo_acceso']:
                    ultimo_acceso = user['ultimo_acceso'].strftime("%Y-%m-%d %H:%M")
                
                # Determine status
                estado = "Active" if user['activo'] else "Inactive"
                if user['bloqueado_hasta'] and user['bloqueado_hasta'] > datetime.now():
                    estado = "Blocked"
                
                # Insert into tree
                self.users_tree.insert("", "end", values=(
                    user['id_usuario'],
                    user['username'],
                    user['nombre_completo'],
                    user['rol'].upper(),
                    estado,
                    ultimo_acceso,
                    user['intentos_fallidos']
                ))
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading users: {e}")
    
    def filter_users(self, *args):
        """Filter users based on search text"""
        search_text = self.search_var.get().lower()
        
        # If no search text, reload all users
        if not search_text:
            self.load_users()
            return
        
        # Clear existing items
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        
        try:
            # Search in username and full name
            self.cursor.execute("""
                SELECT id_usuario, username, nombre_completo, rol, activo, 
                       ultimo_acceso, intentos_fallidos, bloqueado_hasta
                FROM usuarios_sistema
                WHERE LOWER(username) LIKE %s OR LOWER(nombre_completo) LIKE %s
                ORDER BY username
            """, (f"%{search_text}%", f"%{search_text}%"))
            
            users: List[Any] = self.cursor.fetchall()
            
            for user in users:
                # Format last access
                ultimo_acceso = "Never"
                if user['ultimo_acceso']:
                    ultimo_acceso = user['ultimo_acceso'].strftime("%Y-%m-%d %H:%M")
                
                # Determine status
                estado = "Active" if user['activo'] else "Inactive"
                if user['bloqueado_hasta'] and user['bloqueado_hasta'] > datetime.now():
                    estado = "Blocked"
                
                # Insert into tree
                self.users_tree.insert("", "end", values=(
                    user['id_usuario'],
                    user['username'],
                    user['nombre_completo'],
                    user['rol'].upper(),
                    estado,
                    ultimo_acceso,
                    user['intentos_fallidos']
                ))
        
        except Exception as e:
            messagebox.showerror("Error", f"Error filtering users: {e}")
    
    def create_new_user(self):
        """Create a new user"""
        dialog = UserDialog(self.root, "Create New User", self.auth_manager)
        if dialog.result:
            self.load_users()
    
    def edit_selected_user(self, event=None):
        """Edit the selected user"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Selection", "Please select a user to edit.")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = int(item['values'][0])
        
        # Get current user data
        try:
            user_info = self.auth_manager.get_user_info_by_id(user_id)
            if user_info:
                dialog = UserDialog(self.root, "Edit User", self.auth_manager, user_info)
                if dialog.result:
                    self.load_users()
            else:
                messagebox.showerror("Error", "Could not load user information.")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading user: {e}")
    
    def toggle_user_status(self):
        """Toggle user active/inactive status"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Selection", "Please select a user.")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = int(item['values'][0])
        username = item['values'][1]
        current_status = item['values'][4]
        
        # Prevent self-deactivation
        if username == self.user_data.get('username', ''):
            messagebox.showwarning("Warning", "You cannot deactivate your own account.")
            return
        
        # Confirm action
        new_status = "inactive" if current_status == "Active" else "active"
        if not messagebox.askyesno("Confirm", 
                                  f"Are you sure you want to mark user '{username}' as {new_status}?"):
            return
        
        try:
            new_active = current_status != "Activo"
            self.cursor.execute("""
                UPDATE usuarios_sistema 
                SET activo = %s 
                WHERE id_usuario = %s
            """, (new_active, user_id))
            
            self.conn.commit()
            messagebox.showinfo("Success", f"User '{username}' marked as {new_status}.")
            self.load_users()
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error changing status: {e}")
    
    def reset_failed_attempts(self):
        """Reset failed login attempts for selected user"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Selection", "Please select a user.")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = int(item['values'][0])
        username = item['values'][1]
        
        if not messagebox.askyesno("Confirm", 
                                  f"Are you sure you want to reset failed attempts for '{username}'?"):
            return
        
        try:
            self.cursor.execute("""
                UPDATE usuarios_sistema 
                SET intentos_fallidos = 0, bloqueado_hasta = NULL 
                WHERE id_usuario = %s
            """, (user_id,))
            
            self.conn.commit()
            messagebox.showinfo("Success", f"Failed attempts reset for '{username}'.")
            self.load_users()
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error resetting attempts: {e}")
    
    def delete_user(self):
        """Delete selected user"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Selection", "Please select a user to delete.")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = int(item['values'][0])
        username = item['values'][1]
        
        # Prevent self-deletion
        if username == self.user_data.get('username', ''):
            messagebox.showwarning("Warning", "You cannot delete your own account.")
            return
        
        # Double confirmation for deletion
        if not messagebox.askyesno("CONFIRM DELETION", 
                                  f"Are you ABSOLUTELY SURE you want to delete user '{username}'?\n\n" +
                                  "This action CANNOT BE UNDONE."):
            return
        
        # Second confirmation
        if not messagebox.askyesno("FINAL CONFIRMATION", 
                                  f"LAST CHANCE: Permanently delete user '{username}'?"):
            return
        
        try:
            # Delete user
            self.cursor.execute("DELETE FROM usuarios_sistema WHERE id_usuario = %s", (user_id,))
            self.conn.commit()
            
            messagebox.showinfo("Success", f"User '{username}' deleted successfully.")
            self.load_users()
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error deleting user: {e}")
    
    def on_closing(self):
        """Handle window closing"""
        try:
            if hasattr(self, 'conn'):
                self.conn.close()
        except:
            pass
        self.root.destroy()


class UserDialog:
    """Dialog for creating/editing users"""
    
    def __init__(self, parent, title, auth_manager, user_data=None):
        self.result = False
        self.auth_manager = auth_manager
        self.editing = user_data is not None
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("450x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.configure(bg="#f5f5f5")
        
        # Variables
        self.username_var = tk.StringVar(value=user_data.get('username', '') if user_data else '')
        self.fullname_var = tk.StringVar(value=user_data.get('nombre_completo', '') if user_data else '')
        self.password_var = tk.StringVar()
        self.confirm_password_var = tk.StringVar()
        self.role_var = tk.StringVar(value=user_data.get('rol', 'usuario') if user_data else 'usuario')
        self.active_var = tk.BooleanVar(value=user_data.get('activo', True) if user_data else True)
        
        self.setup_dialog()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (400 // 2)
        self.dialog.geometry(f"450x400+{x}+{y}")
        
        # Focus on first field
        if self.editing:
            self.fullname_entry.focus_set()
        else:
            self.username_entry.focus_set()
    
    def setup_dialog(self):
        """Setup dialog interface"""
        main_frame = tk.Frame(self.dialog, bg="#f5f5f5", padx=30, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_text = "Edit User" if self.editing else "Create New User"
        tk.Label(main_frame, 
                text=title_text,
                font=("Arial", 16, "bold"),
                bg="#f5f5f5",
                fg="#2C3E50").pack(pady=(0, 20))
        
        # Username field
        tk.Label(main_frame, text="Username:", font=("Arial", 11, "bold"), bg="#f5f5f5").pack(anchor="w")
        self.username_entry = tk.Entry(main_frame, textvariable=self.username_var, font=("Arial", 11))
        self.username_entry.pack(fill="x", pady=(5, 15))
        
        if self.editing:
            self.username_entry.config(state="disabled")  # Can't change username when editing
        
        # Full name field
        tk.Label(main_frame, text="Full Name:", font=("Arial", 11, "bold"), bg="#f5f5f5").pack(anchor="w")
        self.fullname_entry = tk.Entry(main_frame, textvariable=self.fullname_var, font=("Arial", 11))
        self.fullname_entry.pack(fill="x", pady=(5, 15))
        
        # Password fields (only show if creating new user or if editing and want to change password)
        if not self.editing:
            tk.Label(main_frame, text="Password:", font=("Arial", 11, "bold"), bg="#f5f5f5").pack(anchor="w")
            tk.Entry(main_frame, textvariable=self.password_var, font=("Arial", 11), show="*").pack(fill="x", pady=(5, 10))
            
            tk.Label(main_frame, text="Confirm Password:", font=("Arial", 11, "bold"), bg="#f5f5f5").pack(anchor="w")
            tk.Entry(main_frame, textvariable=self.confirm_password_var, font=("Arial", 11), show="*").pack(fill="x", pady=(5, 15))
        else:
            # Option to change password when editing
            self.change_password_var = tk.BooleanVar()
            tk.Checkbutton(main_frame, 
                          text="Change password",
                          variable=self.change_password_var,
                          font=("Arial", 11),
                          bg="#f5f5f5",
                          command=self.toggle_password_fields).pack(anchor="w", pady=(0, 10))
            
            self.password_frame = tk.Frame(main_frame, bg="#f5f5f5")
            self.password_frame.pack(fill="x")
            
        # Role selection
        tk.Label(main_frame, text="Role:", font=("Arial", 11, "bold"), bg="#f5f5f5").pack(anchor="w")
        role_frame = tk.Frame(main_frame, bg="#f5f5f5")
        role_frame.pack(fill="x", pady=(5, 15))
        
        tk.Radiobutton(role_frame, text="User", variable=self.role_var, value="usuario", 
                      font=("Arial", 11), bg="#f5f5f5").pack(side="left")
        tk.Radiobutton(role_frame, text="Administrator", variable=self.role_var, value="admin", 
                      font=("Arial", 11), bg="#f5f5f5").pack(side="left", padx=(20, 0))
        
        # Active checkbox (only for editing)
        if self.editing:
            tk.Checkbutton(main_frame, 
                          text="Active user",
                          variable=self.active_var,
                          font=("Arial", 11),
                          bg="#f5f5f5").pack(anchor="w", pady=(0, 15))
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg="#f5f5f5")
        button_frame.pack(fill="x", pady=(20, 0))
        
        tk.Button(button_frame,
                 text="Cancel",
                 command=self.dialog.destroy,
                 font=("Arial", 11),
                 bg="#95A5A6",
                 fg="white",
                 cursor="hand2",
                 padx=20).pack(side="right", padx=(10, 0))
        
        save_text = "Update" if self.editing else "Create"
        tk.Button(button_frame,
                 text=save_text,
                 command=self.save_user,
                 font=("Arial", 11, "bold"),
                 bg="#27AE60",
                 fg="white",
                 cursor="hand2",
                 padx=20).pack(side="right")
    
    def toggle_password_fields(self):
        """Show/hide password fields when editing"""
        if not self.editing:
            return
            
        # Clear password frame
        for widget in self.password_frame.winfo_children():
            widget.destroy()
        
        if self.change_password_var.get():
            tk.Label(self.password_frame, text="New Password:", font=("Arial", 11, "bold"), bg="#f5f5f5").pack(anchor="w")
            tk.Entry(self.password_frame, textvariable=self.password_var, font=("Arial", 11), show="*").pack(fill="x", pady=(5, 10))
            
            tk.Label(self.password_frame, text="Confirm New Password:", font=("Arial", 11, "bold"), bg="#f5f5f5").pack(anchor="w")
            tk.Entry(self.password_frame, textvariable=self.confirm_password_var, font=("Arial", 11), show="*").pack(fill="x", pady=(5, 0))
    
    def validate_input(self):
        """Validate user input"""
        username = self.username_var.get().strip()
        fullname = self.fullname_var.get().strip()
        password = self.password_var.get()
        confirm_password = self.confirm_password_var.get()
        
        # Check required fields
        if not username:
            messagebox.showerror("Error", "Username is required.")
            return False
        
        if not fullname:
            messagebox.showerror("Error", "Full name is required.")
            return False
        
        # Username validation
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            messagebox.showerror("Error", "Username can only contain letters, numbers, and underscores.")
            return False
        
        if len(username) < 3:
            messagebox.showerror("Error", "Username must be at least 3 characters.")
            return False
        
        # Password validation (for new users or when changing password)
        need_password = not self.editing or (self.editing and hasattr(self, 'change_password_var') and self.change_password_var.get())
        
        if need_password:
            if not password:
                messagebox.showerror("Error", "Password is required.")
                return False
            
            if len(password) < 8:
                messagebox.showerror("Error", "Password must be at least 8 characters.")
                return False
            
            if password != confirm_password:
                messagebox.showerror("Error", "Passwords do not match.")
                return False
        
        return True
    
    def save_user(self):
        """Save user data"""
        if not self.validate_input():
            return
        
        try:
            username = self.username_var.get().strip()
            fullname = self.fullname_var.get().strip()
            password = self.password_var.get()
            role = self.role_var.get()
            active = self.active_var.get() if self.editing else True
            
            if self.editing:
                # Update existing user
                result = self.auth_manager.update_user(
                    username, fullname, role, active,
                    password if hasattr(self, 'change_password_var') and self.change_password_var.get() else None
                )
            else:
                # Create new user
                result = self.auth_manager.create_user(username, password, fullname, role)
            
            if result['success']:
                self.result = True
                messagebox.showinfo("Success", result['message'])
                self.dialog.destroy()
            else:
                messagebox.showerror("Error", result['message'])
                
        except Exception as e:
            messagebox.showerror("Error", f"Error saving user: {e}")


def main(user_data=None):
    """Main function to run the user manager"""
    # Parse user data if it's a JSON string
    if isinstance(user_data, str):
        import json
        try:
            user_data = json.loads(user_data)
        except:
            user_data = {}
    
    root = tk.Tk()
    app = UserManagerApp(root, user_data)
    root.mainloop()


if __name__ == "__main__":
    # Test data for standalone running
    test_user_data = {
        'username': 'Valeria',
        'nombre_completo': 'Valeria (Administrator)',
        'rol': 'admin'
    }
    main(test_user_data)