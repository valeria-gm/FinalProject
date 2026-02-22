import bcrypt
import mysql.connector
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, cast
import hashlib

# Importar configuración de base de datos local`
from src.database.cloud_config import get_db_config

class AuthManager:
    def __init__(self, db_host=None, db_name=None):
        # Usar configuración local de base de datos
        self.db_config = get_db_config()
        self.max_intentos = 3
        self.bloqueo_minutos = 15
        
    def _get_admin_connection(self):
        """Obtener conexión administrativa para validar usuarios"""
        try:
            # Usar configuración local de MySQL
            conn = cast(mysql.connector.MySQLConnection, mysql.connector.connect(**self.db_config))
            return conn
        except mysql.connector.Error as e:
            raise Exception(f"Administrative connection error: {e}")
    
    def _hash_password(self, password: str) -> str:
        """Generar hash seguro de contraseña"""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verificar contraseña contra hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False
    
    def _log_access_attempt(self, username: str, success: bool, detail: str = ""):
        """Registrar intento de acceso"""
        try:
            conn = self._get_admin_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO log_accesos (username_intento, exito, detalle)
                VALUES (%s, %s, %s)
            """, (username, success, detail))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging access attempt: {e}")
    
    def _check_user_blocked(self, username: str) -> tuple[bool, Optional[datetime]]:
        """Verificar si usuario está bloqueado"""
        try:
            conn = self._get_admin_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT bloqueado_hasta, intentos_fallidos 
                FROM usuarios_sistema 
                WHERE username = %s
            """, (username,))
            
            result = cast(Optional[Dict[str, Any]], cursor.fetchone())
            conn.close()
            
            if not result:
                return False, None
                
            if result['bloqueado_hasta'] and result['bloqueado_hasta'] > datetime.now():
                return True, result['bloqueado_hasta']
                
            return False, None
            
        except Exception as e:
            print(f"Error checking user blocked status: {e}")
            return False, None
    
    def _increment_failed_attempts(self, username: str):
        """Incrementar intentos fallidos y bloquear si es necesario"""
        try:
            conn = self._get_admin_connection()
            cursor = conn.cursor()
            
            # Incrementar intentos fallidos
            cursor.execute("""
                UPDATE usuarios_sistema 
                SET intentos_fallidos = intentos_fallidos + 1
                WHERE username = %s
            """, (username,))
            
            # Verificar si debe bloquearse
            cursor.execute("""
                SELECT intentos_fallidos 
                FROM usuarios_sistema 
                WHERE username = %s
            """, (username,))
            
            result = cast(Optional[tuple], cursor.fetchone())
            if result and result[0] >= self.max_intentos:
                # Bloquear usuario
                bloqueo_hasta = datetime.now() + timedelta(minutes=self.bloqueo_minutos)
                cursor.execute("""
                    UPDATE usuarios_sistema 
                    SET bloqueado_hasta = %s, intentos_fallidos = 0
                    WHERE username = %s
                """, (bloqueo_hasta, username))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error incrementing failed attempts: {e}")
    
    def _reset_failed_attempts(self, username: str):
        """Resetear intentos fallidos tras login exitoso"""
        try:
            conn = self._get_admin_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE usuarios_sistema 
                SET intentos_fallidos = 0, bloqueado_hasta = NULL, ultimo_acceso = NOW()
                WHERE username = %s
            """, (username,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error resetting failed attempts: {e}")
    
    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """
        Autenticar usuario
        
        Returns:
            Dict con 'success', 'message', 'user_data' (si exitoso)
        """
        try:
            # Verificar si usuario está bloqueado
            is_blocked, blocked_until = self._check_user_blocked(username)
            if is_blocked and blocked_until is not None:
                remaining_time = blocked_until - datetime.now()
                minutes = int(remaining_time.total_seconds() / 60)
                message = f"Blocked user. Remaining time: {minutes} minutes"
                
                self._log_access_attempt(username, False, "Blocked user")
                return {
                    'success': False,
                    'message': message,
                    'blocked': True,
                    'blocked_until': blocked_until
                }
            
            # Obtener datos del usuario
            conn = self._get_admin_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT id_usuario, username, password_hash, nombre_completo, rol, activo
                FROM usuarios_sistema 
                WHERE username = %s
            """, (username,))
            
            user = cast(Optional[Dict[str, Any]], cursor.fetchone())
            conn.close()
            
            if not user:
                self._log_access_attempt(username, False, "User does not exist")
                return {
                    'success': False,
                    'message': "Incorrect user or password"
                }
            
            if not user['activo']:
                self._log_access_attempt(username, False, "Inactive user")
                return {
                    'success': False,
                    'message': "Inactive user. Please contact the administrator."
                }
            
            # Verificar contraseña
            if not self._verify_password(password, user['password_hash']):
                self._increment_failed_attempts(username)
                self._log_access_attempt(username, False, "Incorrect password")
                return {
                    'success': False,
                    'message': "Incorrect user or password"
                }
            
            # Login exitoso
            self._reset_failed_attempts(username)
            self._log_access_attempt(username, True, "Successful login")
            
            # Remover información sensible
            user_data = {
                'id_usuario': user['id_usuario'],
                'username': user['username'],
                'nombre_completo': user['nombre_completo'],
                'rol': user['rol']
            }
            
            return {
                'success': True,
                'message': "Sucessful authentication",
                'user_data': user_data
            }
            
        except Exception as e:
            self._log_access_attempt(username, False, f"System error: {str(e)}")
            return {
                'success': False,
                'message': "System error. Please try again"
            }
    
    def create_user_connection(self, username: str, password: str) -> mysql.connector.MySQLConnection:
        """
        Crear conexión a MySQL usando credenciales del usuario
        """
        try:
            # Primero verificar si el usuario ya está autenticado en nuestro sistema
            auth_result = self.authenticate(username, password)
            if not auth_result['success']:
                raise Exception(auth_result['message'])
            
            # Usar las credenciales de MySQL local para todos los usuarios
            # Los usuarios de la aplicación se autentican contra la tabla usuarios_sistema
            conn = cast(mysql.connector.MySQLConnection, mysql.connector.connect(**self.db_config))
            
            return conn
            
        except mysql.connector.Error as e:
            raise Exception(f"Database connection error: {e}")
    
    def change_password(self, username: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """Cambiar contraseña de usuario"""
        try:
            # Verificar contraseña actual
            auth_result = self.authenticate(username, old_password)
            if not auth_result['success']:
                return {
                    'success': False,
                    'message': "Incorrect password"
                }
            
            # Validar nueva contraseña
            if len(new_password) < 8:
                return {
                    'success': False,
                    'message': "The new password must be at least 8 characters long"
                }
            
            # Generar hash de nueva contraseña
            new_hash = self._hash_password(new_password)
            
            # Actualizar en base de datos
            conn = self._get_admin_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE usuarios_sistema 
                SET password_hash = %s
                WHERE username = %s
            """, (new_hash, username))
            
            conn.commit()
            conn.close()
            
            self._log_access_attempt(username, True, "Password updated")
            
            return {
                'success': True,
                'message': "Password updated successfully"
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error changing password: {str(e)}"
            }
    
    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Obtener información del usuario"""
        try:
            conn = self._get_admin_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT id_usuario, username, nombre_completo, rol, activo, ultimo_acceso
                FROM usuarios_sistema 
                WHERE username = %s
            """, (username,))
            
            user = cast(Optional[Dict[str, Any]], cursor.fetchone())
            conn.close()
            
            return user
            
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None
    
    def get_user_info_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Obtener información del usuario por ID"""
        try:
            conn = self._get_admin_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT id_usuario, username, nombre_completo, rol, activo, ultimo_acceso
                FROM usuarios_sistema 
                WHERE id_usuario = %s
            """, (user_id,))
            
            user = cast(Optional[Dict[str, Any]], cursor.fetchone())
            conn.close()
            
            return user
            
        except Exception as e:
            print(f"Error getting user info by ID: {e}")
            return None
    
    def create_user(self, username: str, password: str, nombre_completo: str, rol: str = 'usuario') -> Dict[str, Any]:
        """Crear nuevo usuario"""
        try:
            # Validar datos de entrada
            if not username or not password or not nombre_completo:
                return {
                    'success': False,
                    'message': 'All fields are required'
                }
            
            if len(password) < 8:
                return {
                    'success': False,
                    'message': 'The password must be at least 8 characters long'
                }
            
            if rol not in ['admin', 'usuario']:
                return {
                    'success': False,
                    'message': 'Invalid rol'
                }
            
            # Verificar si el usuario ya existe
            conn = self._get_admin_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT username FROM usuarios_sistema WHERE username = %s", (username,))
            if cursor.fetchone():
                conn.close()
                return {
                    'success': False,
                    'message': f'The user "{username}" already exists'
                }
            
            # Generar hash de contraseña
            password_hash = self._hash_password(password)
            
            # Insertar nuevo usuario
            cursor.execute("""
                INSERT INTO usuarios_sistema (username, password_hash, nombre_completo, rol, activo)
                VALUES (%s, %s, %s, %s, %s)
            """, (username, password_hash, nombre_completo, rol, True))
            
            conn.commit()
            conn.close()
            
            self._log_access_attempt(username, True, f"User created by administrator")
            
            return {
                'success': True,
                'message': f'User "{username}" created successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error creating user: {str(e)}'
            }
    
    def update_user(self, username: str, nombre_completo: str, rol: str, activo: bool, new_password: Optional[str] = None) -> Dict[str, Any]:
        """Actualizar usuario existente"""
        try:
            # Validar datos de entrada
            if not username or not nombre_completo:
                return {
                    'success': False,
                    'message': 'Username and name are required'
                }
            
            if rol not in ['admin', 'usuario']:
                return {
                    'success': False,
                    'message': 'Invalid rol'
                }
            
            conn = self._get_admin_connection()
            cursor = conn.cursor()
            
            # Verificar que el usuario existe
            cursor.execute("SELECT id_usuario FROM usuarios_sistema WHERE username = %s", (username,))
            if not cursor.fetchone():
                conn.close()
                return {
                    'success': False,
                    'message': f'The user "{username}" does not exist'
                }
            
            # Actualizar usuario
            if new_password:
                if len(new_password) < 8:
                    conn.close()
                    return {
                        'success': False,
                        'message': 'The new password must be at least 8 characters long'
                    }
                
                password_hash = self._hash_password(new_password)
                cursor.execute("""
                    UPDATE usuarios_sistema 
                    SET nombre_completo = %s, rol = %s, activo = %s, password_hash = %s
                    WHERE username = %s
                """, (nombre_completo, rol, activo, password_hash, username))
            else:
                cursor.execute("""
                    UPDATE usuarios_sistema 
                    SET nombre_completo = %s, rol = %s, activo = %s
                    WHERE username = %s
                """, (nombre_completo, rol, activo, username))
            
            conn.commit()
            conn.close()
            
            action_detail = "User updated by administrator"
            if new_password:
                action_detail += " (password updated)"
            
            self._log_access_attempt(username, True, action_detail)
            
            return {
                'success': True,
                'message': f'User "{username}" updated successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error updating user: {str(e)}'
            }