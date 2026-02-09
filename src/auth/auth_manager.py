import bcrypt
import mysql.connector
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import hashlib

# Importar configuración de Cloud SQL
from src.database.cloud_config import get_db_config

class AuthManager:
    def __init__(self, db_host=None, db_name=None):
        # Usar configuración de cloud_config en lugar de parámetros hardcodeados
        self.db_config = get_db_config()
        self.max_intentos = 3
        self.bloqueo_minutos = 15
        
    def _get_admin_connection(self):
        """Obtener conexión administrativa para validar usuarios"""
        try:
            # Usar configuración desde .env (Cloud SQL o local)
            conn = mysql.connector.connect(**self.db_config)
            return conn
        except mysql.connector.Error as e:
            raise Exception(f"Error de conexión administrativa: {e}")
    
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
            
            result = cursor.fetchone()
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
            
            result = cursor.fetchone()
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
            if is_blocked:
                remaining_time = blocked_until - datetime.now()
                minutes = int(remaining_time.total_seconds() / 60)
                message = f"Usuario bloqueado. Tiempo restante: {minutes} minutos"
                
                self._log_access_attempt(username, False, "Usuario bloqueado")
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
            
            user = cursor.fetchone()
            conn.close()
            
            if not user:
                self._log_access_attempt(username, False, "Usuario no existe")
                return {
                    'success': False,
                    'message': "Usuario o contraseña incorrectos"
                }
            
            if not user['activo']:
                self._log_access_attempt(username, False, "Usuario inactivo")
                return {
                    'success': False,
                    'message': "Usuario inactivo. Contacte al administrador."
                }
            
            # Verificar contraseña
            if not self._verify_password(password, user['password_hash']):
                self._increment_failed_attempts(username)
                self._log_access_attempt(username, False, "Contraseña incorrecta")
                return {
                    'success': False,
                    'message': "Usuario o contraseña incorrectos"
                }
            
            # Login exitoso
            self._reset_failed_attempts(username)
            self._log_access_attempt(username, True, "Login exitoso")
            
            # Remover información sensible
            user_data = {
                'id_usuario': user['id_usuario'],
                'username': user['username'],
                'nombre_completo': user['nombre_completo'],
                'rol': user['rol']
            }
            
            return {
                'success': True,
                'message': "Autenticación exitosa",
                'user_data': user_data
            }
            
        except Exception as e:
            self._log_access_attempt(username, False, f"Error del sistema: {str(e)}")
            return {
                'success': False,
                'message': "Error del sistema. Intente nuevamente."
            }
    
    def create_user_connection(self, username: str, password: str) -> mysql.connector.MySQLConnection:
        """
        Crear conexión a MySQL usando credenciales del usuario
        Ahora usa la configuración de Cloud SQL
        """
        try:
            # Primero verificar si el usuario ya está autenticado en nuestro sistema
            auth_result = self.authenticate(username, password)
            if not auth_result['success']:
                raise Exception(auth_result['message'])
            
            # Usar las credenciales de Cloud SQL para todos los usuarios
            # Los usuarios de la aplicación se autentican contra la tabla usuarios_sistema
            # pero las conexiones a MySQL usan las credenciales de Cloud SQL
            conn = mysql.connector.connect(**self.db_config)
            
            return conn
            
        except mysql.connector.Error as e:
            raise Exception(f"Error de conexión a base de datos: {e}")
    
    def change_password(self, username: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """Cambiar contraseña de usuario"""
        try:
            # Verificar contraseña actual
            auth_result = self.authenticate(username, old_password)
            if not auth_result['success']:
                return {
                    'success': False,
                    'message': "Contraseña actual incorrecta"
                }
            
            # Validar nueva contraseña
            if len(new_password) < 8:
                return {
                    'success': False,
                    'message': "La nueva contraseña debe tener al menos 8 caracteres"
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
            
            self._log_access_attempt(username, True, "Contraseña cambiada")
            
            return {
                'success': True,
                'message': "Contraseña actualizada exitosamente"
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error al cambiar contraseña: {str(e)}"
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
            
            user = cursor.fetchone()
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
            
            user = cursor.fetchone()
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
                    'message': 'Todos los campos son requeridos'
                }
            
            if len(password) < 8:
                return {
                    'success': False,
                    'message': 'La contraseña debe tener al menos 8 caracteres'
                }
            
            if rol not in ['admin', 'usuario']:
                return {
                    'success': False,
                    'message': 'Rol inválido'
                }
            
            # Verificar si el usuario ya existe
            conn = self._get_admin_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT username FROM usuarios_sistema WHERE username = %s", (username,))
            if cursor.fetchone():
                conn.close()
                return {
                    'success': False,
                    'message': f'El usuario "{username}" ya existe'
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
            
            self._log_access_attempt(username, True, f"Usuario creado por administrador")
            
            return {
                'success': True,
                'message': f'Usuario "{username}" creado exitosamente'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error al crear usuario: {str(e)}'
            }
    
    def update_user(self, username: str, nombre_completo: str, rol: str, activo: bool, new_password: str = None) -> Dict[str, Any]:
        """Actualizar usuario existente"""
        try:
            # Validar datos de entrada
            if not username or not nombre_completo:
                return {
                    'success': False,
                    'message': 'Username y nombre completo son requeridos'
                }
            
            if rol not in ['admin', 'usuario']:
                return {
                    'success': False,
                    'message': 'Rol inválido'
                }
            
            conn = self._get_admin_connection()
            cursor = conn.cursor()
            
            # Verificar que el usuario existe
            cursor.execute("SELECT id_usuario FROM usuarios_sistema WHERE username = %s", (username,))
            if not cursor.fetchone():
                conn.close()
                return {
                    'success': False,
                    'message': f'El usuario "{username}" no existe'
                }
            
            # Actualizar usuario
            if new_password:
                if len(new_password) < 8:
                    conn.close()
                    return {
                        'success': False,
                        'message': 'La nueva contraseña debe tener al menos 8 caracteres'
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
            
            action_detail = "Usuario actualizado por administrador"
            if new_password:
                action_detail += " (contraseña cambiada)"
            
            self._log_access_attempt(username, True, action_detail)
            
            return {
                'success': True,
                'message': f'Usuario "{username}" actualizado exitosamente'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error al actualizar usuario: {str(e)}'
            }