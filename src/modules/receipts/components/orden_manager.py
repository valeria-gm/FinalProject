# src/modules/receipts/components/orden_manager.py
# Gestor de órdenes guardadas y manejo de folios reservados - VERSIÓN ACTUALIZADA

import json
import mysql.connector
from mysql.connector import Error
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
from .database import conectar

class OrdenManager:
    """
    Gestor centralizado para el manejo de órdenes guardadas y folios reservados.
    
    Responsabilidades:
    - Gestión de folios únicos y reservados
    - Persistencia de órdenes en estado 'guardada'
    - Conversión entre formato carrito y JSON
    - Control de permisos por usuario
    """
    
    def __init__(self):
        self.connection = None
    
    def _get_connection(self):
        """Obtiene conexión a la base de datos usando la configuración existente"""
        if not self.connection or not self.connection.is_connected():
            self.connection = conectar()
        return self.connection
    
    def _close_connection(self):
        """Cierra la conexión si está activa"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.connection = None
    
    # ==================== GESTIÓN DE FOLIOS ====================
    
    def obtener_siguiente_folio_disponible(self) -> Optional[int]:
        """
        Obtiene el siguiente folio disponible usando la tabla folio_sequence.
        
        Returns:
            int: Siguiente folio disponible o None si hay error
        """
        conn = self._get_connection()
        if not conn:
            print("Error: No se pudo conectar a la base de datos")
            return None
        
        cursor = conn.cursor()
        siguiente_folio = None
        
        try:
            # Usar tabla folio_sequence para obtener el siguiente folio
            query = "SELECT next_val FROM folio_sequence WHERE id = 1 FOR UPDATE"
            cursor.execute(query)
            resultado = cursor.fetchone()
            
            if resultado:
                siguiente_folio = resultado[0]
                
                # Actualizar el siguiente valor
                update_query = "UPDATE folio_sequence SET next_val = next_val + 1 WHERE id = 1"
                cursor.execute(update_query)
                conn.commit()
                
                print(f"Siguiente folio disponible: {siguiente_folio}")
            else:
                # Inicializar la secuencia si no existe
                insert_query = "INSERT INTO folio_sequence (id, next_val) VALUES (1, 1)"
                cursor.execute(insert_query)
                conn.commit()
                siguiente_folio = 1
                print(f"Inicializado folio_sequence, primer folio: {siguiente_folio}")
            
        except Error as e:
            print(f"Error al obtener siguiente folio: {e}")
            conn.rollback()
        finally:
            cursor.close()
        
        return siguiente_folio
    
    def _verificar_folio_disponible(self, folio: int) -> bool:
        """
        Verifica si un folio específico está disponible.
        
        Args:
            folio: Número de folio a verificar
            
        Returns:
            bool: True si está disponible, False si ya está usado
        """
        conn = self._get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        disponible = False
        
        try:
            # Verificar en órdenes guardadas activas
            query_orden = """
                SELECT COUNT(*) FROM ordenes_guardadas 
                WHERE folio_numero = %s AND activo = TRUE
            """
            cursor.execute(query_orden, (folio,))
            count_orden = cursor.fetchone()[0]
            
            disponible = count_orden == 0
            
        except Error as e:
            print(f"Error al verificar disponibilidad del folio {folio}: {e}")
        finally:
            cursor.close()
        
        return disponible
    
    # ==================== GESTIÓN DE ÓRDENES ====================
    
    def reservar_folio(self, folio: int, id_cliente: int, usuario: str, 
                      datos_carrito: Dict[str, Any], total: float) -> bool:
        """
        Reserva un folio creando una orden en estado 'guardada'.
        
        Args:
            folio: Número de folio a reservar
            id_cliente: ID del cliente
            usuario: Usuario que crea la orden
            datos_carrito: Datos completos del carrito
            total: Total estimado de la orden
            
        Returns:
            bool: True si se reservó exitosamente, False si falló
        """
        if not self._verificar_folio_disponible(folio):
            print(f"Error: El folio {folio} ya está en uso")
            return False
        
        conn = self._get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        try:
            # Serializar datos del carrito
            carrito_json = json.dumps(datos_carrito, ensure_ascii=False, indent=2)
            
            # Insertar orden guardada
            query = """
                INSERT INTO ordenes_guardadas 
                (folio_numero, id_cliente, usuario_creador, datos_carrito, total_estimado, estado)
                VALUES (%s, %s, %s, %s, %s, 'guardada')
            """
            
            cursor.execute(query, (folio, id_cliente, usuario, carrito_json, total))
            conn.commit()
            
            print(f"Folio {folio} reservado exitosamente para usuario {usuario}")
            return True
            
        except Error as e:
            if e.errno == 1062:  # Duplicate entry error
                print(f"Error: El folio {folio} ya está siendo usado (conflicto de clave duplicada)")
            else:
                print(f"Error al reservar folio {folio}: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
    
    def liberar_folio(self, folio: int) -> bool:
        """
        Libera un folio eliminando la orden guardada (soft delete).
        
        Args:
            folio: Número de folio a liberar
            
        Returns:
            bool: True si se liberó exitosamente, False si falló
        """
        conn = self._get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        try:
            # Soft delete: marcar como inactivo
            query = """
                UPDATE ordenes_guardadas 
                SET activo = FALSE, fecha_modificacion = CURRENT_TIMESTAMP
                WHERE folio_numero = %s AND estado = 'guardada' AND activo = TRUE
            """
            
            cursor.execute(query, (folio,))
            
            if cursor.rowcount > 0:
                conn.commit()
                print(f"Folio {folio} liberado exitosamente")
                return True
            else:
                print(f"No se encontró orden guardada con folio {folio}")
                return False
                
        except Error as e:
            print(f"Error al liberar folio {folio}: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
    
    def obtener_ordenes_activas(self, usuario: str, es_admin: bool = False) -> List[Dict[str, Any]]:
        """
        Obtiene lista de órdenes en estado 'guardada'.
        
        Args:
            usuario: Usuario que solicita las órdenes
            es_admin: Si el usuario es administrador
            
        Returns:
            List[Dict]: Lista de órdenes activas con información resumida
        """
        conn = self._get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        ordenes = []
        
        try:
            # Query base
            query = """
                SELECT 
                    og.folio_numero,
                    og.id_cliente,
                    c.nombre_cliente,
                    og.usuario_creador,
                    og.fecha_creacion,
                    og.fecha_modificacion,
                    og.total_estimado,
                    JSON_LENGTH(og.datos_carrito, '$.items') as num_items
                FROM ordenes_guardadas og
                JOIN cliente c ON og.id_cliente = c.id_cliente
                WHERE og.estado = 'guardada' AND og.activo = TRUE
            """
            
            # Filtrar por usuario si no es admin
            if not es_admin:
                query += " AND og.usuario_creador = %s"
                cursor.execute(query, (usuario,))
            else:
                cursor.execute(query)
            
            ordenes = cursor.fetchall()
            
            # Formatear fechas para mejor legibilidad
            for orden in ordenes:
                if orden['fecha_creacion']:
                    orden['fecha_creacion_str'] = orden['fecha_creacion'].strftime('%d/%m/%Y %H:%M')
                if orden['fecha_modificacion']:
                    orden['fecha_modificacion_str'] = orden['fecha_modificacion'].strftime('%d/%m/%Y %H:%M')
            
            print(f"Obtenidas {len(ordenes)} órdenes activas para usuario {usuario}")
            
        except Error as e:
            print(f"Error al obtener órdenes activas: {e}")
        finally:
            cursor.close()
        
        return ordenes
    
    def obtener_historial(self, usuario: str, es_admin: bool = False, 
                         limite: int = 50) -> List[Dict[str, Any]]:
        """
        Obtiene historial de órdenes en estado 'registrada'.
        
        Args:
            usuario: Usuario que solicita el historial
            es_admin: Si el usuario es administrador
            limite: Número máximo de registros a retornar
            
        Returns:
            List[Dict]: Lista de órdenes registradas
        """
        conn = self._get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        historial = []
        
        try:
            query = """
                SELECT 
                    og.folio_numero,
                    og.id_cliente,
                    c.nombre_cliente,
                    og.usuario_creador,
                    og.fecha_creacion,
                    og.fecha_modificacion,
                    og.total_estimado,
                    f.id_factura as id_venta_asociada
                FROM ordenes_guardadas og
                JOIN cliente c ON og.id_cliente = c.id_cliente
                LEFT JOIN factura f ON og.folio_numero = f.id_factura
                WHERE og.estado = 'registrada' AND og.activo = TRUE
            """
            
            # Filtrar por usuario si no es admin
            if not es_admin:
                query += " AND og.usuario_creador = %s"
            
            query += " ORDER BY og.fecha_modificacion DESC LIMIT %s"
            
            if not es_admin:
                cursor.execute(query, (usuario, limite))
            else:
                cursor.execute(query, (limite,))
            
            historial = cursor.fetchall()
            
            # Formatear fechas
            for orden in historial:
                if orden['fecha_creacion']:
                    orden['fecha_creacion_str'] = orden['fecha_creacion'].strftime('%d/%m/%Y %H:%M')
                if orden['fecha_modificacion']:
                    orden['fecha_modificacion_str'] = orden['fecha_modificacion'].strftime('%d/%m/%Y %H:%M')
            
            print(f"Obtenido historial de {len(historial)} órdenes para usuario {usuario}")
            
        except Error as e:
            print(f"Error al obtener historial: {e}")
        finally:
            cursor.close()
        
        return historial
    
    def cargar_orden(self, folio: int) -> Optional[Dict[str, Any]]:
        """
        Carga los datos completos de una orden específica.
        
        Args:
            folio: Número de folio de la orden
            
        Returns:
            Dict: Datos completos de la orden o None si no existe
        """
        conn = self._get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        orden = None
        
        try:
            query = """
                SELECT 
                    og.*,
                    c.nombre_cliente,
                    t.nombre_tipo as tipo_cliente
                FROM ordenes_guardadas og
                JOIN cliente c ON og.id_cliente = c.id_cliente
                JOIN grupo g ON c.id_grupo = g.id_grupo
                JOIN tipo_cliente t ON g.id_tipo_cliente = t.id_tipo_cliente
                WHERE og.folio_numero = %s AND og.activo = TRUE
            """
            
            cursor.execute(query, (folio,))
            resultado = cursor.fetchone()
            
            if resultado:
                # Deserializar datos del carrito
                try:
                    datos_carrito = json.loads(resultado['datos_carrito'])
                    resultado['datos_carrito_obj'] = datos_carrito
                except json.JSONDecodeError as e:
                    print(f"Error al deserializar carrito del folio {folio}: {e}")
                    resultado['datos_carrito_obj'] = None
                
                orden = resultado
                print(f"Orden {folio} cargada exitosamente")
            else:
                print(f"No se encontró orden con folio {folio}")
        
        except Error as e:
            print(f"Error al cargar orden {folio}: {e}")
        finally:
            cursor.close()
        
        return orden
    
    def actualizar_orden(self, folio: int, datos_carrito: Dict[str, Any], 
                        total: float) -> bool:
        """
        Actualiza los datos de una orden existente.
        
        Args:
            folio: Número de folio de la orden
            datos_carrito: Nuevos datos del carrito
            total: Nuevo total estimado
            
        Returns:
            bool: True si se actualizó exitosamente, False si falló
        """
        conn = self._get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        try:
            # Serializar nuevos datos del carrito
            carrito_json = json.dumps(datos_carrito, ensure_ascii=False, indent=2)
            
            # Actualizar orden
            query = """
                UPDATE ordenes_guardadas 
                SET datos_carrito = %s, 
                    total_estimado = %s,
                    fecha_modificacion = CURRENT_TIMESTAMP
                WHERE folio_numero = %s AND estado = 'guardada' AND activo = TRUE
            """
            
            cursor.execute(query, (carrito_json, total, folio))
            
            if cursor.rowcount > 0:
                conn.commit()
                print(f"Orden {folio} actualizada exitosamente")
                return True
            else:
                print(f"No se encontró orden guardada con folio {folio}")
                return False
                
        except Error as e:
            print(f"Error al actualizar orden {folio}: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
    
    def marcar_como_completada(self, folio: int, id_venta: int) -> bool:
        """
        Marca una orden como 'registrada' cuando se completa la venta.
        
        Args:
            folio: Número de folio de la orden
            id_venta: ID de la venta asociada en la tabla factura
            
        Returns:
            bool: True si se marcó exitosamente, False si falló
        """
        conn = self._get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        try:
            query = """
                UPDATE ordenes_guardadas 
                SET estado = 'registrada', fecha_modificacion = CURRENT_TIMESTAMP
                WHERE folio_numero = %s AND estado = 'guardada' AND activo = TRUE
            """
            
            cursor.execute(query, (folio,))
            
            if cursor.rowcount > 0:
                conn.commit()
                print(f"Orden {folio} marcada como registrada (venta ID: {id_venta})")
                return True
            else:
                print(f"No se encontró orden guardada con folio {folio}")
                return False
                
        except Error as e:
            print(f"Error al marcar orden {folio} como registrada: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
    
    # ==================== UTILIDADES DE CONVERSIÓN ====================
    
    @staticmethod
    def carrito_a_json(carrito_obj) -> Dict[str, Any]:
        """
        Convierte un objeto CarritoConSecciones a formato JSON serializable.
        
        Args:
            carrito_obj: Instancia de CarritoConSecciones
            
        Returns:
            Dict: Datos del carrito en formato serializable
        """
        try:
            datos = {
                'sectioning_enabled': carrito_obj.sectioning_enabled,
                'secciones': {},
                'items': {},
                'timestamp': datetime.now().isoformat()
            }
            
            # Serializar secciones
            for seccion_id, seccion in carrito_obj.secciones.items():
                datos['secciones'][seccion_id] = {
                    'id': seccion.id,
                    'nombre': seccion.nombre
                }
            
            # Serializar items - ¡ACTUALIZADO para incluir id_producto!
            for key, item in carrito_obj.items.items():
                datos['items'][key] = {
                    'id_producto': item.id_producto,  # Añadir ID del producto
                    'nombre_producto': item.nombre_producto,
                    'cantidad': item.cantidad,
                    'precio_unitario': item.precio_unitario,
                    'unidad_producto': item.unidad_producto,
                    'seccion_id': item.seccion_id,
                    'subtotal': item.subtotal
                }
            
            return datos
            
        except Exception as e:
            print(f"Error al convertir carrito a JSON: {e}")
            return {}
    
    @staticmethod
    def json_a_carrito(datos_json: Dict[str, Any], carrito_obj) -> bool:
        """
        Carga datos JSON en un objeto CarritoConSecciones.
        
        Args:
            datos_json: Datos del carrito en formato JSON
            carrito_obj: Instancia de CarritoConSecciones a llenar
            
        Returns:
            bool: True si se cargó exitosamente, False si falló
        """
        try:
            # Limpiar carrito actual
            carrito_obj.items.clear()
            carrito_obj.secciones.clear()
            
            # Configurar modo de secciones
            carrito_obj.sectioning_enabled = datos_json.get('sectioning_enabled', False)
            carrito_obj.sectioning_var.set(carrito_obj.sectioning_enabled)
            
            # Cargar secciones
            secciones_data = datos_json.get('secciones', {})
            for seccion_id, seccion_data in secciones_data.items():
                from .carrito_module import SeccionCarrito
                seccion = SeccionCarrito(seccion_data['id'], seccion_data['nombre'])
                carrito_obj.secciones[seccion_id] = seccion
            
            # Cargar items - ¡CORREGIDO!
            items_data = datos_json.get('items', {})
            for key, item_data in items_data.items():
                from .carrito_module import ItemCarrito
                
                # Asegurar que los tipos numéricos sean correctos
                cantidad = float(item_data['cantidad']) if isinstance(item_data['cantidad'], (int, float, str)) else 0.0
                precio_unitario = float(item_data['precio_unitario']) if isinstance(item_data['precio_unitario'], (int, float, str)) else 0.0
                
                item = ItemCarrito(
                    item_data.get('id_producto', 0),  # Añadir ID del producto
                    item_data['nombre_producto'],
                    cantidad,
                    precio_unitario,
                    item_data['unidad_producto'],
                    item_data.get('seccion_id')
                )
                carrito_obj.items[key] = item
            
            # Actualizar display
            carrito_obj._actualizar_display()
            carrito_obj._notificar_cambio()
            
            print("Carrito cargado exitosamente desde JSON")
            return True
            
        except Exception as e:
            print(f"Error al cargar carrito desde JSON: {e}")
            import traceback
            traceback.print_exc()  # Para debugging detallado
            return False
    
    # ==================== CLEANUP ====================
    
    def __del__(self):
        """Cleanup al destruir la instancia"""
        self._close_connection()


# ==================== FUNCIONES DE CONVENIENCIA ====================

def obtener_manager():
    """
    Factory function para obtener una instancia del OrdenManager.
    
    Returns:
        OrdenManager: Instancia configurada del gestor
    """
    return OrdenManager()

def limpiar_ordenes_antiguas(dias: int = 30) -> int:
    """
    Limpia órdenes guardadas inactivas más antiguas que el número de días especificado.
    
    Args:
        dias: Número de días de antigüedad para considerar una orden como antigua
        
    Returns:
        int: Número de órdenes limpiadas
    """
    manager = obtener_manager()
    conn = manager._get_connection()
    
    if not conn:
        return 0
    
    cursor = conn.cursor()
    ordenes_limpiadas = 0
    
    try:
        query = """
            DELETE FROM ordenes_guardadas 
            WHERE estado = 'guardada' 
            AND activo = FALSE 
            AND fecha_modificacion < DATE_SUB(NOW(), INTERVAL %s DAY)
        """
        
        cursor.execute(query, (dias,))
        ordenes_limpiadas = cursor.rowcount
        conn.commit()
        
        print(f"Limpiadas {ordenes_limpiadas} órdenes antiguas")
        
    except Error as e:
        print(f"Error al limpiar órdenes antiguas: {e}")
        conn.rollback()
    finally:
        cursor.close()
        manager._close_connection()
    
    return ordenes_limpiadas


# ==================== BLOQUE DE PRUEBA ====================

if __name__ == '__main__':
    """Bloque de pruebas para verificar funcionalidad"""
    print("--- Probando OrdenManager ---")
    
    manager = obtener_manager()
    
    # Probar obtener siguiente folio
    folio = manager.obtener_siguiente_folio_disponible()
    print(f"Siguiente folio disponible: {folio}")
    
    # Probar obtener órdenes activas
    ordenes = manager.obtener_ordenes_activas("test_user", es_admin=True)
    print(f"Órdenes activas encontradas: {len(ordenes)}")
    
    # Probar obtener historial
    historial = manager.obtener_historial("test_user", es_admin=True, limite=10)
    print(f"Registros en historial: {len(historial)}")
    
    print("--- Pruebas completadas ---")