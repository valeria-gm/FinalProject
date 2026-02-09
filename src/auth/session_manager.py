import tkinter as tk
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
import threading
import time

class SessionManager:
    """
    Gestión de sesiones de usuario con timeout automático
    """
    
    def __init__(self, timeout_minutes: int = 30):
        self.timeout_minutes = timeout_minutes
        self.current_user = None
        self.login_time = None
        self.last_activity = None
        self.session_callbacks = []
        self.timeout_timer = None
        self.session_active = False
        
    def start_session(self, user_data: Dict[str, Any]):
        """Iniciar sesión de usuario"""
        self.current_user = user_data
        self.login_time = datetime.now()
        self.last_activity = datetime.now()
        self.session_active = True
        
        # Iniciar timer de timeout
        self._start_timeout_timer()
        
        # Notificar callbacks
        self._notify_callbacks('session_started', user_data)
    
    def end_session(self):
        """Terminar sesión actual"""
        if self.session_active:
            user_data = self.current_user
            
            # Limpiar datos de sesión
            self.current_user = None
            self.login_time = None
            self.last_activity = None
            self.session_active = False
            
            # Cancelar timer
            if self.timeout_timer:
                self.timeout_timer.cancel()
                self.timeout_timer = None
            
            # Notificar callbacks
            self._notify_callbacks('session_ended', user_data)
    
    def update_activity(self):
        """Actualizar timestamp de última actividad"""
        if self.session_active:
            self.last_activity = datetime.now()
            
            # Reiniciar timer de timeout
            self._start_timeout_timer()
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Obtener usuario actual"""
        return self.current_user if self.session_active else None
    
    def is_active(self) -> bool:
        """Verificar si hay sesión activa"""
        return self.session_active and self.current_user is not None
    
    def get_session_duration(self) -> Optional[timedelta]:
        """Obtener duración de la sesión actual"""
        if self.login_time:
            return datetime.now() - self.login_time
        return None
    
    def get_time_until_timeout(self) -> Optional[timedelta]:
        """Obtener tiempo restante hasta timeout"""
        if not self.session_active or not self.last_activity:
            return None
        
        timeout_time = self.last_activity + timedelta(minutes=self.timeout_minutes)
        remaining = timeout_time - datetime.now()
        
        return remaining if remaining.total_seconds() > 0 else timedelta(0)
    
    def add_callback(self, callback: Callable):
        """
        Agregar callback para eventos de sesión
        
        callback signature: callback(event_type: str, user_data: dict)
        event_types: 'session_started', 'session_ended', 'session_timeout'
        """
        self.session_callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """Remover callback"""
        if callback in self.session_callbacks:
            self.session_callbacks.remove(callback)
    
    def _notify_callbacks(self, event_type: str, user_data: Dict[str, Any]):
        """Notificar a todos los callbacks registrados"""
        for callback in self.session_callbacks:
            try:
                callback(event_type, user_data)
            except Exception as e:
                print(f"Error in session callback: {e}")
    
    def _start_timeout_timer(self):
        """Iniciar/reiniciar timer de timeout"""
        # Cancelar timer anterior si existe
        if self.timeout_timer:
            self.timeout_timer.cancel()
        
        # Crear nuevo timer
        timeout_seconds = self.timeout_minutes * 60
        self.timeout_timer = threading.Timer(timeout_seconds, self._handle_timeout)
        self.timeout_timer.daemon = True
        self.timeout_timer.start()
    
    def _handle_timeout(self):
        """Manejar timeout de sesión"""
        if self.session_active:
            user_data = self.current_user
            self.end_session()
            self._notify_callbacks('session_timeout', user_data)

# Instancia global del gestor de sesiones
session_manager = SessionManager()

class SessionAwareWidget:
    """
    Mixin class para widgets que necesitan estar al tanto de la sesión
    """
    
    def __init__(self):
        self.session_callback_registered = False
        
    def register_session_callback(self):
        """Registrar callback de sesión"""
        if not self.session_callback_registered:
            session_manager.add_callback(self._handle_session_event)
            self.session_callback_registered = True
    
    def unregister_session_callback(self):
        """Desregistrar callback de sesión"""
        if self.session_callback_registered:
            session_manager.remove_callback(self._handle_session_event)
            self.session_callback_registered = False
    
    def _handle_session_event(self, event_type: str, user_data: dict):
        """
        Manejar eventos de sesión - debe ser implementado por subclases
        """
        pass
    
    def update_session_activity(self):
        """Actualizar actividad de sesión"""
        session_manager.update_activity()

class SessionStatusBar(tk.Frame, SessionAwareWidget):
    """
    Barra de estado que muestra información de sesión
    """
    
    def __init__(self, parent):
        tk.Frame.__init__(self, parent, relief=tk.SUNKEN, bd=1)
        SessionAwareWidget.__init__(self)
        
        # Variables
        self.user_var = tk.StringVar()
        self.time_var = tk.StringVar()
        
        # Layout
        self.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Labels
        self.user_label = tk.Label(self, textvariable=self.user_var, anchor=tk.W)
        self.user_label.pack(side=tk.LEFT, padx=5)
        
        self.time_label = tk.Label(self, textvariable=self.time_var, anchor=tk.E)
        self.time_label.pack(side=tk.RIGHT, padx=5)
        
        # Registrar callback y iniciar actualización
        self.register_session_callback()
        self._update_display()
        self._start_update_timer()
    
    def _handle_session_event(self, event_type: str, user_data: dict):
        """Manejar eventos de sesión"""
        if event_type in ['session_started', 'session_ended', 'session_timeout']:
            self._update_display()
    
    def _update_display(self):
        """Actualizar display de información"""
        user = session_manager.get_current_user()
        
        if user:
            self.user_var.set(f"Usuario: {user['nombre_completo']} ({user['rol']})")
            
            # Tiempo hasta timeout
            time_remaining = session_manager.get_time_until_timeout()
            if time_remaining:
                minutes = int(time_remaining.total_seconds() / 60)
                self.time_var.set(f"Sesión expira en {minutes} min")
            else:
                self.time_var.set("Sesión expirada")
        else:
            self.user_var.set("No hay usuario autenticado")
            self.time_var.set("")
    
    def _start_update_timer(self):
        """Iniciar timer para actualizar display"""
        self._update_display()
        # Actualizar cada minuto
        self.after(60000, self._start_update_timer)
    
    def destroy(self):
        """Cleanup al destruir widget"""
        self.unregister_session_callback()
        super().destroy()

def require_authentication(func):
    """
    Decorador para funciones que requieren autenticación
    """
    def wrapper(*args, **kwargs):
        if not session_manager.is_active():
            raise Exception("Función requiere autenticación. Por favor, inicie sesión.")
        
        # Actualizar actividad
        session_manager.update_activity()
        
        return func(*args, **kwargs)
    
    return wrapper

def get_current_user():
    """Obtener usuario actual de la sesión"""
    return session_manager.get_current_user()

def is_authenticated():
    """Verificar si hay usuario autenticado"""
    return session_manager.is_active()

def logout():
    """Cerrar sesión actual"""
    session_manager.end_session()