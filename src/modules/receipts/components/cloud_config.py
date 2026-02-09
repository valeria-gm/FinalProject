import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de base de datos
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'Jared'),
    'password': os.getenv('DB_PASSWORD', 'Zoi.1.J0t0'),
    'database': os.getenv('DB_NAME', 'disfruleg'),
    'auth_plugin': 'mysql_native_password',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

def get_db_config():
    """Obtener configuración de base de datos"""
    return DB_CONFIG.copy()

def is_cloud_sql():
    """Verificar si estamos usando Cloud SQL"""
    return os.getenv('DB_HOST') != 'localhost' and os.getenv('DB_HOST') is not None