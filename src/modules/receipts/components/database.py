# Módulo actualizado para interactuar con la base de datos 'disfruleg' con nueva estructura - CORREGIDO

import mysql.connector
from mysql.connector import Error
import bcrypt  # Para el manejo seguro de contraseñas
from datetime import date
import json

# --- CONFIGURACIÓN DE CONEXIÓN A GOOGLE CLOUD SQL ---
try:
    # Intentar importación local primero
    from cloud_config import get_db_config, is_cloud_sql
except ImportError:
    try:
        # Intentar importación desde el directorio principal
        from src.database.cloud_config import get_db_config, is_cloud_sql
    except ImportError:
        # Fallback: usar configuración directa desde variables de entorno
        import os
        from dotenv import load_dotenv
        
        # Cargar .env desde la raíz del proyecto
        env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path)
        else:
            load_dotenv()  # Buscar .env en directorio actual y padres
        
        def get_db_config():
            return {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': int(os.getenv('DB_PORT', 3306)),
                'user': os.getenv('DB_USER', 'root'),
                'password': os.getenv('DB_PASSWORD', ''),
                'database': os.getenv('DB_NAME', 'disfruleg'),
                'auth_plugin': 'mysql_native_password',
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci'
            }
        
        def is_cloud_sql():
            return os.getenv('DB_HOST') != 'localhost' and os.getenv('DB_HOST') is not None
        
        print("⚠️ Usando configuración directa de variables de entorno")

# Obtener configuración de la base de datos
db_config = get_db_config()

def conectar():
    """Establece la conexión a la base de datos."""
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
        return None

# --- Funciones de Autenticación ---

def validar_usuario(username, password):
    """
    Valida las credenciales de un usuario contra la base de datos.
    Retorna el rol del usuario si es válido, de lo contrario None.
    """
    conn = conectar()
    if not conn: return None
    
    rol_usuario = None
    cursor = conn.cursor(dictionary=True)  # dictionary=True para obtener resultados como dict
    
    try:
        query = "SELECT password_hash, rol FROM usuarios_sistema WHERE username = %s AND activo = TRUE"
        cursor.execute(query, (username,))
        usuario = cursor.fetchone()

        if usuario:
            # Compara la contraseña proporcionada con el hash almacenado
            if bcrypt.checkpw(password.encode('utf-8'), usuario['password_hash'].encode('utf-8')):
                rol_usuario = usuario['rol']
                # Actualizar último acceso
                update_query = "UPDATE usuarios_sistema SET ultimo_acceso = NOW() WHERE username = %s"
                cursor.execute(update_query, (username,))
                conn.commit()
    except Error as e:
        print(f"Error al validar usuario: {e}")
    finally:
        cursor.close()
        conn.close()
        
    return rol_usuario

# --- Funciones de Grupos de Clientes (MANTENIDAS COMO EN ORIGINAL) ---

def obtener_grupos():
    """Obtiene todos los grupos de clientes."""
    conn = conectar()
    if not conn: return []
    
    grupos = []
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id_grupo, clave_grupo FROM grupo ORDER BY clave_grupo")
        grupos = cursor.fetchall()
    except Error as e:
        print(f"Error al obtener grupos: {e}")
    finally:
        cursor.close()
        conn.close()
    return grupos

def obtener_clientes_por_grupo(id_grupo):
    """Obtiene los clientes que pertenecen a un grupo específico."""
    conn = conectar()
    if not conn: return []
    
    clientes = []
    cursor = conn.cursor()
    try:
        query = "SELECT id_cliente, nombre_cliente FROM cliente WHERE id_grupo = %s ORDER BY nombre_cliente"
        cursor.execute(query, (id_grupo,))
        clientes = cursor.fetchall()
    except Error as e:
        print(f"Error al obtener clientes: {e}")
    finally:
        cursor.close()
        conn.close()
    return clientes

# --- Funciones de Productos y Precios (ADAPTADAS PARA NUEVA ESTRUCTURA) ---

def buscar_productos_por_grupo(id_grupo, texto_busqueda):
    """
    Busca productos y obtiene su precio específico para un grupo de clientes.
    ADAPTADA para nueva estructura de base de datos.
    """
    conn = conectar()
    if not conn: return []
    
    productos = []
    cursor = conn.cursor()
    try:
        # Unimos producto con precio_por_grupo para obtener el precio correcto
        query = """
            SELECT p.nombre_producto, ppg.precio_base, p.unidad_producto
            FROM producto p
            JOIN precio_por_grupo ppg ON p.id_producto = ppg.id_producto
            WHERE ppg.id_grupo = %s AND p.nombre_producto LIKE %s AND p.stock > 0
            ORDER BY p.nombre_producto
        """
        valores = (id_grupo, f"%{texto_busqueda}%")
        cursor.execute(query, valores)
        productos = cursor.fetchall()
    except Error as e:
        print(f"Error al buscar productos: {e}")
    finally:
        cursor.close()
        conn.close()
    return productos

def buscar_productos_por_grupo_con_especial(id_grupo, texto_busqueda):
    """
    Busca productos y obtiene su precio específico para un grupo de clientes,
    incluyendo si el producto es 'especial'.
    ADAPTADA para nueva estructura de base de datos.
    """
    conn = conectar()
    if not conn: return []
    
    productos = []
    cursor = conn.cursor()
    try:
        query = """
            SELECT p.nombre_producto, ppg.precio_base, p.es_especial, p.unidad_producto
            FROM producto p
            JOIN precio_por_grupo ppg ON p.id_producto = ppg.id_producto
            WHERE ppg.id_grupo = %s AND p.nombre_producto LIKE %s AND p.stock > 0
            ORDER BY p.nombre_producto
        """
        valores = (id_grupo, f"%{texto_busqueda}%")
        cursor.execute(query, valores)
        productos = cursor.fetchall()
    except Error as e:
        print(f"Error al buscar productos con es_especial: {e}")
    finally:
        cursor.close()
        conn.close()
    return productos

def buscar_insumos(query, id_grupo):
    """
    Busca insumos en la base de datos para un grupo específico.
    Retorna lista de diccionarios con id, nombre, precio, unidad y es_especial.
    """
    conn = conectar()
    if not conn: return []
    
    resultados = []
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT 
                p.id_producto as id,
                p.nombre_producto as nombre, 
                ppg.precio_base as precio,
                p.unidad_producto as unidad,
                p.es_especial
            FROM producto p
            JOIN precio_por_grupo ppg ON p.id_producto = ppg.id_producto
            WHERE ppg.id_grupo = %s 
            AND p.nombre_producto LIKE %s 
            AND p.stock > 0
            ORDER BY p.nombre_producto
        """
        cursor.execute(sql, (id_grupo, f"%{query}%"))
        resultados = cursor.fetchall()
        
    except Error as e:
        print(f"Error al buscar insumos: {e}")
    finally:
        cursor.close()
        conn.close()
    return resultados

def buscar_todos_insumos(id_grupo):
    """
    Obtiene todos los insumos para un grupo específico.
    Retorna lista de diccionarios con id, nombre, precio, unidad y es_especial.
    """
    conn = conectar()
    if not conn: return []
    
    resultados = []
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT 
                p.id_producto as id,
                p.nombre_producto as nombre, 
                ppg.precio_base as precio,
                p.unidad_producto as unidad,
                p.es_especial
            FROM producto p
            JOIN precio_por_grupo ppg ON p.id_producto = ppg.id_producto
            WHERE ppg.id_grupo = %s 
            AND p.stock > 0
            ORDER BY p.nombre_producto
        """
        cursor.execute(sql, (id_grupo,))
        resultados = cursor.fetchall()
        
    except Error as e:
        print(f"Error al buscar todos los insumos: {e}")
    finally:
        cursor.close()
        conn.close()
    return resultados

# --- Funciones de Numeración de Folios (ACTUALIZADAS) ---

def obtener_siguiente_folio():
    """
    Obtiene el siguiente número de folio disponible desde la tabla folio_sequence.
    Retorna un número de folio único e incremental.
    """
    conn = conectar()
    if not conn: return None
    
    cursor = conn.cursor()
    siguiente_folio = None
    
    try:
        # Iniciar transacción para evitar race conditions
        conn.start_transaction()
        
        # Usar la tabla folio_sequence para obtener el siguiente folio con bloqueo
        query = "SELECT next_val FROM folio_sequence WHERE id = 1 FOR UPDATE"
        cursor.execute(query)
        resultado = cursor.fetchone()
        
        if resultado:
            siguiente_folio = resultado[0]
            
            # Actualizar el siguiente valor
            update_query = "UPDATE folio_sequence SET next_val = next_val + 1 WHERE id = 1"
            cursor.execute(update_query)
            conn.commit()
        else:
            # Inicializar la secuencia si no existe
            insert_query = "INSERT INTO folio_sequence (id, next_val) VALUES (1, 1)"
            cursor.execute(insert_query)
            conn.commit()
            siguiente_folio = 1
            
    except Error as e:
        print(f"Error al obtener siguiente folio: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
    
    return siguiente_folio

# --- Funciones de Facturación (CORREGIDA PARA NUEVA ESTRUCTURA) ---

def crear_factura_completa(id_cliente, items_carrito, fecha_venta=None, folio_especifico=None):
    """
    Crea una transacción completa: factura, detalles, deuda y actualiza stock.
    Retorna un diccionario con el ID de la nueva factura y el número de folio.
    ADAPTADA para nueva estructura de base de datos.
    
    Args:
        id_cliente: ID del cliente
        items_carrito: Lista con formato [[id_producto, nombre, precio, cantidad, subtotal], ...]
        fecha_venta: Fecha de la venta (opcional)
    """
    if fecha_venta is None:
        fecha_venta = date.today()
    
    # Validar que la fecha no sea futura
    if fecha_venta > date.today():
        print("Error: No se pueden registrar ventas con fecha futura")
        return None
    
    conn = conectar()
    if not conn: return None
    
    cursor = conn.cursor()
    id_factura_nueva = None
    folio_numero = None
    
    try:
        # Iniciar una transacción para asegurar que todas las operaciones se completen
        conn.start_transaction()

        # 1. Obtener el número de folio (específico o siguiente disponible)
        if folio_especifico is not None:
            folio_numero = folio_especifico
            print(f"Usando folio específico para orden guardada: {folio_numero}")
        else:
            folio_numero = obtener_siguiente_folio()
            if folio_numero is None:
                raise Error("No se pudo obtener el número de folio")

        # 2. Crear la factura con número de folio
        query_factura = """
            INSERT INTO factura (fecha_factura, id_cliente, folio_numero) 
            VALUES (%s, %s, %s)
        """
        cursor.execute(query_factura, (fecha_venta, id_cliente, folio_numero))
        id_factura_nueva = cursor.lastrowid  # Obtener el ID de la factura recién creada

        # 3. Insertar cada producto en detalle_factura y actualizar stock
        monto_total = 0.0
        query_detalle = """
            INSERT INTO detalle_factura (id_factura, id_producto, cantidad_factura, precio_unitario_venta)
            VALUES (%s, %s, %s, %s)
        """
        
        query_stock = "UPDATE producto SET stock = stock - %s WHERE id_producto = %s"

        for item in items_carrito:
            # El formato correcto: [id_producto, nombre, precio, cantidad, subtotal]
            id_producto = int(item[0])
            cantidad = float(item[3])  # Asegurar que sea float
            precio = float(item[2])    # Asegurar que sea float
            
            # Insertar detalle
            cursor.execute(query_detalle, (id_factura_nueva, id_producto, cantidad, precio))
            # Actualizar stock
            cursor.execute(query_stock, (cantidad, id_producto))
            
            monto_total += cantidad * precio

        # 4. Los triggers SQL se encargan automáticamente de crear la deuda
        # (after_detalle_insert_update_deuda en disfruleg_triggers.sql)
        
        # Si todo fue exitoso, confirmar la transacción
        conn.commit()
        print(f"Factura creada exitosamente: ID={id_factura_nueva}, Folio={folio_numero}")

    except Error as e:
        print(f"Error en la transacción de facturación: {e}")
        # Si algo falla, revertir todos los cambios
        conn.rollback()
        id_factura_nueva = None
        folio_numero = None
    finally:
        cursor.close()
        conn.close()
        
    return {
        'id_factura': id_factura_nueva,
        'folio_numero': folio_numero
    } if id_factura_nueva else None

def registrar_venta(id_cliente, usuario, items_carrito, total, fecha_venta=None, folio_especifico=None):
    """
    Función alternativa simplificada para registrar venta.
    Retorna el ID de la factura creada o None en caso de error.
    """
    resultado = crear_factura_completa(id_cliente, items_carrito, fecha_venta, folio_especifico)
    return resultado['id_factura'] if resultado else None

# --- Funciones para Órdenes Guardadas (NUEVAS) ---

def guardar_orden(folio, id_cliente, usuario, datos_carrito, total_estimado):
    """
    Guarda una orden en la tabla ordenes_guardadas.
    Retorna True si fue exitoso, False en caso contrario.
    """
    conn = conectar()
    if not conn: return False
    
    cursor = conn.cursor()
    exito = False
    
    try:
        # Convertir datos_carrito a JSON si es un diccionario
        if isinstance(datos_carrito, dict):
            datos_carrito_json = json.dumps(datos_carrito, ensure_ascii=False)
        else:
            datos_carrito_json = datos_carrito
            
        query = """
            INSERT INTO ordenes_guardadas 
            (folio_numero, id_cliente, usuario_creador, datos_carrito, total_estimado, estado)
            VALUES (%s, %s, %s, %s, %s, 'guardada')
        """
        cursor.execute(query, (folio, id_cliente, usuario, datos_carrito_json, total_estimado))
        conn.commit()
        exito = True
        
    except Error as e:
        print(f"Error al guardar orden: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        
    return exito

def cargar_orden(folio):
    """
    Carga una orden guardada desde la base de datos.
    Retorna los datos de la orden o None si no existe.
    """
    conn = conectar()
    if not conn: return None
    
    cursor = conn.cursor(dictionary=True)
    orden = None
    
    try:
        query = """
            SELECT 
                og.folio_numero, 
                og.id_cliente, 
                c.nombre_cliente,
                og.usuario_creador,
                og.datos_carrito,
                og.total_estimado,
                og.estado,
                og.fecha_creacion
            FROM ordenes_guardadas og
            JOIN cliente c ON og.id_cliente = c.id_cliente
            WHERE og.folio_numero = %s AND og.activo = TRUE
        """
        cursor.execute(query, (folio,))
        orden = cursor.fetchone()
        
    except Error as e:
        print(f"Error al cargar orden: {e}")
    finally:
        cursor.close()
        conn.close()
        
    return orden

def actualizar_orden(folio, datos_carrito, total_estimado):
    """
    Actualiza una orden existente.
    Retorna True si fue exitoso, False en caso contrario.
    """
    conn = conectar()
    if not conn: return False
    
    cursor = conn.cursor()
    exito = False
    
    try:
        # Convertir datos_carrito a JSON si es un diccionario
        if isinstance(datos_carrito, dict):
            datos_carrito_json = json.dumps(datos_carrito, ensure_ascii=False)
        else:
            datos_carrito_json = datos_carrito
            
        query = """
            UPDATE ordenes_guardadas 
            SET datos_carrito = %s, total_estimado = %s, fecha_modificacion = NOW()
            WHERE folio_numero = %s AND estado = 'guardada'
        """
        cursor.execute(query, (datos_carrito_json, total_estimado, folio))
        conn.commit()
        exito = cursor.rowcount > 0
        
    except Error as e:
        print(f"Error al actualizar orden: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        
    return exito

def marcar_orden_como_completada(folio, id_factura):
    """
    Marca una orden como completada y la relaciona con una factura.
    Retorna True si fue exitoso, False en caso contrario.
    """
    conn = conectar()
    if not conn: return False
    
    cursor = conn.cursor()
    exito = False
    
    try:
        query = """
            UPDATE ordenes_guardadas 
            SET estado = 'registrada', fecha_modificacion = NOW()
            WHERE folio_numero = %s AND estado = 'guardada'
        """
        cursor.execute(query, (folio,))
        conn.commit()
        exito = cursor.rowcount > 0
        
    except Error as e:
        print(f"Error al marcar orden como completada: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        
    return exito

def verificar_folio_disponible(folio):
    """
    Verifica si un folio está disponible para usar.
    Retorna True si está disponible, False si ya está en uso.
    """
    conn = conectar()
    if not conn: return False
    
    cursor = conn.cursor()
    disponible = True
    
    try:
        # Verificar en órdenes guardadas
        query_ordenes = "SELECT 1 FROM ordenes_guardadas WHERE folio_numero = %s AND activo = TRUE"
        cursor.execute(query_ordenes, (folio,))
        if cursor.fetchone():
            disponible = False
        
        # Verificar en facturas si no se encontró en órdenes
        if disponible:
            query_facturas = "SELECT 1 FROM factura WHERE folio_numero = %s"
            cursor.execute(query_facturas, (folio,))
            if cursor.fetchone():
                disponible = False
                
    except Error as e:
        print(f"Error al verificar folio: {e}")
        disponible = False
    finally:
        cursor.close()
        conn.close()
        
    return disponible

# --- BLOQUE DE PRUEBA ---
if __name__ == '__main__':
    print("--- Probando funciones del database.py actualizado para 'disfruleg' ---")
    
    # Probar conexión
    conn = conectar()
    if conn:
        print("✓ Conexión exitosa a la base de datos")
        conn.close()
    else:
        print("✗ Error de conexión")
    
    # Probar obtención de grupos
    print("\nObteniendo grupos:")
    grupos = obtener_grupos()
    if grupos:
        print(f"Grupos encontrados: {grupos}")
        id_grupo_prueba = grupos[0][0]  # Usar el primer grupo para las demás pruebas
        
        print(f"\nObteniendo clientes del grupo ID {id_grupo_prueba}:")
        clientes = obtener_clientes_por_grupo(id_grupo_prueba)
        print(f"Clientes encontrados: {clientes}")

        print(f"\nBuscando productos para el grupo ID {id_grupo_prueba} que contengan 'a':")
        productos = buscar_productos_por_grupo(id_grupo_prueba, 'a')
        print(f"Productos encontrados: {productos}")

        print(f"\nBuscando productos (con 'es_especial') para el grupo ID {id_grupo_prueba} que contengan 'e':")
        productos_especiales = buscar_productos_por_grupo_con_especial(id_grupo_prueba, 'e')
        print(f"Productos especiales encontrados: {productos_especiales}")
    else:
        print("No se encontraron grupos. Asegúrate de tener datos en la BD.")
    
    # Probar obtención de folio
    print(f"\nObteniendo siguiente folio:")
    folio = obtener_siguiente_folio()
    print(f"Siguiente folio: {folio}")