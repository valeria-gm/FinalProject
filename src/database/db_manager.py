import mysql.connector
from typing import Optional
from src.auth.auth_manager import AuthManager
from .cloud_config import get_db_config

class DatabaseManager:
    """
    Gestor centralizado de conexiones a base de datos
    Mantiene compatibilidad con el sistema existente
    """
    
    def __init__(self):
        self.auth_manager = AuthManager()
        self.current_user = None
        self.current_connection = None
    
    def authenticate_and_connect(self, username: str, password: str) -> dict:
        """
        Autenticar usuario y establecer conexión
        
        Returns:
            dict: {'success': bool, 'message': str, 'user_data': dict}
        """
        try:
            # Autenticar usuario
            auth_result = self.auth_manager.authenticate(username, password)
            
            if auth_result['success']:
                # Crear conexión para el usuario autenticado
                self.current_connection = self.auth_manager.create_user_connection(username, password)
                self.current_user = auth_result['user_data']
                
                return {
                    'success': True,
                    'message': 'Conexión establecida exitosamente',
                    'user_data': self.current_user
                }
            else:
                return auth_result
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Error de conexión: {str(e)}'
            }
    
    def get_connection(self) -> Optional[mysql.connector.MySQLConnection]:
        """
        Obtener conexión actual del usuario autenticado
        """
        if not self.current_connection:
            raise Exception("No hay usuario autenticado. Debe hacer login primero.")
        
        # Verificar que la conexión sigue activa
        try:
            self.current_connection.ping(reconnect=True, attempts=3, delay=0)
            return self.current_connection
        except mysql.connector.Error:
            # Reconectar si es necesario
            if self.current_user:
                # Intentar reconectar (necesitaríamos almacenar credenciales o manejar de otra forma)
                raise Exception("Conexión perdida. Por favor, inicie sesión nuevamente.")
            else:
                raise Exception("No hay usuario autenticado.")
    
    def get_cursor(self, dictionary: bool = True):
        """
        Obtener cursor de la conexión actual
        """
        conn = self.get_connection()
        return conn.cursor(dictionary=dictionary)
    
    def close_connection(self):
        """
        Cerrar conexión actual
        """
        if self.current_connection:
            try:
                self.current_connection.close()
            except:
                pass
            finally:
                self.current_connection = None
                self.current_user = None
    
    def get_current_user(self) -> Optional[dict]:
        """
        Obtener información del usuario actual
        """
        return self.current_user
    
    def is_authenticated(self) -> bool:
        """
        Verificar si hay un usuario autenticado
        """
        return self.current_user is not None and self.current_connection is not None
    
    def change_password(self, old_password: str, new_password: str) -> dict:
        """
        Cambiar contraseña del usuario actual
        """
        if not self.current_user:
            return {
                'success': False,
                'message': 'No hay usuario autenticado'
            }
        
        return self.auth_manager.change_password(
            self.current_user['username'], 
            old_password, 
            new_password
        )

# Instancia global para uso en toda la aplicación
db_manager = DatabaseManager()

# Funciones de compatibilidad con el sistema existente
def conectar():
    """
    Función de compatibilidad con conexion.py
    DEPRECADA: Usar db_manager.get_connection() en su lugar
    """
    if db_manager.is_authenticated():
        return db_manager.get_connection()
    else:
        # Para compatibilidad temporal, usar configuración desde .env
        config = get_db_config()
        return mysql.connector.connect(**config)

def get_authenticated_connection():
    """
    Obtener conexión del usuario autenticado
    Lanza excepción si no hay usuario autenticado
    """
    return db_manager.get_connection()

def get_current_user():
    """
    Obtener información del usuario actual
    """
    return db_manager.get_current_user()

def is_user_authenticated():
    """
    Verificar si hay usuario autenticado
    """
    return db_manager.is_authenticated()

def logout():
    """
    Cerrar sesión del usuario actual
    """
    db_manager.close_connection()