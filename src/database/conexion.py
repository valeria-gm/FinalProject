import mysql.connector
from mysql.connector import Error
from .cloud_config import get_db_config

# Variable global para estado de disponibilidad
db_available = False

def verify_db_availability():
    global db_available
    try:
        conn = conectar()
        if conn and conn.is_connected():
            db_available = True
            conn.close()
        return db_available
    except:
        return False

def conectar():
    try:
        config = get_db_config()
        
        print(f"Connecting to: Local MySQL")
        print(f"Host: {config['host']}")
        
        conn = mysql.connector.connect(**config)
        
        if conn.is_connected():
            print("Successfully connected to the database")
        
        return conn
        
    except Error as e:
        print(f"Connection error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

# Verificar disponibilidad al importar
verify_db_availability()