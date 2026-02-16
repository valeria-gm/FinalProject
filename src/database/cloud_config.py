# Configuración de base de datos MySQL local

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'market_user',
    'password': 'm4rK3t!!!',
    'database': 'market',
    'auth_plugin': 'mysql_native_password',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

def get_db_config():
    """Obtener configuración de base de datos local"""
    return DB_CONFIG.copy()

def is_cloud_sql():
    """Siempre retorna False — conexión exclusivamente local"""
    return False