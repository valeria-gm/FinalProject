import os
import tkinter as tk
from tkinter import messagebox, ttk
import mysql.connector
from src.database.conexion import conectar
from decimal import Decimal
from datetime import datetime
from typing import Any, List
from src.auth.auth_manager import AuthManager

class ComprasApp:
    def __init__(self, root, user_data):
        self.root = root
        self.root.title("Purchase Registry - Market")
        self.root.geometry("800x600")

        # Datos del usuario autenticado
        self.user_data = user_data
        self.es_admin = (self.user_data['rol'] == 'admin')
        self.auth_manager = AuthManager()
        
        # Connect to database
        self.conn: Any = conectar()
        self.cursor: Any = self.conn.cursor(dictionary=True)
        
        # Variables
        self.selected_product = tk.StringVar()
        self.cantidad_var = tk.DoubleVar()
        self.precio_var = tk.DoubleVar()
        self.fecha_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        
        self.load_productos()
        self.create_interface()
        self.load_compras()
        
    def load_productos(self):
        """Cargar productos desde la base de datos"""
        self.cursor.execute("SELECT id_producto, nombre_producto, unidad_producto, es_especial FROM producto ORDER BY nombre_producto")
        self.productos = self.cursor.fetchall()
        
    def create_interface(self):
        """Crear la interfaz de usuario"""
        # Título
        title_frame = tk.Frame(self.root)
        title_frame.pack(fill="x", pady=10)
        
        tk.Label(title_frame, text="Purchase Registry", font=("Arial", 18, "bold")).pack()
        
        # Frame principal dividido en dos secciones
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # SECCIÓN 1: Formulario de registro de compras
        self.create_registro_section(main_frame)
        
        # SECCIÓN 2: Lista de purchases registered
        self.create_lista_section(main_frame)
        
        # Barra de estado
        self.status_var = tk.StringVar()
        self.status_var.set(f"Username: {self.user_data['nombre_completo']} | Role: {self.user_data['rol']}")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_registro_section(self, parent):
        """Crear sección de registro de nuevas compras"""
        # Frame para registro de compras
        registro_frame = tk.LabelFrame(parent, text="Register New Purchase", padx=10, pady=10)
        registro_frame.pack(fill="x", pady=(0, 10))
        
        # Primera fila: Producto y Fecha
        row1 = tk.Frame(registro_frame)
        row1.pack(fill="x", pady=5)
        
        # Producto
        tk.Label(row1, text="Product:", width=15, anchor="w").pack(side="left")
        productos_nombres = [f"{p['nombre_producto']} ({p['unidad_producto']})" for p in self.productos]
        self.producto_combo = ttk.Combobox(row1, textvariable=self.selected_product, 
                                         values=productos_nombres, state="readonly", width=30)
        self.producto_combo.pack(side="left", padx=5)
        
        # Fecha
        tk.Label(row1, text="Date:", anchor="w").pack(side="left", padx=(20, 5))
        self.fecha_entry = tk.Entry(row1, textvariable=self.fecha_var, width=12)
        self.fecha_entry.pack(side="left", padx=5)
        
        # Segunda fila: Cantidad y Precio
        row2 = tk.Frame(registro_frame)
        row2.pack(fill="x", pady=5)
        
        # Cantidad
        tk.Label(row2, text="Quantity:", width=15, anchor="w").pack(side="left")
        self.cantidad_entry = tk.Entry(row2, textvariable=self.cantidad_var, width=15)
        self.cantidad_entry.pack(side="left", padx=5)
        
        # Precio unitario
        tk.Label(row2, text="Price/Unit:", anchor="w").pack(side="left", padx=(20, 5))
        tk.Label(row2, text="$").pack(side="left")
        self.precio_entry = tk.Entry(row2, textvariable=self.precio_var, width=15)
        self.precio_entry.pack(side="left", padx=5)
        
        # Total (calculado automáticamente)
        self.total_var = tk.StringVar(value="$0.00")
        tk.Label(row2, text="Total:", anchor="w").pack(side="left", padx=(20, 5))
        self.total_label = tk.Label(row2, textvariable=self.total_var, font=("Arial", 10, "bold"))
        self.total_label.pack(side="left", padx=5)
        
        # Conectar eventos para cálculo automático
        self.cantidad_var.trace("w", self.calcular_total)
        self.precio_var.trace("w", self.calcular_total)
        
        # Botones
        button_frame = tk.Frame(registro_frame)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Register purchase", command=self.registrar_compra, 
                  bg="#4CAF50", fg="white", padx=15, pady=5).pack(side="left", padx=5)
        tk.Button(button_frame, text="Clear", command=self.limpiar_formulario, 
                  bg="#ff9800", fg="white", padx=15, pady=5).pack(side="left", padx=5)
    
    def create_lista_section(self, parent):
        """Crear sección de lista de compras"""
        # Frame para lista de compras
        lista_frame = tk.LabelFrame(parent, text="Registered purchases", padx=10, pady=10)
        lista_frame.pack(fill="both", expand=True)
        
        # Filtros
        filtro_frame = tk.Frame(lista_frame)
        filtro_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(filtro_frame, text="Filter by product:").pack(side="left", padx=5)
        self.filtro_var = tk.StringVar()
        self.filtro_entry = tk.Entry(filtro_frame, textvariable=self.filtro_var, width=30)
        self.filtro_entry.pack(side="left", padx=5)
        self.filtro_var.trace("w", self.filtrar_compras)
        
        # Botones de acción
        tk.Button(filtro_frame, text="Edit", command=self.editar_compra, 
                  bg="#2196F3", fg="white", padx=10, pady=3).pack(side="right", padx=5)
        tk.Button(filtro_frame, text="Delete", command=self.eliminar_compra, 
                  bg="#f44336", fg="white", padx=10, pady=3).pack(side="right", padx=5)
        
        # Tabla de compras
        self.create_compras_table(lista_frame)
    
    def create_compras_table(self, parent):
        """Crear tabla de compras"""
        # Frame para la tabla con scrollbar
        table_frame = tk.Frame(parent)
        table_frame.pack(fill="both", expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(table_frame)
        scrollbar.pack(side="right", fill="y")
        
        # Treeview
        self.compras_tree = ttk.Treeview(table_frame, 
                                       columns=("id", "fecha", "producto", "cantidad", "precio", "total"),
                                       show="headings", 
                                       yscrollcommand=scrollbar.set)
        
        # Configurar columnas
        self.compras_tree.heading("id", text="ID")
        self.compras_tree.heading("fecha", text="Date")
        self.compras_tree.heading("producto", text="Product")
        self.compras_tree.heading("cantidad", text="Quantity")
        self.compras_tree.heading("precio", text="Unitary price")
        self.compras_tree.heading("total", text="Total")
        
        self.compras_tree.column("id", width=50)
        self.compras_tree.column("fecha", width=100)
        self.compras_tree.column("producto", width=200)
        self.compras_tree.column("cantidad", width=100)
        self.compras_tree.column("precio", width=100)
        self.compras_tree.column("total", width=100)
        
        self.compras_tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.compras_tree.yview)
        
        # Double-click para editar
        self.compras_tree.bind("<Double-1>", lambda event: self.editar_compra())
    
    def calcular_total(self, *args):
        """Calcular total automáticamente"""
        try:
            cantidad = self.cantidad_var.get()
            precio = self.precio_var.get()
            total = cantidad * precio
            self.total_var.set(f"${total:.2f}")
        except:
            self.total_var.set("$0.00")
    
    def verificar_password_admin(self):
        """Verificar contraseña de administrador"""
        popup = tk.Toplevel(self.root)
        popup.title("Admin Authentication")
        popup.geometry("400x300")
        popup.transient(self.root)
        popup.grab_set()
        
        # Centrar popup
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (width // 2)
        y = (popup.winfo_screenheight() // 2) - (height // 2)
        popup.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        # Contenido
        tk.Label(popup, text="🔒 Special Product", 
                font=("Arial", 14, "bold"), fg="#f44336").pack(pady=(20, 10))
        
        tk.Label(popup, text="This product requires admin permissions.\nEnter admin credentials:",
                font=("Arial", 10), justify="center").pack(pady=(0, 20))
        
        # Campos de entrada
        tk.Label(popup, text="Username:", font=("Arial", 11)).pack()
        username_var = tk.StringVar()
        tk.Entry(popup, textvariable=username_var, font=("Arial", 11)).pack(pady=(0, 10))
        
        tk.Label(popup, text="Password:", font=("Arial", 11)).pack()
        password_var = tk.StringVar()
        tk.Entry(popup, textvariable=password_var, show="*", font=("Arial", 11)).pack(pady=(0, 20))
        
        # Variable para resultado
        result = {'success': False}
        
        def verificar():
            username = username_var.get().strip()
            password = password_var.get().strip()
            
            if not username or not password:
                messagebox.showerror("Error", "Please enter username and password")
                return
            
            auth_result = self.auth_manager.authenticate(username, password)
            
            if auth_result['success'] and auth_result['user_data']['rol'] == 'admin':
                result['success'] = True
                popup.destroy()
            else:
                messagebox.showerror("Error", auth_result.get('message', 'Invalid credentials'))
                password_var.set("")
        
        # Botones
        button_frame = tk.Frame(popup)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Verify", command=verificar,
                 bg="#4CAF50", fg="white", padx=15, pady=5).pack(side="left", padx=10)
        tk.Button(button_frame, text="Cancel", command=popup.destroy,
                 bg="#f44336", fg="white", padx=15, pady=5).pack(side="left", padx=10)
        
        popup.wait_window()
        return result['success']

    def registrar_compra(self):
        """Registrar una nueva compra"""
        # Validar campos existentes...
        if not self.selected_product.get():
            messagebox.showerror("Error", "You must select a product")
            return
        
        # NUEVA VALIDACIÓN DE FECHA
        fecha = self.fecha_var.get()
        fecha_valida, resultado = self.validar_fecha(fecha)
        
        if not fecha_valida:
            messagebox.showerror("Date Error", str(resultado))
            return
        
        # Usar la fecha validada en lugar de la fecha actual
        assert isinstance(resultado, datetime), "the result must be a datetime after succeddful validation"
        fecha_compra = resultado.strftime("%Y-%m-%d")
        
        try:
            cantidad = Decimal(str(self.cantidad_var.get()))
            precio = Decimal(str(self.precio_var.get()))
            
            if cantidad <= Decimal('0'):
                messagebox.showerror("Error", "Quantity must be greater than 0")
                return
                
            if precio <= Decimal('0'):
                messagebox.showerror("Error", "Price must be greater than 0")
                return
        except Exception as e:
            messagebox.showerror("Error", f"Verify that quantity and price are valid numbers: {str(e)}")
            return
        
        # Obtener ID del producto seleccionado
        producto_nombre = self.selected_product.get().split(" (")[0]  # Remover la unidad
        producto_id = None
        producto_especial = False
        
        for p in self.productos:
            if p['nombre_producto'] == producto_nombre:
                producto_id = p['id_producto']
                producto_especial = p.get('es_especial', False)
                break
        
        if not producto_id:
            messagebox.showerror("Error", "The selected product could not be identified")
            return
        
        # Verificar si es producto especial y el usuario no es admin
        if producto_especial and not self.es_admin:
            if not self.verificar_password_admin():
                return  # Usuario canceló o falló la autenticación
        
        try:
            # Insertar en la base de datos CON LA FECHA ESPECIFICADA
            # NOTA: Los triggers manejan automáticamente la actualización del stock
            self.cursor.execute("""
                INSERT INTO compra (fecha_compra, id_producto, cantidad_compra, precio_unitario_compra)
                VALUES (%s, %s, %s, %s)
            """, (fecha, producto_id, cantidad, precio))
            
            self.conn.commit()
            
            # Confirmar y limpiar
            messagebox.showinfo("Success", "Purchase registered successfully")
            self.status_var.set(f"Purchase registered - Total: ${cantidad * precio:.2f}")
            self.limpiar_formulario()
            self.load_compras()
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error registering purchase: {str(e)}")
    
    def limpiar_formulario(self):
        """Limpiar formulario"""
        self.selected_product.set("")
        self.cantidad_var.set(0)
        self.precio_var.set(0)
        self.fecha_var.set(datetime.now().strftime("%Y-%m-%d"))
        self.total_var.set("$0.00")
    
    def load_compras(self):
        """Cargar compras desde la base de datos"""
        # Limpiar tabla existente
        for item in self.compras_tree.get_children():
            self.compras_tree.delete(item)
        
        # Obtener compras con detalles del producto
        self.cursor.execute("""
            SELECT c.id_compra, c.fecha_compra as fecha, p.nombre_producto, p.unidad_producto as unidad, 
                   c.cantidad_compra as cantidad, c.precio_unitario_compra as precio_unitario_compra,
                   (c.cantidad_compra * c.precio_unitario_compra) as total
            FROM compra c
            JOIN producto p ON c.id_producto = p.id_producto
            ORDER BY c.fecha_compra DESC, c.id_compra DESC
        """)
        
        compras = self.cursor.fetchall()
        
        # Guardar todas las compras para filtrado
        self.all_compras = compras
        
        # Insertar en la tabla
        for compra in compras:
            self.compras_tree.insert("", "end", 
                                   values=(compra["id_compra"],
                                          compra["fecha"],
                                          f"{compra['nombre_producto']} ({compra['unidad']})",
                                          f"{compra['cantidad']:.2f}",
                                          f"${compra['precio_unitario_compra']:.2f}",
                                          f"${compra['total']:.2f}"))
        
        # Refresh contador en barra de estado
        total_compras = sum(c['total'] for c in compras if c['total'])
        self.status_var.set(f"Username: {self.user_data['nombre_completo']} | Purchases: {len(compras)} registers - Total: ${total_compras:.2f}")
    
    def filtrar_compras(self, *args):
        """Filtrar compras por producto"""
        filtro = self.filtro_var.get().lower()
        
        # Limpiar tabla
        for item in self.compras_tree.get_children():
            self.compras_tree.delete(item)
        
        # Filtrar y mostrar
        for compra in self.all_compras:
            if filtro in compra['nombre_producto'].lower():
                self.compras_tree.insert("", "end", 
                                       values=(compra["id_compra"],
                                              compra["fecha"],
                                              f"{compra['nombre_producto']} ({compra['unidad']})",
                                              f"{compra['cantidad']:.2f}",
                                              f"${compra['precio_unitario_compra']:.2f}",
                                              f"${compra['total']:.2f}"))
    
    def editar_compra(self):
        """Editar compra seleccionada"""
        selected_item = self.compras_tree.focus()
        if not selected_item:
            messagebox.showwarning("Warning", "Select a purchase to edit")
            return
        
        # Obtener datos de la compra
        values = self.compras_tree.item(selected_item, "values")
        compra_id = values[0]
        
         # Obtener datos completos de la base de datos
        self.cursor.execute("""
            SELECT c.*, p.nombre_producto, p.unidad_producto, p.es_especial
            FROM compra c
            JOIN producto p ON c.id_producto = p.id_producto
            WHERE c.id_compra = %s
        """, (compra_id,))
        
        compra = self.cursor.fetchone()
        if not compra:
            messagebox.showerror("Error", "Purchase not found")
            return
        
        # Verificar si es producto especial y el usuario no es admin
        if compra.get('es_especial', False) and not self.es_admin:
            if not self.verificar_password_admin():
                return  # Usuario canceló o falló la autenticación

        # Crear ventana de edición
        self.create_edit_dialog(compra)
    
    def create_edit_dialog(self, compra):
        """Crear diálogo de edición"""
        popup = tk.Toplevel(self.root)
        popup.title("Edit Purchase")
        popup.geometry("500x350")
        popup.transient(self.root)
        popup.grab_set()
        
        # Centrar popup
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (width // 2)
        y = (popup.winfo_screenheight() // 2) - (height // 2)
        popup.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        # Título
        tk.Label(popup, text="Edit Purchase", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Formulario
        form_frame = tk.Frame(popup)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Producto (no editable)
        prod_frame = tk.Frame(form_frame)
        prod_frame.pack(fill="x", pady=5)
        tk.Label(prod_frame, text="Product:", width=15, anchor="w").pack(side="left")
        tk.Label(prod_frame, text=f"{compra['nombre_producto']} ({compra['unidad_producto']})", 
                font=("Arial", 10, "bold")).pack(side="left")
        
        # Fecha
        fecha_frame = tk.Frame(form_frame)
        fecha_frame.pack(fill="x", pady=5)
        tk.Label(fecha_frame, text="Date:", width=15, anchor="w").pack(side="left")
        fecha_var = tk.StringVar(value=str(compra['fecha_compra']))
        fecha_entry = tk.Entry(fecha_frame, textvariable=fecha_var, width=20)
        fecha_entry.pack(side="left", fill="x", expand=True)
        
        # Cantidad
        cant_frame = tk.Frame(form_frame)
        cant_frame.pack(fill="x", pady=5)
        tk.Label(cant_frame, text="Quantity:", width=15, anchor="w").pack(side="left")
        cantidad_var = tk.DoubleVar(value=float(compra['cantidad_compra']))
        cantidad_entry = tk.Entry(cant_frame, textvariable=cantidad_var, width=20)
        cantidad_entry.pack(side="left", fill="x", expand=True)
        
        # Precio
        precio_frame = tk.Frame(form_frame)
        precio_frame.pack(fill="x", pady=5)
        tk.Label(precio_frame, text="Unitary price:", width=15, anchor="w").pack(side="left")
        precio_var = tk.DoubleVar(value=float(compra['precio_unitario_compra']))
        precio_entry = tk.Entry(precio_frame, textvariable=precio_var, width=20)
        precio_entry.pack(side="left", fill="x", expand=True)
        
        # Total calculado
        total_frame = tk.Frame(form_frame)
        total_frame.pack(fill="x", pady=5)
        tk.Label(total_frame, text="Total:", width=15, anchor="w").pack(side="left")
        total_var = tk.StringVar()
        total_label = tk.Label(total_frame, textvariable=total_var, font=("Arial", 10, "bold"))
        total_label.pack(side="left")
        
        # Función para calcular total
        def calcular_total_edit(*args):
            try:
                total = cantidad_var.get() * precio_var.get()
                total_var.set(f"${total:.2f}")
            except:
                total_var.set("$0.00")
        
        # Conectar cálculo automático
        cantidad_var.trace("w", calcular_total_edit)
        precio_var.trace("w", calcular_total_edit)
        calcular_total_edit()  # Calcular inicialmente
        
        # Botones
        button_frame = tk.Frame(popup)
        button_frame.pack(side="bottom", fill="x", pady=15)
        
        tk.Button(button_frame, text="Save changes", 
                 command=lambda: self.save_edit_compra(popup, compra['id_compra'], 
                                                     fecha_var.get(), cantidad_var.get(), precio_var.get()), 
                 bg="#4CAF50", fg="white", padx=15, pady=5).pack(side="left", padx=10)
        
        tk.Button(button_frame, text="Cancel", 
                 command=popup.destroy, 
                 bg="#f44336", fg="white", padx=15, pady=5).pack(side="left", padx=10)
    
    def validar_fecha(self, fecha_str):
        """Valida que la fecha esté en formato correcto y no sea futura"""
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            fecha_actual = datetime.now()
            
            # Permitir fechas pasadas y del día actual
            if fecha <= fecha_actual:
                return True, fecha
            else:
                return False, "Future dates cannot be registered"
        except ValueError:
            return False, "Invalid date format. Use YYYY-MM-DD"

    def save_edit_compra(self, popup, compra_id, fecha, cantidad, precio):
        """Guardar cambios en la compra"""
        try:
            # Convertir a Decimal
            cantidad = Decimal(str(cantidad))
            precio = Decimal(str(precio))
            
            # Validar
            if cantidad <= Decimal('0'):
                messagebox.showerror("Error", "Quantity must be greater than 0")
                return
            if precio <= Decimal('0'):
                messagebox.showerror("Error", "Price must be greater than 0")
                return
            
            # Obtener cantidad anterior para ajustar stock manualmente ya que no hay trigger para UPDATE
            self.cursor.execute("""
                SELECT cantidad_compra, id_producto 
                FROM compra 
                WHERE id_compra = %s
            """, (compra_id,))
            old_data = self.cursor.fetchone()
            
            if not old_data:
                raise Exception("Purchase not found")
            
            diferencia_cantidad = cantidad - Decimal(str(old_data['cantidad_compra']))
            
            # Refresh en la base de datos
            self.cursor.execute("""
                UPDATE compra 
                SET fecha_compra = %s, cantidad_compra = %s, precio_unitario_compra = %s
                WHERE id_compra = %s
            """, (fecha, float(cantidad), float(precio), compra_id))
            
            # Refresh stock del producto manualmente (no hay trigger para UPDATE en compra)
            if diferencia_cantidad != Decimal('0'):
                self.cursor.execute("""
                    UPDATE producto 
                    SET stock = stock + %s 
                    WHERE id_producto = %s
                """, (float(diferencia_cantidad), old_data['id_producto']))
            
            self.conn.commit()
            
            messagebox.showinfo("Success", "Purchase updated successfully")
            popup.destroy()
            self.load_compras()
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error updating purchase: {str(e)}")

    def eliminar_compra(self):
        """Eliminar compra seleccionada"""
        selected_item = self.compras_tree.focus()
        if not selected_item:
            messagebox.showwarning("Warning", "Select a purchase to delete")
            return
        
        # Obtener datos de la compra
        values = self.compras_tree.item(selected_item, "values")
        compra_id = values[0]
        producto = values[2]
        total = values[5]
        
        # Confirmar eliminación
        if not messagebox.askyesno("Confirm Deletion", 
                                 f"Are you sure you want to delete this purchase?\n\n"
                                 f"Product: {producto}\n"
                                 f"Total: {total}"):
            return
        
        try:
            # Obtener datos para ajustar stock manualmente (ya que necesitamos revertir el stock)
            self.cursor.execute("""
                SELECT cantidad_compra, id_producto 
                FROM compra 
                WHERE id_compra = %s
            """, (compra_id,))
            compra_data = self.cursor.fetchone()
            
            if compra_data:
                # Eliminar de la base de datos
                self.cursor.execute("DELETE FROM compra WHERE id_compra = %s", (compra_id,))
                
                # Ajustar stock manualmente (revertir la cantidad que se había agregado)
                self.cursor.execute("""
                    UPDATE producto 
                    SET stock = stock - %s 
                    WHERE id_producto = %s
                """, (compra_data['cantidad_compra'], compra_data['id_producto']))
            
            self.conn.commit()
            
            messagebox.showinfo("Success", "Purchase deleted successfully")
            self.load_compras()
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error deleting purchase: {str(e)}")

    def on_closing(self):
        """Cerrar aplicación"""
        try:
            self.conn.close()
        except:
            pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    user_data = {
        'nombre_completo': 'Usuario Prueba',
        'rol': 'usuario'  # Cambiar a 'admin' para probar productos especiales
    }
    app = ComprasApp(root, user_data)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()