import tkinter as tk
from tkinter import messagebox, ttk
import threading
from datetime import datetime
import locale
import os
from typing import Any

# CRITICAL FIX: Force C locale to avoid decimal comma issues
try:
    locale.setlocale(locale.LC_NUMERIC, 'C')
except locale.Error:
    # Fallback if setting locale fails
    pass

# Import with fallback for PIL
PIL_AVAILABLE = False
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    print("Warning: PIL/Pillow not available, using basic interface")

# Import db_manager and session_manager with fallback
try:
    from src.database.db_manager import db_manager
    from src.auth.session_manager import session_manager
    from src.database.conexion import db_available
    DB_AVAILABLE = db_available
except ImportError:
    print("Warning: DB components not available")
    db_manager: Any = None
    session_manager: Any = None
    DB_AVAILABLE = False

class LoginWindow:
    def __init__(self, on_success_callback=None):
        self.root = tk.Tk()
        self.on_success_callback = on_success_callback
        self.login_successful = False
        self.user_data = None
        
        # Variables
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.remember_var = tk.BooleanVar()
        self.show_password_var = tk.BooleanVar()
        
        self.setup_window()
        self.create_interface()
        self.center_window()
        
        # Load remembered credentials if any
        self.load_remembered_credentials()
        
    def setup_window(self):
        """Configurar ventana principal"""
        self.root.title("MARKET - Sign In")
        
        # Use fixed geometry to avoid locale issues - VENTANA MÁS GRANDE
        self.root.geometry("450x650")  
        self.root.configure(bg="#f0f0f0")
        self.root.resizable(False, False)
        
        # Hacer modal
        self.root.transient()
        self.root.grab_set()
        
        # Protocolo de cierre
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def center_window(self):
        """Centrar ventana en la pantalla - versión segura"""
        try:
            self.root.update_idletasks()
            
            # Fixed dimensions to avoid float calculations - AJUSTADO AL NUEVO TAMAÑO
            width = 450
            height = 650  # Cambié de 600 a 650
            
            # Get screen dimensions and ensure they're integers
            screen_width = int(self.root.winfo_screenwidth())
            screen_height = int(self.root.winfo_screenheight())
            
            # Calculate position with integer division
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            
            # Ensure positive values
            x = max(0, x)
            y = max(0, y)
            
            # Apply geometry with explicit integer values
            self.root.geometry(f'{width}x{height}+{x}+{y}')
            
        except Exception as e:
            print(f"Warning: Could not center window: {e}")
            # Window will appear at default position
        
    def create_interface(self):
        """Crear interfaz de login"""
        # Main container with fixed padding
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Header
        self.create_header(main_frame)
        
        # Login form
        self.create_login_form(main_frame)
        
        # Footer
        self.create_footer(main_frame)
        
    def create_header(self, parent):
        """Crear encabezado"""
        header_frame = tk.Frame(parent, bg="#f0f0f0")
        header_frame.pack(fill="x", pady=(0, 30))
        
        # Logo/Title with safe styling
        title_frame = tk.Frame(header_frame, bg="#2C3E50", relief="raised", bd=2)
        title_frame.pack(fill="x", pady=(0, 20))
        
        # Use fixed padding instead of calculated values
        tk.Label(title_frame, 
                text="MARKET", 
                font=("Arial", 24, "bold"),
                fg="white", 
                bg="#2C3E50",
                pady=20).pack()
        
        tk.Label(title_frame,
                text="Business Management System",
                font=("Arial", 12),
                fg="#BDC3C7",
                bg="#2C3E50",
                pady=15).pack()  # Fixed padding
        
        # Subtitle
        tk.Label(header_frame,
                text="Sign In",
                font=("Arial", 18, "bold"),
                fg="#2C3E50",
                bg="#f0f0f0").pack()
        
    def create_login_form(self, parent):
        """Crear formulario de login"""
        # Form container with fixed styling
        form_frame = tk.Frame(parent, bg="white", relief="raised", bd=2)
        form_frame.pack(fill="x", pady=20, padx=20)
        
        # Inner frame with fixed padding
        inner_frame = tk.Frame(form_frame, bg="white")
        inner_frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Username field
        tk.Label(inner_frame, 
                text="Username:", 
                font=("Arial", 12, "bold"),
                bg="white",
                fg="#2C3E50").pack(anchor="w", pady=(0, 5))
        
        # Use Entry with safe configuration
        self.username_entry = tk.Entry(inner_frame, 
                                     textvariable=self.username_var,
                                     font=("Arial", 12),
                                     relief="solid",
                                     bd=1)
        # Use ipady instead of calculated values
        self.username_entry.pack(fill="x", pady=(0, 15), ipady=8)
        
        # Password field
        tk.Label(inner_frame, 
                text="Password:", 
                font=("Arial", 12, "bold"),
                bg="white",
                fg="#2C3E50").pack(anchor="w", pady=(0, 5))
        
        password_frame = tk.Frame(inner_frame, bg="white")
        password_frame.pack(fill="x", pady=(0, 15))
        
        self.password_entry = tk.Entry(password_frame, 
                                     textvariable=self.password_var,
                                     font=("Arial", 12),
                                     show="*",
                                     relief="solid",
                                     bd=1)
        self.password_entry.pack(side="left", fill="x", expand=True, ipady=8)
        
        # Show/Hide password button - simplified
        self.show_pass_btn = tk.Button(password_frame,
                                     text="👁",
                                     font=("Arial", 10),
                                     command=self.toggle_password_visibility,
                                     relief="flat",
                                     bg="white",
                                     fg="#7F8C8D",
                                     cursor="hand2",
                                     bd=0,
                                     width=3)
        self.show_pass_btn.pack(side="right", padx=(5, 0))
        
        # Remember me checkbox
        remember_frame = tk.Frame(inner_frame, bg="white")
        remember_frame.pack(fill="x", pady=(0, 20))
        
        tk.Checkbutton(remember_frame,
                      text="Remember credentials",
                      variable=self.remember_var,
                      font=("Arial", 10),
                      bg="white",
                      fg="#7F8C8D",
                      activebackground="white").pack(side="left")
        
        # Login button - SOLO UN BOTÓN AZUL
        self.login_btn = tk.Button(inner_frame,
                                 text="SIGN IN",
                                 command=self.handle_login,
                                 font=("Arial", 12, "bold"),
                                 bg="#3498DB",
                                 fg="white",
                                 relief="flat",
                                 cursor="hand2",
                                 pady=12)
        self.login_btn.pack(fill="x", pady=(0, 10))
        
        # Status label
        self.status_var = tk.StringVar()
        self.status_label = tk.Label(inner_frame,
                                   textvariable=self.status_var,
                                   font=("Arial", 10),
                                   bg="white",
                                   fg="#E74C3C",
                                   wraplength=300)
        self.status_label.pack(pady=(10, 0))
        
        # Bind Enter key
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())
        self.password_entry.bind("<Return>", lambda e: self.handle_login())
        
        # Set initial focus
        self.username_entry.focus_set()
        
    def create_footer(self, parent):
        """Crear pie de página"""
        footer_frame = tk.Frame(parent, bg="#f0f0f0")
        footer_frame.pack(fill="x", pady=(20, 0))
        
        # System info
        tk.Label(footer_frame,
                text="Secure Authentication System",
                font=("Arial", 9),
                fg="#7F8C8D",
                bg="#f0f0f0").pack()
        
        tk.Label(footer_frame,
                text=f"© {datetime.now().year} MARKET",
                font=("Arial", 8),
                fg="#BDC3C7",
                bg="#f0f0f0").pack(pady=(5, 0))
        
    def toggle_password_visibility(self):
        """Alternar visibilidad de contraseña"""
        if self.show_password_var.get():
            self.password_entry.config(show="")
            self.show_pass_btn.config(text="🙈")
            self.show_password_var.set(False)
        else:
            self.password_entry.config(show="*")
            self.show_pass_btn.config(text="👁")
            self.show_password_var.set(True)
    
    def handle_login(self):
        """Manejar intento de login"""
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        
        # Validaciones básicas
        if not username:
            self.show_error("Please, enter your username")
            self.username_entry.focus_set()
            return
            
        if not password:
            self.show_error("Please, ingrese su contraseña")
            self.password_entry.focus_set()
            return
        
        # Deshabilitar botón y mostrar progreso
        self.login_btn.config(state="disabled", text="VERIFYING...")
        self.status_var.set("Verifying credentials...")
        self.root.update()
        
        # Realizar autenticación en hilo separado
        auth_thread = threading.Thread(target=self.authenticate_user, args=(username, password))
        auth_thread.daemon = True
        auth_thread.start()
    
    def authenticate_user(self, username, password):
        """Autenticar usuario (ejecutado en hilo separado)"""
        try:
            if DB_AVAILABLE and db_manager is not None:
                # Intentar autenticación real
                result = db_manager.authenticate_and_connect(username, password)
            else:
                # Simulación para pruebas
                if username in ['valeria', 'test'] and password:
                    result = {
                        'success': True,
                        'user_data': {
                            'username': username,
                            'nombre_completo': f'{username.title()} (Administrador)',
                            'rol': 'admin'
                        }
                    }
                else:
                    result = {
                        'success': False,
                        'message': 'Incorrect credentials'
                    }
            
            # Volver al hilo principal para actualizar UI
            self.root.after(0, self.handle_auth_result, result)
            
        except Exception as e:
            error_result = {
                'success': False,
                'message': f'Connection error: {str(e)}'
            }
            self.root.after(0, self.handle_auth_result, error_result)
    
    def handle_auth_result(self, result):
        """Manejar resultado de autenticación"""
        # Rehabilitar botón
        self.login_btn.config(state="normal", text="SIGN IN")
        
        if result['success']:
            self.user_data = result['user_data']
            
            # Iniciar sesión en session manager si está disponible
            if DB_AVAILABLE and session_manager is not None:
                session_manager.start_session(self.user_data)
            
            # Guardar credenciales si está marcado
            if self.remember_var.get():
                self.save_credentials()
            else:
                self.clear_saved_credentials()
            
            self.show_success(f"Welcome, {self.user_data['nombre_completo']}!")
            
            # Esperar un momento y cerrar
            self.root.after(1500, self.close_with_success)
            
        else:
            self.show_error(result['message'])
            
            # Manejar bloqueo especial
            if result.get('blocked', False):
                self.login_btn.config(state="disabled")
                # Rehabilitar después del tiempo de bloqueo
                if 'blocked_until' in result:
                    self.schedule_unblock(result['blocked_until'])
    
    def schedule_unblock(self, blocked_until):
        """Programar desbloqueo del botón de login"""
        from datetime import datetime
        
        def check_unblock():
            if datetime.now() >= blocked_until:
                self.login_btn.config(state="normal")
                self.status_var.set("")
            else:
                remaining = blocked_until - datetime.now()
                minutes = int(remaining.total_seconds() / 60)
                self.status_var.set(f"User blocked. Time remaining: {minutes} min")
                self.root.after(60000, check_unblock)  # Verificar cada minuto
        
        check_unblock()
    
    def show_error(self, message):
        """Mostrar mensaje de error"""
        self.status_var.set(message)
        self.status_label.config(fg="#E74C3C")
        
        # Limpiar después de unos segundos
        self.root.after(5000, lambda: self.status_var.set(""))
    
    def show_success(self, message):
        """Mostrar mensaje de éxito"""
        self.status_var.set(message)
        self.status_label.config(fg="#27AE60")
    
    def close_with_success(self):
        """Cerrar ventana con éxito"""
        self.login_successful = True
        
        if self.on_success_callback:
            self.on_success_callback(self.user_data)
        
        self.root.destroy()
    
    def save_credentials(self):
        """Guardar credenciales (solo username)"""
        try:
            with open(".market_remember", "w") as f:
                f.write(self.username_var.get())
        except:
            pass  # No es crítico si falla
    
    def load_remembered_credentials(self):
        """Cargar credenciales guardadas"""
        try:
            with open(".market_remember", "r") as f:
                username = f.read().strip()
                if username:
                    self.username_var.set(username)
                    self.remember_var.set(True)
                    self.password_entry.focus_set()
        except:
            pass  # No hay credenciales guardadas
    
    def clear_saved_credentials(self):
        """Limpiar credenciales guardadas"""
        try:
            if os.path.exists(".market_remember"):
                os.remove(".market_remember")
        except:
            pass
    
    def on_closing(self):
        """Manejar cierre de ventana"""
        if not self.login_successful:
            # Usuario canceló el login
            self.root.quit()
        else:
            self.root.destroy()
    
    def run(self):
        """Ejecutar ventana de login"""
        self.root.mainloop()
        return self.login_successful, self.user_data

def show_login(on_success_callback=None):
    """
    Función de conveniencia para mostrar ventana de login
    
    Returns:
        tuple: (success: bool, user_data: dict)
    """
    login_window = LoginWindow(on_success_callback)
    return login_window.run()

if __name__ == "__main__":
    # Test the login window
    success, user_data = show_login()
    if success:
        print(f"Login successful: {user_data}")
    else:
        print("Login cancelled or failed")