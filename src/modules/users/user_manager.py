import os
import tkinter as tk
from tkinter import messagebox, ttk
import mysql.connector
from datetime import datetime
import re
from src.auth.auth_manager import AuthManager
from src.auth.session_manager import session_manager
from src.database.conexion import conectar

class UserManagerApp:
    def __init__(self, root, user_data=None):
        self.root = root
        self.root.title("Administrador de Usuarios - Disfruleg")
        self.root.geometry("900x700")
        self.root.configure(bg="#f5f5f5")
        
        # User data and permissions
        self.user_data = user_data if isinstance(user_data, dict) else {}
        self.current_user_is_admin = (self.user_data.get('rol', '') == 'admin')
        
        # Initialize AuthManager
        self.auth_manager = AuthManager()
        
        # Connect to database
        try:
            self.conn = conectar()
            self.cursor = self.conn.cursor(dictionary=True)
        except Exception as e:
            messagebox.showerror("Error de Conexión", f"No se pudo conectar a la base de datos: {e}")
            self.root.destroy()
            return
        
        # Variables
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_users)
        
        # Check admin permissions
        if not self.current_user_is_admin:
            messagebox.showerror("Acceso Denegado", "Este módulo requiere permisos de administrador.")
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
                text="ADMINISTRADOR DE USUARIOS", 
                font=("Arial", 18, "bold"),
                fg="white", 
                bg="#2C3E50").pack(expand=True)
        
        # User info frame
        info_frame = tk.Frame(self.root, bg="#34495E", height=40)
        info_frame.pack(fill="x")
        info_frame.pack_propagate(False)
        
        user_info = f"Usuario: {self.user_data.get('nombre_completo', '')} | Rol: {self.user_data.get('rol', '').upper()}"
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
                text="Buscar Usuario:", 
                font=("Arial", 12, "bold"),
                bg="#f5f5f5").pack(side="left")
        
        search_entry = tk.Entry(search_frame, 
                               textvariable=self.search_var,
                               font=("Arial", 11),
                               width=30)
        search_entry.pack(side="left", padx=(10, 20))
        
        # Refresh button
        tk.Button(search_frame,
                 text="🔄 Actualizar",
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
        columns = ("ID", "Usuario", "Nombre Completo", "Rol", "Estado", "Último Acceso", "Intentos Fallidos")
        self.users_tree = ttk.Treeview(table_frame,
                                      columns=columns,
                                      show="headings",
                                      yscrollcommand=v_scrollbar.set,
                                      xscrollcommand=h_scrollbar.set)
        
        # Configure columns
        column_widths = {"ID": 50, "Usuario": 120, "Nombre Completo": 200, "Rol": 80, 
                        "Estado": 80, "Último Acceso": 150, "Intentos Fallidos": 120}
        
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
                 text="👤 Crear Usuario",
                 command=self.create_new_user,
                 bg="#27AE60",
                 fg="white",
                 **button_config).pack(side="left", padx=(0, 10))
        
        # Edit User button
        tk.Button(button_frame,
                 text="✏️ Editar Usuario",
                 command=self.edit_selected_user,
                 bg="#3498DB",
                 fg="white",
                 **button_config).pack(side="left", padx=(0, 10))
        
        # Toggle Status button
        tk.Button(button_frame,
                 text="🔄 Cambiar Estado",
                 command=self.toggle_user_status,
                 bg="#F39C12",
                 fg="white",
                 **button_config).pack(side="left", padx=(0, 10))
        
        # Reset Failed Attempts button
        tk.Button(button_frame,
                 text="🔓 Resetear Bloqueo",
                 command=self.reset_failed_attempts,
                 bg="#9B59B6",
                 fg="white",
                 **button_config).pack(side="left", padx=(0, 10))
        
        # Delete User button
        tk.Button(button_frame,
                 text="🗑️ Eliminar Usuario",
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
            
            users = self.cursor.fetchall()
            
            for user in users:
                # Format last access
                ultimo_acceso = "Nunca"
                if user['ultimo_acceso']:
                    ultimo_acceso = user['ultimo_acceso'].strftime("%Y-%m-%d %H:%M")
                
                # Determine status
                estado = "Activo" if user['activo'] else "Inactivo"
                if user['bloqueado_hasta'] and user['bloqueado_hasta'] > datetime.now():
                    estado = "Bloqueado"
                
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
            messagebox.showerror("Error", f"Error al cargar usuarios: {e}")
    
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
            
            users = self.cursor.fetchall()
            
            for user in users:
                # Format last access
                ultimo_acceso = "Nunca"
                if user['ultimo_acceso']:
                    ultimo_acceso = user['ultimo_acceso'].strftime("%Y-%m-%d %H:%M")
                
                # Determine status
                estado = "Activo" if user['activo'] else "Inactivo"
                if user['bloqueado_hasta'] and user['bloqueado_hasta'] > datetime.now():
                    estado = "Bloqueado"
                
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
            messagebox.showerror("Error", f"Error al filtrar usuarios: {e}")
    
    def create_new_user(self):
        """Create a new user"""
        dialog = UserDialog(self.root, "Crear Nuevo Usuario", self.auth_manager)
        if dialog.result:
            self.load_users()
    
    def edit_selected_user(self, event=None):
        """Edit the selected user"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Selección", "Por favor, seleccione un usuario para editar.")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = item['values'][0]
        
        # Get current user data
        try:
            user_info = self.auth_manager.get_user_info_by_id(user_id)
            if user_info:
                dialog = UserDialog(self.root, "Editar Usuario", self.auth_manager, user_info)
                if dialog.result:
                    self.load_users()
            else:
                messagebox.showerror("Error", "No se pudo cargar la información del usuario.")
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar usuario: {e}")
    
    def toggle_user_status(self):
        """Toggle user active/inactive status"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Selección", "Por favor, seleccione un usuario.")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = item['values'][0]
        username = item['values'][1]
        current_status = item['values'][4]
        
        # Prevent self-deactivation
        if username == self.user_data.get('username', ''):
            messagebox.showwarning("Advertencia", "No puede desactivar su propia cuenta.")
            return
        
        # Confirm action
        new_status = "inactivo" if current_status == "Activo" else "activo"
        if not messagebox.askyesno("Confirmar", 
                                  f"¿Está seguro de que desea marcar al usuario '{username}' como {new_status}?"):
            return
        
        try:
            new_active = current_status != "Activo"
            self.cursor.execute("""
                UPDATE usuarios_sistema 
                SET activo = %s 
                WHERE id_usuario = %s
            """, (new_active, user_id))
            
            self.conn.commit()
            messagebox.showinfo("Éxito", f"Usuario '{username}' marcado como {new_status}.")
            self.load_users()
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error al cambiar estado: {e}")
    
    def reset_failed_attempts(self):
        """Reset failed login attempts for selected user"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Selección", "Por favor, seleccione un usuario.")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = item['values'][0]
        username = item['values'][1]
        
        if not messagebox.askyesno("Confirmar", 
                                  f"¿Está seguro de que desea resetear los intentos fallidos para '{username}'?"):
            return
        
        try:
            self.cursor.execute("""
                UPDATE usuarios_sistema 
                SET intentos_fallidos = 0, bloqueado_hasta = NULL 
                WHERE id_usuario = %s
            """, (user_id,))
            
            self.conn.commit()
            messagebox.showinfo("Éxito", f"Intentos fallidos reseteados para '{username}'.")
            self.load_users()
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error al resetear intentos: {e}")
    
    def delete_user(self):
        """Delete selected user"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Selección", "Por favor, seleccione un usuario para eliminar.")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = item['values'][0]
        username = item['values'][1]
        
        # Prevent self-deletion
        if username == self.user_data.get('username', ''):
            messagebox.showwarning("Advertencia", "No puede eliminar su propia cuenta.")
            return
        
        # Double confirmation for deletion
        if not messagebox.askyesno("CONFIRMAR ELIMINACIÓN", 
                                  f"¿Está ABSOLUTAMENTE SEGURO de que desea eliminar al usuario '{username}'?\n\n" +
                                  "Esta acción NO SE PUEDE DESHACER."):
            return
        
        # Second confirmation
        if not messagebox.askyesno("ÚLTIMA CONFIRMACIÓN", 
                                  f"ÚLTIMA OPORTUNIDAD: ¿Eliminar permanentemente al usuario '{username}'?"):
            return
        
        try:
            # Delete user
            self.cursor.execute("DELETE FROM usuarios_sistema WHERE id_usuario = %s", (user_id,))
            self.conn.commit()
            
            messagebox.showinfo("Éxito", f"Usuario '{username}' eliminado exitosamente.")
            self.load_users()
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error al eliminar usuario: {e}")
    
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
        title_text = "Editar Usuario" if self.editing else "Crear Nuevo Usuario"
        tk.Label(main_frame, 
                text=title_text,
                font=("Arial", 16, "bold"),
                bg="#f5f5f5",
                fg="#2C3E50").pack(pady=(0, 20))
        
        # Username field
        tk.Label(main_frame, text="Nombre de Usuario:", font=("Arial", 11, "bold"), bg="#f5f5f5").pack(anchor="w")
        self.username_entry = tk.Entry(main_frame, textvariable=self.username_var, font=("Arial", 11))
        self.username_entry.pack(fill="x", pady=(5, 15))
        
        if self.editing:
            self.username_entry.config(state="disabled")  # Can't change username when editing
        
        # Full name field
        tk.Label(main_frame, text="Nombre Completo:", font=("Arial", 11, "bold"), bg="#f5f5f5").pack(anchor="w")
        self.fullname_entry = tk.Entry(main_frame, textvariable=self.fullname_var, font=("Arial", 11))
        self.fullname_entry.pack(fill="x", pady=(5, 15))
        
        # Password fields (only show if creating new user or if editing and want to change password)
        if not self.editing:
            tk.Label(main_frame, text="Contraseña:", font=("Arial", 11, "bold"), bg="#f5f5f5").pack(anchor="w")
            tk.Entry(main_frame, textvariable=self.password_var, font=("Arial", 11), show="*").pack(fill="x", pady=(5, 10))
            
            tk.Label(main_frame, text="Confirmar Contraseña:", font=("Arial", 11, "bold"), bg="#f5f5f5").pack(anchor="w")
            tk.Entry(main_frame, textvariable=self.confirm_password_var, font=("Arial", 11), show="*").pack(fill="x", pady=(5, 15))
        else:
            # Option to change password when editing
            self.change_password_var = tk.BooleanVar()
            tk.Checkbutton(main_frame, 
                          text="Cambiar contraseña",
                          variable=self.change_password_var,
                          font=("Arial", 11),
                          bg="#f5f5f5",
                          command=self.toggle_password_fields).pack(anchor="w", pady=(0, 10))
            
            self.password_frame = tk.Frame(main_frame, bg="#f5f5f5")
            self.password_frame.pack(fill="x")
            
        # Role selection
        tk.Label(main_frame, text="Rol:", font=("Arial", 11, "bold"), bg="#f5f5f5").pack(anchor="w")
        role_frame = tk.Frame(main_frame, bg="#f5f5f5")
        role_frame.pack(fill="x", pady=(5, 15))
        
        tk.Radiobutton(role_frame, text="Usuario", variable=self.role_var, value="usuario", 
                      font=("Arial", 11), bg="#f5f5f5").pack(side="left")
        tk.Radiobutton(role_frame, text="Administrador", variable=self.role_var, value="admin", 
                      font=("Arial", 11), bg="#f5f5f5").pack(side="left", padx=(20, 0))
        
        # Active checkbox (only for editing)
        if self.editing:
            tk.Checkbutton(main_frame, 
                          text="Usuario activo",
                          variable=self.active_var,
                          font=("Arial", 11),
                          bg="#f5f5f5").pack(anchor="w", pady=(0, 15))
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg="#f5f5f5")
        button_frame.pack(fill="x", pady=(20, 0))
        
        tk.Button(button_frame,
                 text="Cancelar",
                 command=self.dialog.destroy,
                 font=("Arial", 11),
                 bg="#95A5A6",
                 fg="white",
                 cursor="hand2",
                 padx=20).pack(side="right", padx=(10, 0))
        
        save_text = "Actualizar" if self.editing else "Crear"
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
            tk.Label(self.password_frame, text="Nueva Contraseña:", font=("Arial", 11, "bold"), bg="#f5f5f5").pack(anchor="w")
            tk.Entry(self.password_frame, textvariable=self.password_var, font=("Arial", 11), show="*").pack(fill="x", pady=(5, 10))
            
            tk.Label(self.password_frame, text="Confirmar Nueva Contraseña:", font=("Arial", 11, "bold"), bg="#f5f5f5").pack(anchor="w")
            tk.Entry(self.password_frame, textvariable=self.confirm_password_var, font=("Arial", 11), show="*").pack(fill="x", pady=(5, 0))
    
    def validate_input(self):
        """Validate user input"""
        username = self.username_var.get().strip()
        fullname = self.fullname_var.get().strip()
        password = self.password_var.get()
        confirm_password = self.confirm_password_var.get()
        
        # Check required fields
        if not username:
            messagebox.showerror("Error", "El nombre de usuario es requerido.")
            return False
        
        if not fullname:
            messagebox.showerror("Error", "El nombre completo es requerido.")
            return False
        
        # Username validation
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            messagebox.showerror("Error", "El nombre de usuario solo puede contener letras, números y guiones bajos.")
            return False
        
        if len(username) < 3:
            messagebox.showerror("Error", "El nombre de usuario debe tener al menos 3 caracteres.")
            return False
        
        # Password validation (for new users or when changing password)
        need_password = not self.editing or (self.editing and hasattr(self, 'change_password_var') and self.change_password_var.get())
        
        if need_password:
            if not password:
                messagebox.showerror("Error", "La contraseña es requerida.")
                return False
            
            if len(password) < 8:
                messagebox.showerror("Error", "La contraseña debe tener al menos 8 caracteres.")
                return False
            
            if password != confirm_password:
                messagebox.showerror("Error", "Las contraseñas no coinciden.")
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
                messagebox.showinfo("Éxito", result['message'])
                self.dialog.destroy()
            else:
                messagebox.showerror("Error", result['message'])
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar usuario: {e}")


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
        'username': 'jared',
        'nombre_completo': 'Jared (Administrador)',
        'rol': 'admin'
    }
    main(test_user_data)