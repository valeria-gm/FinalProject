import os
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import mysql.connector
from src.database.conexion import conectar
from decimal import Decimal
from src.auth.auth_manager import AuthManager

class PriceEditorApp:
    def __init__(self, root, user_data=None):
        self.root = root
        self.root.title("Editor de Precios - Disfruleg")
        self.root.geometry("1000x700")
        
        # User data
        self.user_data = user_data if isinstance(user_data, dict) else {}
        self.es_admin = (self.user_data.get('rol', '') == 'admin')
        
        # Connect to database
        self.conn = conectar()
        self.cursor = self.conn.cursor(dictionary=True)
        self.auth_manager = AuthManager()
        
        # Variables
        self.current_group = tk.IntVar(value=1)
        self.changes_made = False
        self.groups = []
        self.client_types = []
        
        self.create_interface()
        self.load_groups()
        self.load_client_types()
        self.load_products()
    
    def create_interface(self):
        # Main container
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_frame = tk.Frame(main_frame, bg="#2C3E50", relief="raised", bd=2)
        title_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(title_frame, 
                text="EDITOR DE PRECIOS", 
                font=("Arial", 18, "bold"),
                fg="white", bg="#2C3E50").pack(pady=10)
        
        # User info
        if self.user_data:
            user_info = f"Usuario: {self.user_data.get('nombre_completo', '')} | Rol: {self.user_data.get('rol', '')}"
            tk.Label(title_frame, 
                    text=user_info, 
                    font=("Arial", 10),
                    fg="#BDC3C7", bg="#2C3E50").pack(pady=(0, 5))
        
        # Group selection frame
        group_frame = tk.Frame(main_frame, bg="#f0f0f0")
        group_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(group_frame, 
                text="1. Seleccionar Grupo para Editar Precios:", 
                font=("Arial", 12, "bold"),
                bg="#f0f0f0").pack(side="left", padx=5)
        
        self.group_buttons_frame = tk.Frame(group_frame, bg="#f0f0f0")
        self.group_buttons_frame.pack(side="left")
        
        # Client types info frame
        client_type_info_frame = tk.Frame(main_frame, bg="#f0f0f0")
        client_type_info_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(client_type_info_frame, 
                text="2. Información de Tipos de Cliente (Descuentos):", 
                font=("Arial", 12, "bold"),
                bg="#f0f0f0").pack(side="left", padx=5)
        
        self.client_type_info_label = tk.Label(client_type_info_frame, 
                text="(Seleccione un grupo primero)", 
                font=("Arial", 10),
                fg="gray", bg="#f0f0f0")
        self.client_type_info_label.pack(side="left", padx=10)
        
        # Info note about management
        info_frame = tk.Frame(client_type_info_frame, bg="#f0f0f0")
        info_frame.pack(side="right")
        
        tk.Label(info_frame, 
                text="🔧 Para editar grupos/tipos, usar 'Administrador de Clientes'", 
                font=("Arial", 9, "italic"),
                fg="#666", bg="#f0f0f0").pack()
        
        # Search and actions frame
        action_frame = tk.Frame(main_frame, bg="#f0f0f0")
        action_frame.pack(fill="x", pady=10)
        
        # Search
        search_frame = tk.Frame(action_frame, bg="#f0f0f0")
        search_frame.pack(side="left")
        
        tk.Label(search_frame, 
                text="3. 🔍 Buscar producto:", 
                font=("Arial", 12),
                bg="#f0f0f0").pack(side="left")
        
        self.search_entry = tk.Entry(search_frame, width=30, font=("Arial", 11))
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self.filter_products)
        
        tk.Button(search_frame, 
                 text="Limpiar", 
                 command=self.clear_search,
                 bg="#95A5A6", fg="white", padx=10).pack(side="left", padx=5)
        
        # Buttons
        btn_frame = tk.Frame(action_frame, bg="#f0f0f0")
        btn_frame.pack(side="right")
        
        tk.Button(btn_frame, 
                 text="➕ Agregar Producto", 
                 command=self.add_product_dialog,
                 bg="#2ECC71", fg="white", padx=15, pady=3).pack(side="left", padx=5)
        
        tk.Button(btn_frame, 
                 text="✏️ Editar Precio Base", 
                 command=self.edit_selected_price,
                 bg="#3498DB", fg="white", padx=15, pady=3).pack(side="left", padx=5)
        
        tk.Button(btn_frame, 
                 text="🗑️ Eliminar Producto", 
                 command=self.delete_product,
                 bg="#E74C3C", fg="white", padx=15, pady=3).pack(side="left", padx=5)
        
        # Products table
        table_frame = tk.Frame(main_frame)
        table_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        # Create treeview with scrollbars
        self.create_products_table(table_frame)

        # Bottom buttons frame (NEW - Added Save and Cancel buttons)
        bottom_buttons_frame = tk.Frame(main_frame, bg="#f0f0f0")
        bottom_buttons_frame.pack(fill="x", pady=(10, 0))
        
        tk.Button(bottom_buttons_frame,
                 text="💾 Guardar Cambios",
                 command=self.save_changes,
                 bg="#27AE60", fg="white", padx=15, pady=5).pack(side="left", padx=5)
        
        tk.Button(bottom_buttons_frame,
                 text="❌ Cancelar Cambios",
                 command=self.cancel_changes,
                 bg="#E74C3C", fg="white", padx=15, pady=5).pack(side="right", padx=5)
        
        # Bottom info frame
        info_bottom_frame = tk.Frame(main_frame, bg="#f0f0f0")
        info_bottom_frame.pack(fill="x", pady=(10, 0))
        
        tk.Label(info_bottom_frame, 
                text="💡 Tip: Doble clic en un producto para editar precio base del grupo | Los descuentos se aplican según el tipo de cliente", 
                font=("Arial", 9, "italic"),
                fg="#666", bg="#f0f0f0").pack(side="left")
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Listo")
        status_bar = tk.Label(self.root, 
                            textvariable=self.status_var,
                            bd=1, relief=tk.SUNKEN, 
                            anchor=tk.W,
                            font=("Arial", 9))
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def save_changes(self):
        """Guardar todos los cambios realizados"""
        try:
            self.conn.commit()
            self.changes_made = False
            messagebox.showinfo("Éxito", "Todos los cambios han sido guardados correctamente")
            self.status_var.set("Cambios guardados correctamente")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron guardar los cambios: {str(e)}")
            self.status_var.set("Error al guardar cambios")

    def cancel_changes(self):
        """Cancelar todos los cambios no guardados"""
        if self.changes_made:
            if messagebox.askyesno("Confirmar", "¿Está seguro que desea descartar todos los cambios no guardados?"):
                try:
                    self.conn.rollback()
                    self.changes_made = False
                    self.load_products()  # Recargar datos originales
                    self.status_var.set("Cambios cancelados - Se recargaron los datos originales")
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudieron cancelar los cambios: {str(e)}")
        else:
            messagebox.showinfo("Información", "No hay cambios pendientes por guardar")
            
    def create_products_table(self, parent):
        """Crear tabla de productos con scrollbars"""
        # Frame for scrollbars
        scroll_frame = tk.Frame(parent)
        scroll_frame.pack(fill="both", expand=True)
        
        # Vertical scrollbar
        v_scrollbar = tk.Scrollbar(scroll_frame, orient="vertical")
        v_scrollbar.pack(side="right", fill="y")
        
        # Horizontal scrollbar
        h_scrollbar = tk.Scrollbar(scroll_frame, orient="horizontal")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Treeview
        self.product_tree = ttk.Treeview(
            scroll_frame,
            columns=("id", "nombre", "unidad", "precio_base", "clientes_afectados", "stock", "especial"),
            show="headings",
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set
        )
        
        # Configure columns
        columns_config = {
            "id": ("ID", 50, "center"),
            "nombre": ("Producto", 280, "w"),
            "unidad": ("Unidad", 80, "center"),
            "precio_base": ("Precio Base", 120, "e"),
            "clientes_afectados": ("Clientes Afectados", 150, "center"),
            "stock": ("Stock", 80, "e"),
            "especial": ("Especial", 80, "center")
        }
        
        for col, (heading, width, anchor) in columns_config.items():
            self.product_tree.heading(col, text=heading)
            self.product_tree.column(col, width=width, anchor=anchor)
        
        self.product_tree.pack(fill="both", expand=True)
        
        # Configure scrollbars
        v_scrollbar.config(command=self.product_tree.yview)
        h_scrollbar.config(command=self.product_tree.xview)
        
        # Bind events
        self.product_tree.bind("<Double-1>", self.edit_product_price)
        self.product_tree.bind("<ButtonRelease-1>", self.on_product_select)
    
    def on_product_select(self, event):
        """Manejar selección de producto"""
        selected_item = self.product_tree.focus()
        if selected_item:
            values = self.product_tree.item(selected_item, "values")
            if values:
                product_name = values[1]
                self.status_var.set(f"Producto seleccionado: {product_name}")
    
    def clear_search(self):
        """Limpiar campo de búsqueda"""
        self.search_entry.delete(0, tk.END)
        self.load_products()
    
    def edit_selected_price(self):
        """Editar precio del producto seleccionado"""
        selected_item = self.product_tree.focus()
        if not selected_item:
            messagebox.showwarning("Advertencia", "Por favor seleccione un producto para editar")
            return
        
        # Llamar al método de edición existente
        self.edit_product_price(None)
    
    def load_groups(self):
        """Cargar grupos desde la base de datos"""
        for widget in self.group_buttons_frame.winfo_children():
            widget.destroy()
        
        self.cursor.execute("SELECT id_grupo, clave_grupo FROM grupo ORDER BY clave_grupo")
        self.groups = self.cursor.fetchall()
        
        for group in self.groups:
            rb = tk.Radiobutton(
                self.group_buttons_frame,
                text=f"{group['clave_grupo']}",
                variable=self.current_group,
                value=group['id_grupo'],
                command=self.on_group_change,
                bg="#f0f0f0",
                font=("Arial", 10)
            )
            rb.pack(side="left", padx=5)
            
    def load_client_types(self):
        """Cargar tipos de cliente desde la base de datos"""
        self.cursor.execute("SELECT id_tipo_cliente, nombre_tipo, descuento FROM tipo_cliente ORDER BY nombre_tipo")
        self.client_types = self.cursor.fetchall()
        
    def on_group_change(self):
        """Manejar cambio de grupo seleccionado"""
        self.update_client_type_info()
        self.load_products()
        
    def update_client_type_info(self):
        """Actualizar información de tipos de cliente"""
        group_id = self.current_group.get()
        
        # Get the client type associated with this group
        self.cursor.execute("""
            SELECT tc.nombre_tipo, tc.descuento, COUNT(c.id_cliente) as num_clientes
            FROM grupo g
            JOIN tipo_cliente tc ON g.id_tipo_cliente = tc.id_tipo_cliente
            LEFT JOIN cliente c ON c.id_grupo = g.id_grupo
            WHERE g.id_grupo = %s
            GROUP BY tc.id_tipo_cliente, tc.nombre_tipo, tc.descuento
        """, (group_id,))
        
        result = self.cursor.fetchone()
        
        if result:
            type_info = f"Tipo: {result['nombre_tipo']} (Descuento: {result['descuento']}%) - {result['num_clientes']} clientes"
            self.client_type_info_label.config(text=type_info, fg="blue")
        else:
            self.client_type_info_label.config(text="(Grupo sin tipo de cliente asignado)", fg="red")
    
    def load_products(self):
        """Cargar productos desde la base de datos"""
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)
            
        group_id = self.current_group.get()
        
        # Get all products with their base prices for the selected group
        self.cursor.execute("""
            SELECT p.id_producto, p.nombre_producto, p.unidad_producto, p.stock, p.es_especial,
                   ppg.precio_base
            FROM producto p
            LEFT JOIN precio_por_grupo ppg ON p.id_producto = ppg.id_producto AND ppg.id_grupo = %s
            ORDER BY p.nombre_producto
        """, (group_id,))
        self.all_products = self.cursor.fetchall()
        
        # Get clients count in this group
        self.cursor.execute("""
            SELECT COUNT(*) as client_count
            FROM cliente c
            WHERE c.id_grupo = %s
        """, (group_id,))
        client_count_result = self.cursor.fetchone()
        client_count = client_count_result['client_count'] if client_count_result else 0
        
        for product in self.all_products:
            precio_base = product['precio_base'] if product['precio_base'] else Decimal('0.00')
            
            # Color coding for special products
            tags = ()
            if product['es_especial']:
                tags = ('special',)
            
            # Color coding for products without price
            if precio_base == 0:
                tags = tags + ('no_price',)
            
            self.product_tree.insert("", "end",
                values=(
                    product["id_producto"],
                    product["nombre_producto"],
                    product["unidad_producto"],
                    f"${precio_base:.2f}" if precio_base > 0 else "Sin precio",
                    f"{client_count} clientes",
                    f"{product['stock']:.2f}",
                    "🔒 Sí" if product['es_especial'] else "No"
                ),
                tags=tags
            )
        
        # Configure tags for special products and products without price
        self.product_tree.tag_configure('special', background='#FFE5B4')
        self.product_tree.tag_configure('no_price', background='#FFE5E5')
        
        group_name = self.get_current_group_name()
        self.status_var.set(f"Mostrando {len(self.all_products)} productos para grupo: {group_name}")
    
    def get_current_group_name(self):
        """Obtener nombre del grupo actual"""
        group_id = self.current_group.get()
        group = next((g for g in self.groups if g['id_grupo'] == group_id), None)
        return group['clave_grupo'] if group else "Desconocido"
    
    def filter_products(self, event=None):
        """Filtrar productos por búsqueda"""
        search_text = self.search_entry.get().lower()
        
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)
        
        if not search_text:
            self.load_products()
            return
        
        group_id = self.current_group.get()
        
        # Get clients count in this group
        self.cursor.execute("""
            SELECT COUNT(*) as client_count
            FROM cliente c
            WHERE c.id_grupo = %s
        """, (group_id,))
        client_count_result = self.cursor.fetchone()
        client_count = client_count_result['client_count'] if client_count_result else 0
        
        filtered_count = 0
        for product in self.all_products:
            if search_text in product["nombre_producto"].lower():
                precio_base = product['precio_base'] if product['precio_base'] else Decimal('0.00')
                
                tags = ()
                if product['es_especial']:
                    tags = ('special',)
                
                # Color coding for products without price
                if precio_base == 0:
                    tags = tags + ('no_price',)
                
                self.product_tree.insert("", "end",
                    values=(
                        product["id_producto"],
                        product["nombre_producto"],
                        product["unidad_producto"],
                        f"${precio_base:.2f}" if precio_base > 0 else "Sin precio",
                        f"{client_count} clientes",
                        f"{product['stock']:.2f}",
                        "🔒 Sí" if product['es_especial'] else "No"
                    ),
                    tags=tags
                )
                filtered_count += 1
        
        self.product_tree.tag_configure('special', background='#FFE5B4')
        self.product_tree.tag_configure('no_price', background='#FFE5E5')
        self.status_var.set(f"Filtrado: {filtered_count} productos encontrados")
    
    def add_product_dialog(self):
        """Mostrar popup para agregar nuevo producto"""
        popup = tk.Toplevel(self.root)
        popup.title("Agregar Producto")
        popup.geometry("450x400")
        popup.transient(self.root)
        popup.grab_set()
        
        # Variables
        name_var = tk.StringVar()
        unit_var = tk.StringVar()
        price_var = tk.StringVar()
        stock_var = tk.StringVar(value="0")
        special_var = tk.BooleanVar(value=False)
        
        # Frame principal
        main_frame = tk.Frame(popup, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Título
        tk.Label(main_frame, text="➕ Agregar Nuevo Producto", 
                font=("Arial", 14, "bold")).pack(pady=(0, 15))
        
        # Campos del formulario
        fields = [
            ("Nombre del Producto:", name_var, "entry"),
            ("Unidad de Medida:", unit_var, "combo"),
            ("Stock Inicial:", stock_var, "entry")
        ]
        
        for i, (label, var, widget_type) in enumerate(fields):
            frame = tk.Frame(main_frame)
            frame.pack(fill="x", pady=5)
            
            tk.Label(frame, text=label, width=18, anchor="w").pack(side="left")
            
            if widget_type == "combo" and label == "Unidad de Medida:":
                combo = ttk.Combobox(frame, textvariable=var, width=25,
                            values=["kg", "g", "lb", "pz", "unidad", "L", "ml", "docena", "paquete", "manojo", "caja", "botella"])
                combo.pack(side="left", fill="x", expand=True, padx=(5, 0))
                if i == 0:  # First field gets focus
                    combo.focus_set()
            else:
                entry = tk.Entry(frame, textvariable=var, width=25)
                entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
                if i == 0:  # First field gets focus
                    entry.focus_set()
        
        # Checkbox para producto especial
        special_frame = tk.Frame(main_frame)
        special_frame.pack(fill="x", pady=10)
        
        check = tk.Checkbutton(special_frame, 
                     text="🔒 Producto Especial (requiere permisos de administrador)",
                     variable=special_var,
                     font=("Arial", 10))
        check.pack(side="left")
        
        # Botones
        button_frame = tk.Frame(main_frame)
        button_frame.pack(side="bottom", fill="x", pady=(20, 0))
        
        tk.Button(button_frame, 
                text="💾 Guardar", 
                command=lambda: self.save_new_product(popup, name_var.get(), unit_var.get(), 
                                                    stock_var.get(), special_var.get()),
                bg="#4CAF50", fg="white", width=12, pady=5).pack(side="left", padx=5)
        
        tk.Button(button_frame, 
                text="❌ Cancelar", 
                command=popup.destroy,
                bg="#F44336", fg="white", width=12, pady=5).pack(side="right", padx=5)
        
        # Centrar popup
        self.center_popup(popup)
    
    def center_popup(self, popup):
        """Centrar popup en pantalla"""
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (width // 2)
        y = (popup.winfo_screenheight() // 2) - (height // 2)
        popup.geometry(f'{width}x{height}+{x}+{y}')
    
    def save_new_product(self, popup, name, unit, stock, is_special):
        """Guardar nuevo producto en la base de datos"""
        # Validaciones
        if not name.strip():
            messagebox.showerror("Error", "El nombre del producto es obligatorio", parent=popup)
            return
            
        if not unit.strip():
            messagebox.showerror("Error", "La unidad de medida es obligatoria", parent=popup)
            return
        
        try:
            stock = Decimal(stock)
            if stock < 0:
                messagebox.showerror("Error", "El stock no puede ser negativo", parent=popup)
                return
        except:
            messagebox.showerror("Error", "Ingrese un valor de stock válido", parent=popup)
            return
        
        # Verificar permisos para productos especiales
        if is_special and not self.es_admin:
            if not self.verify_admin_password("crear producto especial"):
                return
        
        try:
            self.cursor.execute("""
                INSERT INTO producto (nombre_producto, unidad_producto, stock, es_especial)
                VALUES (%s, %s, %s, %s)
            """, (name.strip(), unit.strip(), stock, is_special))
            
            self.conn.commit()
            self.changes_made = True
            popup.destroy()
            self.load_products()
            self.status_var.set(f"✅ Producto '{name}' agregado correctamente. Use 'Editar Precio' para asignar precio base para el grupo.")
            
        except mysql.connector.Error as err:
            self.conn.rollback()
            if err.errno == 1062:  # Duplicate entry
                messagebox.showerror("Error", "Ya existe un producto con ese nombre", parent=popup)
            else:
                messagebox.showerror("Error", f"Error al guardar producto: {err}", parent=popup)
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error inesperado: {str(e)}", parent=popup)
    
    def edit_product_price(self, event):
        """Editar precio base de un producto para el grupo seleccionado"""
        item = self.product_tree.focus()
        if not item:
            messagebox.showwarning("Advertencia", "Por favor seleccione un producto para editar")
            return
            
        values = self.product_tree.item(item, "values")
        product_id = values[0]
        product_name = values[1]
        product_unit = values[2]
        current_price = values[3]
        current_stock = values[5]
        is_special = "🔒" in values[6]
        
        # Verificar permisos para productos especiales
        if is_special and not self.es_admin:
            if not self.verify_admin_password(f"editar {product_name}"):
                return
        
        popup = tk.Toplevel(self.root)
        popup.title(f"Editar Precio Base - {product_name}")
        popup.geometry("600x600")
        popup.transient(self.root)
        popup.grab_set()
        
        # Frame principal
        main_frame = tk.Frame(popup, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Título
        group_name = self.get_current_group_name()
        title_text = f"✏️ Editar Precio Base para Grupo: {group_name}"
        if is_special:
            title_text += " (Producto Especial)"
        tk.Label(main_frame, text=title_text, font=("Arial", 14, "bold")).pack(pady=(0, 15))
        
        # Info del producto
        info_frame = tk.LabelFrame(main_frame, text="Información del Producto", padx=10, pady=10)
        info_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(info_frame, text=f"Producto: {product_name}", font=("Arial", 10)).pack(anchor="w")
        tk.Label(info_frame, text=f"Unidad: {product_unit}", font=("Arial", 10)).pack(anchor="w")
        tk.Label(info_frame, text=f"Stock actual: {current_stock}", font=("Arial", 10)).pack(anchor="w")
        tk.Label(info_frame, text=f"Precio base actual: {current_price}", font=("Arial", 10, "bold"), fg="blue").pack(anchor="w")
        if is_special:
            tk.Label(info_frame, text="🔒 Producto Especial", font=("Arial", 10, "bold"), fg="red").pack(anchor="w")
        
        # Precio base
        price_frame = tk.LabelFrame(main_frame, text="Precio Base del Grupo", padx=10, pady=10)
        price_frame.pack(fill="x", pady=(0, 15))
        
        # Obtener precio actual
        group_id = self.current_group.get()
        self.cursor.execute("""
            SELECT precio_base FROM precio_por_grupo 
            WHERE id_producto = %s AND id_grupo = %s
        """, (product_id, group_id))
        result = self.cursor.fetchone()
        current_base_price = result['precio_base'] if result else Decimal('0.00')
        
        price_input_frame = tk.Frame(price_frame)
        price_input_frame.pack(fill="x", pady=10)
        
        tk.Label(price_input_frame, text="Precio Base:", width=15, anchor="w", font=("Arial", 12, "bold")).pack(side="left")
        tk.Label(price_input_frame, text="$", font=("Arial", 12, "bold")).pack(side="left", padx=(5, 0))
        
        price_var = tk.StringVar(value=str(current_base_price))
        price_entry = tk.Entry(price_input_frame, textvariable=price_var, font=("Arial", 12), width=15)
        price_entry.pack(side="left", padx=(2, 0))
        price_entry.focus_set()
        
        # Precios finales por tipo de cliente
        preview_frame = tk.LabelFrame(main_frame, text="Vista Previa: Precios Finales por Tipo de Cliente", padx=10, pady=10)
        preview_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Obtener el tipo de cliente del grupo actual
        self.cursor.execute("""
            SELECT tc.nombre_tipo, tc.descuento
            FROM grupo g
            JOIN tipo_cliente tc ON g.id_tipo_cliente = tc.id_tipo_cliente
            WHERE g.id_grupo = %s
        """, (group_id,))
        client_type_info = self.cursor.fetchone()
        
        preview_labels = []
        
        def update_preview():
            try:
                base_price = Decimal(price_var.get().strip()) if price_var.get().strip() else Decimal('0')
                for label in preview_labels:
                    label.destroy()
                preview_labels.clear()
                
                if base_price > 0 and client_type_info:
                    discount = client_type_info['descuento']
                    final_price = base_price * (1 - discount / 100)
                    
                    label = tk.Label(preview_frame, 
                                   text=f"{client_type_info['nombre_tipo']}: ${final_price:.2f} (descuento: {discount}%)",
                                   font=("Arial", 10))
                    label.pack(anchor="w", pady=2)
                    preview_labels.append(label)
                elif base_price > 0 and not client_type_info:
                    label = tk.Label(preview_frame, 
                                   text=f"Precio sin descuento: ${base_price:.2f} (grupo sin tipo de cliente asignado)",
                                   font=("Arial", 10), fg="orange")
                    label.pack(anchor="w", pady=2)
                    preview_labels.append(label)
                else:
                    label = tk.Label(preview_frame, text="Ingrese un precio base para ver la vista previa", 
                                   font=("Arial", 10), fg="gray")
                    label.pack(anchor="w")
                    preview_labels.append(label)
            except:
                pass
        
        price_var.trace('w', lambda *args: update_preview())
        update_preview()
        
        # Botones
        button_frame = tk.Frame(main_frame)
        button_frame.pack(side="bottom", fill="x", pady=(15, 0))
        
        def save_changes():
            try:
                # Validar precio
                try:
                    price = Decimal(price_var.get().strip())
                    if price < 0:
                        messagebox.showerror("Error", "El precio no puede ser negativo", parent=popup)
                        return
                except:
                    messagebox.showerror("Error", "Ingrese un precio válido", parent=popup)
                    return
                
                # Guardar precio
                if price > 0:
                    # Insertar o actualizar precio
                    self.cursor.execute("""
                        INSERT INTO precio_por_grupo (id_grupo, id_producto, precio_base)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE precio_base = VALUES(precio_base)
                    """, (group_id, product_id, price))
                else:
                    # Eliminar precio si es 0
                    self.cursor.execute("""
                        DELETE FROM precio_por_grupo 
                        WHERE id_grupo = %s AND id_producto = %s
                    """, (group_id, product_id))
                
                self.conn.commit()
                self.changes_made = True
                popup.destroy()
                self.load_products()
                self.status_var.set(f"✅ Precio base de '{product_name}' actualizado correctamente para grupo '{group_name}'")
                
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror("Error", f"Error al actualizar: {str(e)}", parent=popup)
        
        tk.Button(button_frame, 
                text="💾 Guardar Cambios", 
                command=save_changes,
                bg="#4CAF50", fg="white", width=15, pady=5).pack(side="left", padx=5)
        
        tk.Button(button_frame, 
                text="❌ Cancelar", 
                command=popup.destroy,
                bg="#F44336", fg="white", width=15, pady=5).pack(side="right", padx=5)
        
        # Centrar popup
        self.center_popup(popup)
    
    def delete_product(self):
        """Eliminar un producto"""
        item = self.product_tree.focus()
        if not item:
            messagebox.showwarning("Advertencia", "Seleccione un producto para eliminar")
            return
            
        values = self.product_tree.item(item, "values")
        product_id = values[0]
        product_name = values[1]
        is_special = "🔒" in values[6]
        
        # Verificar permisos para productos especiales
        if is_special and not self.es_admin:
            if not self.verify_admin_password(f"eliminar {product_name}"):
                return
        
        if not messagebox.askyesno("Confirmar Eliminación", 
                                 f"¿Eliminar el producto '{product_name}'?\n\n"
                                 f"Esta acción no se puede deshacer."):
            return
            
        try:
            # Verificar si el producto está en facturas
            self.cursor.execute("""
                SELECT COUNT(*) as count FROM detalle_factura WHERE id_producto = %s
            """, (product_id,))
            result = self.cursor.fetchone()
            
            if result['count'] > 0:
                confirm = messagebox.askyesno(
                    "⚠️ Advertencia", 
                    f"Este producto aparece en {result['count']} facturas.\n\n"
                    f"Si lo elimina, podría afectar los reportes históricos.\n"
                    f"¿Eliminar de todos modos?"
                )
                if not confirm:
                    return
            
            # Eliminar producto (los triggers y foreign keys se encargan del resto)
            self.cursor.execute("DELETE FROM producto WHERE id_producto = %s", (product_id,))
            self.conn.commit()
            self.changes_made = True
            self.load_products()
            self.status_var.set(f"🗑️ Producto '{product_name}' eliminado")
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"No se pudo eliminar: {str(e)}")
    
    def verify_admin_password(self, action):
        """Verificar contraseña de administrador para productos especiales"""
        class AdminPasswordDialog:
            def __init__(self, parent, action):
                self.result = False
                self.dialog = tk.Toplevel(parent)
                self.dialog.title("Autenticación Requerida")
                self.dialog.geometry("400x250")
                self.dialog.transient(parent)
                self.dialog.grab_set()
                
                # Main frame
                main_frame = tk.Frame(self.dialog, padx=20, pady=20)
                main_frame.pack(fill="both", expand=True)
                
                # Title
                tk.Label(main_frame, text="🔒 Autorización Requerida", 
                        font=("Arial", 14, "bold"), fg="#E74C3C").pack(pady=(0, 10))
                
                # Message
                tk.Label(main_frame, 
                        text=f"Para {action} se requieren\npermisos de administrador.",
                        font=("Arial", 11), justify="center").pack(pady=(0, 15))
                
                # Credentials
                cred_frame = tk.Frame(main_frame)
                cred_frame.pack(fill="x", pady=10)
                
                tk.Label(cred_frame, text="Usuario:", font=("Arial", 10)).pack(anchor="w")
                self.username_var = tk.StringVar()
                self.username_entry = tk.Entry(cred_frame, textvariable=self.username_var, width=30)
                self.username_entry.pack(fill="x", pady=(0, 10))
                
                tk.Label(cred_frame, text="Contraseña:", font=("Arial", 10)).pack(anchor="w")
                self.password_var = tk.StringVar()
                self.password_entry = tk.Entry(cred_frame, textvariable=self.password_var, show="*", width=30)
                self.password_entry.pack(fill="x")
                
                # Buttons
                button_frame = tk.Frame(main_frame)
                button_frame.pack(side="bottom", fill="x", pady=(15, 0))
                
                tk.Button(button_frame, text="Verificar", command=self.verify,
                         bg="#4CAF50", fg="white", padx=15, pady=5).pack(side="left", padx=5)
                tk.Button(button_frame, text="Cancelar", command=self.cancel,
                         bg="#f44336", fg="white", padx=15, pady=5).pack(side="right", padx=5)
                
                # Focus and bindings
                self.username_entry.focus_set()
                self.password_entry.bind("<Return>", lambda e: self.verify())
                self.dialog.bind("<Escape>", lambda e: self.cancel())
                
                # Center dialog
                self.dialog.update_idletasks()
                width = self.dialog.winfo_width()
                height = self.dialog.winfo_height()
                x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
                y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
                self.dialog.geometry(f'{width}x{height}+{x}+{y}')
                
                # Make modal
                self.dialog.wait_window()
            
            def verify(self):
                username = self.username_var.get().strip()
                password = self.password_var.get().strip()
                
                if not username or not password:
                    messagebox.showerror("Error", "Por favor ingrese usuario y contraseña", parent=self.dialog)
                    return
                
                try:
                    from src.auth.auth_manager import AuthManager
                    auth_manager = AuthManager()
                    auth_result = auth_manager.authenticate(username, password)
                    
                    if auth_result['success'] and auth_result['user_data']['rol'] == 'admin':
                        self.result = True
                        self.dialog.destroy()
                        return
                    
                    messagebox.showerror("Error", "Credenciales incorrectas o permisos insuficientes", parent=self.dialog)
                    self.password_entry.delete(0, tk.END)
                    self.password_entry.focus_set()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Error de autenticación: {str(e)}", parent=self.dialog)
            
            def cancel(self):
                self.result = False
                self.dialog.destroy()
        
        # Create and show dialog
        dialog = AdminPasswordDialog(self.root, action)
        return dialog.result
    
    def on_closing(self):
        """Manejar el cierre de la ventana"""
        if self.changes_made:
            result = messagebox.askyesnocancel("Cambios sin guardar", 
                                              "Hay cambios sin guardar. ¿Desea guardarlos antes de salir?")
            if result is True:  # Yes - save
                try:
                    self.conn.commit()
                    self.conn.close()
                    self.root.destroy()
                except:
                    messagebox.showerror("Error", "Error al guardar cambios")
                    return
            elif result is False:  # No - don't save
                try:
                    self.conn.rollback()
                    self.conn.close()
                    self.root.destroy()
                except:
                    self.root.destroy()
            # Cancel - do nothing, stay open
        else:
            try:
                self.conn.close()
            except:
                pass
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    # Datos de usuario de prueba
    user_data = {
        'nombre_completo': 'Usuario Prueba',
        'rol': 'admin'  # Cambiar a 'usuario' para probar sin permisos admin
    }
    app = PriceEditorApp(root, user_data)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()