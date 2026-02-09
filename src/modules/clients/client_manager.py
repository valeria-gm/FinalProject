import os
import tkinter as tk
from tkinter import messagebox, ttk
import mysql.connector
from src.database.conexion import conectar
from tkinter import simpledialog
import re

class ClientManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Administrador de Clientes - Disfruleg")
        self.root.geometry("800x600")
        
        # Connect to database
        self.conn = conectar()
        self.cursor = self.conn.cursor(dictionary=True)

        # Inicializar las listas antes de cargar los datos
        self.groups = []
        self.client_types = []
        
        # Load groups and client types
        self.load_groups()
        self.load_client_types()
        
        # Variables
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_clients)
        
        self.create_interface()
        self.load_clients()
        
    def load_groups(self):
        """Load groups from database with their associated client types"""
        self.cursor.execute("""
            SELECT g.id_grupo, g.clave_grupo, g.descripcion, g.id_tipo_cliente,
                   tc.nombre_tipo, tc.descuento
            FROM grupo g
            LEFT JOIN tipo_cliente tc ON g.id_tipo_cliente = tc.id_tipo_cliente
            ORDER BY g.clave_grupo
        """)
        self.groups = self.cursor.fetchall()
        
    def load_client_types(self):
        """Load client types from database"""
        self.cursor.execute("SELECT id_tipo_cliente, nombre_tipo, descuento FROM tipo_cliente ORDER BY nombre_tipo")
        self.client_types = self.cursor.fetchall()
        
    def create_interface(self):
        """Create the user interface"""
        # Title
        title_frame = tk.Frame(self.root)
        title_frame.pack(fill="x", pady=10)
        
        tk.Label(title_frame, text="ADMINISTRADOR DE CLIENTES", font=("Arial", 18, "bold")).pack()
        
        # Search and actions frame
        action_frame = tk.Frame(self.root)
        action_frame.pack(fill="x", pady=5, padx=10)
        
        # Search section
        search_frame = tk.Frame(action_frame)
        search_frame.pack(side="left", fill="x", expand=True)
        
        tk.Label(search_frame, text="Buscar:", font=("Arial", 12)).pack(side="left", padx=5)
        self.search_entry = tk.Entry(search_frame, width=30, textvariable=self.search_var)
        self.search_entry.pack(side="left", padx=5)
        
        # Buttons section
        buttons_frame = tk.Frame(action_frame)
        buttons_frame.pack(side="right")
        
        tk.Button(buttons_frame, text="Agregar Cliente", command=self.add_client_dialog, 
                  bg="#2196F3", fg="white", padx=10, pady=3).pack(side="left", padx=5)
        tk.Button(buttons_frame, text="Editar Cliente", command=self.edit_client_dialog, 
                  bg="#FFA500", fg="white", padx=10, pady=3).pack(side="left", padx=5)
        tk.Button(buttons_frame, text="Eliminar Cliente", command=self.delete_client, 
                  bg="#f44336", fg="white", padx=10, pady=3).pack(side="left", padx=5)
        
        # Clients table
        table_frame = tk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(table_frame)
        scrollbar.pack(side="right", fill="y")
        
        # Treeview for clients
        self.client_tree = ttk.Treeview(table_frame, 
                                      columns=("id", "nombre", "telefono", "correo", "grupo", "tipo_cliente", "descuento"),
                                      show="headings", 
                                      yscrollcommand=scrollbar.set)
        
        # Configure columns
        self.client_tree.heading("id", text="ID")
        self.client_tree.heading("nombre", text="Nombre")
        self.client_tree.heading("telefono", text="Teléfono")
        self.client_tree.heading("correo", text="Correo")
        self.client_tree.heading("grupo", text="Grupo")
        self.client_tree.heading("tipo_cliente", text="Tipo Cliente")
        self.client_tree.heading("descuento", text="Descuento (%)")
        
        self.client_tree.column("id", width=50)
        self.client_tree.column("nombre", width=150)
        self.client_tree.column("telefono", width=100)
        self.client_tree.column("correo", width=150)
        self.client_tree.column("grupo", width=100)
        self.client_tree.column("tipo_cliente", width=120)
        self.client_tree.column("descuento", width=80)
        
        self.client_tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.client_tree.yview)
        
        # Double-click to edit
        self.client_tree.bind("<Double-1>", lambda event: self.edit_client_dialog())
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Listo")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Add group and type manager buttons
        manager_button_frame = tk.Frame(self.root)
        manager_button_frame.pack(fill="x", pady=5, padx=10)
        
        tk.Button(manager_button_frame, text="Administrar Grupos", 
                 command=self.manage_groups,
                 bg="#673AB7", fg="white", padx=10, pady=3).pack(side="left")
        
        tk.Button(manager_button_frame, text="Administrar Tipos", 
                 command=self.manage_client_types,
                 bg="#009688", fg="white", padx=10, pady=3).pack(side="left", padx=5)
        
    def load_clients(self):
        """Load clients from database"""
        # Clear existing items
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)
            
        # Get clients with group and client type info using the new schema
        self.cursor.execute("""
            SELECT c.id_cliente, c.nombre_cliente, c.telefono, c.correo, 
                   g.clave_grupo, tc.nombre_tipo, tc.descuento, c.id_grupo
            FROM cliente c
            JOIN grupo g ON c.id_grupo = g.id_grupo
            JOIN tipo_cliente tc ON g.id_tipo_cliente = tc.id_tipo_cliente
            ORDER BY c.nombre_cliente
        """)
        
        clients = self.cursor.fetchall()
        
        # Store all clients for reference and filtering
        self.all_clients = clients
        
         # Insert clients into treeview
        for client in clients:
            telefono = client.get('telefono', '') or '---'
            correo = client.get('correo', '') or '---'
            grupo = client.get('clave_grupo', '') or '---'
            tipo_cliente = client.get('nombre_tipo', '') or '---'
            descuento = client.get('descuento', '') or '---'
            
            self.client_tree.insert("", "end", 
                                  values=(client["id_cliente"], 
                                         client["nombre_cliente"], 
                                         telefono,
                                         correo,
                                         grupo,
                                         tipo_cliente,
                                         descuento),
                                  tags=(str(client.get('id_grupo', '')),))
            
        self.status_var.set(f"Mostrando {len(clients)} clientes")
    
    def filter_clients(self, *args):
        """Filter clients based on search text"""
        search_text = self.search_var.get().lower()
        
        # Clear existing items
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)
        
        # Filter clients
        for client in self.all_clients:
            # Search in name, phone, email, group and client type
            if (search_text in client["nombre_cliente"].lower() or 
                (client.get('telefono') and search_text in client.get('telefono').lower()) or
                (client.get('correo') and search_text in client.get('correo', '').lower()) or
                (client.get('clave_grupo') and search_text in client.get('clave_grupo', '').lower()) or
                (client.get('nombre_tipo') and search_text in client.get('nombre_tipo', '').lower())):
                
                telefono = client.get('telefono', '') or '---'
                correo = client.get('correo', '') or '---'
                grupo = client.get('clave_grupo', '') or '---'
                tipo_cliente = client.get('nombre_tipo', '') or '---'
                descuento = client.get('descuento', '') or '---'
                
                self.client_tree.insert("", "end", 
                                      values=(client["id_cliente"], 
                                             client["nombre_cliente"], 
                                             telefono,
                                             correo,
                                             grupo,
                                             tipo_cliente,
                                             descuento),
                                      tags=(str(client.get('id_grupo', '')),))
    
    def validate_email(self, email):
        """Validate email format"""
        if not email:
            return True  # Email is optional
        
        # Basic email validation pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email) is not None
    
    def add_client_dialog(self):
        """Open dialog to add a new client"""
        # Create popup
        popup = tk.Toplevel(self.root)
        popup.title("Agregar Nuevo Cliente")
        popup.geometry("500x450")
        popup.transient(self.root)
        popup.grab_set()
        
        # Center popup
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (width // 2)
        y = (popup.winfo_screenheight() // 2) - (height // 2)
        popup.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        # Title
        tk.Label(popup, text="Agregar Nuevo Cliente", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Form frame
        form_frame = tk.Frame(popup)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Name field (REQUIRED)
        name_frame = tk.Frame(form_frame)
        name_frame.pack(fill="x", pady=5)
        name_label = tk.Label(name_frame, text="Nombre: *", width=15, anchor="w", fg="#d32f2f")
        name_label.pack(side="left")
        name_entry = tk.Entry(name_frame, width=30)
        name_entry.pack(side="left", fill="x", expand=True)
        name_entry.focus_set()
        
        # Name validation label
        name_error_label = tk.Label(form_frame, text="", fg="#d32f2f", font=("Arial", 9))
        name_error_label.pack(fill="x")
        
        # Phone field (OPTIONAL)
        phone_frame = tk.Frame(form_frame)
        phone_frame.pack(fill="x", pady=5)
        tk.Label(phone_frame, text="Teléfono:", width=15, anchor="w").pack(side="left")
        phone_entry = tk.Entry(phone_frame, width=30)
        phone_entry.pack(side="left", fill="x", expand=True)
        
        # Email field (OPTIONAL but validated)
        email_frame = tk.Frame(form_frame)
        email_frame.pack(fill="x", pady=5)
        tk.Label(email_frame, text="Correo:", width=15, anchor="w").pack(side="left")
        email_entry = tk.Entry(email_frame, width=30)
        email_entry.pack(side="left", fill="x", expand=True)
        
        # Email validation label
        email_error_label = tk.Label(form_frame, text="", fg="#d32f2f", font=("Arial", 9))
        email_error_label.pack(fill="x")
        
        # Group field (REQUIRED)
        group_frame = tk.Frame(form_frame)
        group_frame.pack(fill="x", pady=5)
        tk.Label(group_frame, text="Grupo: *", width=15, anchor="w", fg="#d32f2f").pack(side="left")
        
        # Combobox for groups - show group name with client type info
        group_values = [(g['id_grupo'], g['clave_grupo']) for g in self.groups]
        group_names = [g['clave_grupo'] for g in self.groups]
        
        group_var = tk.StringVar()
        group_combo = ttk.Combobox(group_frame, textvariable=group_var, values=group_names, state="readonly")
        group_combo.pack(side="left", fill="x", expand=True)
        if group_names:
            group_combo.current(0)
        
        # Required fields note
        required_note = tk.Label(form_frame, text="* Campos obligatorios", font=("Arial", 9), fg="#666")
        required_note.pack(pady=(10, 0))
        
        # Real-time validation bindings
        def validate_name_real_time(*args):
            name = name_entry.get().strip()
            if not name:
                name_error_label.config(text="")
            elif name:
                name_error_label.config(text="")
        
        def validate_email_real_time(*args):
            email = email_entry.get().strip()
            if not email:
                email_error_label.config(text="")
            elif email and not self.validate_email(email):
                email_error_label.config(text="Formato de correo inválido (debe contener @)")
            else:
                email_error_label.config(text="")
        
        # Bind validation events
        name_entry.bind('<KeyRelease>', validate_name_real_time)
        email_entry.bind('<KeyRelease>', validate_email_real_time)
        
        # Buttons
        button_frame = tk.Frame(popup)
        button_frame.pack(pady=15)
        
        def save_client_with_validation():
            # Clear previous error messages
            name_error_label.config(text="")
            email_error_label.config(text="")
            
            # Get and validate data
            name = name_entry.get().strip()
            phone = phone_entry.get().strip() or None
            email = email_entry.get().strip() or None
            group_name = group_var.get().strip()
            
            is_valid = True
            
            # Validate name (required)
            if not name:
                name_error_label.config(text="El nombre es obligatorio")
                is_valid = False
            
            # Validate email (optional but must be valid if provided)
            if email and not self.validate_email(email):
                email_error_label.config(text="Formato de correo inválido (debe contener @)")
                is_valid = False
            
            if is_valid:
                self.save_client(popup, name, phone, email, group_name, group_values, None)
        
        tk.Button(button_frame, text="Guardar", 
                 command=save_client_with_validation, 
                 bg="#4CAF50", fg="white", padx=10, pady=5).pack(side="left", padx=10)
        
        tk.Button(button_frame, text="Cancelar", 
                 command=popup.destroy, 
                 bg="#f44336", fg="white", padx=10, pady=5).pack(side="left", padx=10)
    
    def edit_client_dialog(self):
        """Open dialog to edit an existing client"""
        # Get selected client
        selected_item = self.client_tree.focus()
        if not selected_item:
            messagebox.showwarning("Advertencia", "Por favor selecciona un cliente para editar")
            return
        
        # Get client data
        values = self.client_tree.item(selected_item, "values")
        client_id = values[0]
        
        # Get client details from database
        self.cursor.execute("""
            SELECT c.id_cliente, c.nombre_cliente, c.telefono, c.correo, c.id_grupo
            FROM cliente c
            WHERE c.id_cliente = %s
        """, (client_id,))
        
        client = self.cursor.fetchone()
        if not client:
            messagebox.showerror("Error", "Cliente no encontrado")
            return
        
        # Create popup
        popup = tk.Toplevel(self.root)
        popup.title("Editar Cliente")
        popup.geometry("500x450")
        popup.transient(self.root)
        popup.grab_set()
        
        # Center popup
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (width // 2)
        y = (popup.winfo_screenheight() // 2) - (height // 2)
        popup.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        # Title
        tk.Label(popup, text="Editar Cliente", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Form frame
        form_frame = tk.Frame(popup)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Name field (REQUIRED)
        name_frame = tk.Frame(form_frame)
        name_frame.pack(fill="x", pady=5)
        name_label = tk.Label(name_frame, text="Nombre: *", width=15, anchor="w", fg="#d32f2f")
        name_label.pack(side="left")
        name_entry = tk.Entry(name_frame, width=30)
        name_entry.pack(side="left", fill="x", expand=True)
        name_entry.insert(0, client["nombre_cliente"])
        name_entry.focus_set()
        
        # Name validation label
        name_error_label = tk.Label(form_frame, text="", fg="#d32f2f", font=("Arial", 9))
        name_error_label.pack(fill="x")
        
        # Phone field (OPTIONAL)
        phone_frame = tk.Frame(form_frame)
        phone_frame.pack(fill="x", pady=5)
        tk.Label(phone_frame, text="Teléfono:", width=15, anchor="w").pack(side="left")
        phone_entry = tk.Entry(phone_frame, width=30)
        phone_entry.pack(side="left", fill="x", expand=True)
        if client.get("telefono"):
            phone_entry.insert(0, client["telefono"])
        
        # Email field (OPTIONAL but validated)
        email_frame = tk.Frame(form_frame)
        email_frame.pack(fill="x", pady=5)
        tk.Label(email_frame, text="Correo:", width=15, anchor="w").pack(side="left")
        email_entry = tk.Entry(email_frame, width=30)
        email_entry.pack(side="left", fill="x", expand=True)
        if client.get("correo"):
            email_entry.insert(0, client["correo"])
        
        # Email validation label
        email_error_label = tk.Label(form_frame, text="", fg="#d32f2f", font=("Arial", 9))
        email_error_label.pack(fill="x")
        
        # Group field (REQUIRED)
        group_frame = tk.Frame(form_frame)
        group_frame.pack(fill="x", pady=5)
        tk.Label(group_frame, text="Grupo: *", width=15, anchor="w", fg="#d32f2f").pack(side="left")
        
        # Combobox for groups
        group_values = [(g['id_grupo'], g['clave_grupo']) for g in self.groups]
        group_names = [g['clave_grupo'] for g in self.groups]
        
        group_var = tk.StringVar()
        group_combo = ttk.Combobox(group_frame, textvariable=group_var, values=group_names, state="readonly")
        group_combo.pack(side="left", fill="x", expand=True)
        
        # Set current group
        if client["id_grupo"]:
            for i, (id_grupo, _) in enumerate(group_values):
                if id_grupo == client["id_grupo"]:
                    group_combo.current(i)
                    break
        
        # Required fields note
        required_note = tk.Label(form_frame, text="* Campos obligatorios", font=("Arial", 9), fg="#666")
        required_note.pack(pady=(10, 0))
        
        # Real-time validation bindings
        def validate_name_real_time(*args):
            name = name_entry.get().strip()
            if not name:
                name_error_label.config(text="")
            elif name:
                name_error_label.config(text="")
        
        def validate_email_real_time(*args):
            email = email_entry.get().strip()
            if not email:
                email_error_label.config(text="")
            elif email and not self.validate_email(email):
                email_error_label.config(text="Formato de correo inválido (debe contener @)")
            else:
                email_error_label.config(text="")
        
        # Bind validation events
        name_entry.bind('<KeyRelease>', validate_name_real_time)
        email_entry.bind('<KeyRelease>', validate_email_real_time)
        
        # Buttons
        button_frame = tk.Frame(popup)
        button_frame.pack(pady=15)
        
        def save_client_with_validation():
            # Clear previous error messages
            name_error_label.config(text="")
            email_error_label.config(text="")
            
            # Get and validate data
            name = name_entry.get().strip()
            phone = phone_entry.get().strip() or None
            email = email_entry.get().strip() or None
            group_name = group_var.get().strip()
            
            is_valid = True
            
            # Validate name (required)
            if not name:
                name_error_label.config(text="El nombre es obligatorio")
                is_valid = False
            
            # Validate email (optional but must be valid if provided)
            if email and not self.validate_email(email):
                email_error_label.config(text="Formato de correo inválido (debe contener @)")
                is_valid = False
            
            if is_valid:
                self.save_client(popup, name, phone, email, group_name, group_values, client_id)

        tk.Button(button_frame, text="Guardar Cambios", 
                 command=save_client_with_validation, 
                 bg="#4CAF50", fg="white", padx=10, pady=5).pack(side="left", padx=10)
        
        tk.Button(button_frame, text="Cancelar", 
                 command=popup.destroy, 
                 bg="#f44336", fg="white", padx=10, pady=5).pack(side="left", padx=10)
    
    def save_client(self, popup, name, phone, email, group_name, group_values, client_id=None):
        """Save client to database (add new or update existing)"""
        # Get group_id from selected group_name
        group_id = None
        for id_grupo, nombre in group_values:
            if nombre == group_name:
                group_id = id_grupo
                break
                
        try:
            if client_id:  # Update existing client
                self.cursor.execute("""
                    UPDATE cliente 
                    SET nombre_cliente = %s, telefono = %s, correo = %s, id_grupo = %s
                    WHERE id_cliente = %s
                """, (name, phone, email, group_id, client_id))
                
                action = "actualizado"
            else:  # Add new client
                self.cursor.execute("""
                    INSERT INTO cliente (nombre_cliente, telefono, correo, id_grupo)
                    VALUES (%s, %s, %s, %s)
                """, (name, phone, email, group_id))
                
                action = "agregado"
            
            self.conn.commit()
            self.status_var.set(f"Cliente {action} correctamente")
            messagebox.showinfo("Éxito", f"Cliente {action} correctamente")
            popup.destroy()
            self.load_clients()
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error al guardar cliente: {str(e)}")

    def delete_client(self):
        """Delete selected client"""
        # Get selected client
        selected_item = self.client_tree.focus()
        if not selected_item:
            messagebox.showwarning("Advertencia", "Por favor selecciona un cliente para eliminar")
            return
        
        # Get client data
        values = self.client_tree.item(selected_item, "values")
        client_id = values[0]
        client_name = values[1]
        
        # Confirm deletion
        if not messagebox.askyesno("Confirmar Eliminación", 
                                 f"¿Estás seguro de eliminar el cliente '{client_name}'?\n\n"
                                 f"Esta acción eliminará todas las facturas asociadas a este cliente."):
            return
        
        # Check if client has invoices
        self.cursor.execute("SELECT COUNT(*) as count FROM factura WHERE id_cliente = %s", (client_id,))
        result = self.cursor.fetchone()
        
        if result and result['count'] > 0:
            if not messagebox.askyesno("Advertencia", 
                                     f"El cliente '{client_name}' tiene {result['count']} facturas asociadas. "
                                     f"Si eliminas este cliente, esas facturas también se eliminarán.\n\n"
                                     f"¿Estás seguro de continuar?"):
                return
        
        try:
            # Start transaction
            self.conn.autocommit = False
            
            # First delete invoice details for all client invoices
            self.cursor.execute("""
                DELETE df FROM detalle_factura df
                JOIN factura f ON df.id_factura = f.id_factura
                WHERE f.id_cliente = %s
            """, (client_id,))
            
            # Delete invoice sections for all client invoices
            self.cursor.execute("""
                DELETE sf FROM seccion_factura sf
                JOIN factura f ON sf.id_factura = f.id_factura
                WHERE f.id_cliente = %s
            """, (client_id,))
            
            # Delete invoice metadata for all client invoices
            self.cursor.execute("""
                DELETE fm FROM factura_metadata fm
                JOIN factura f ON fm.id_factura = f.id_factura
                WHERE f.id_cliente = %s
            """, (client_id,))
            
            # Delete debts for all client invoices
            self.cursor.execute("DELETE FROM deuda WHERE id_cliente = %s", (client_id,))
            
            # Delete saved orders for this client
            self.cursor.execute("DELETE FROM ordenes_guardadas WHERE id_cliente = %s", (client_id,))
            
            # Then delete invoices
            self.cursor.execute("DELETE FROM factura WHERE id_cliente = %s", (client_id,))
            
            # Finally delete client
            self.cursor.execute("DELETE FROM cliente WHERE id_cliente = %s", (client_id,))

            # Commit changes
            self.conn.commit()
            self.conn.autocommit = True
            
            self.status_var.set(f"Cliente '{client_name}' eliminado correctamente")
            messagebox.showinfo("Éxito", f"Cliente '{client_name}' eliminado correctamente")
            self.load_clients()
            
        except Exception as e:
            self.conn.rollback()
            self.conn.autocommit = True
            messagebox.showerror("Error", f"Error al eliminar cliente: {str(e)}")
    
    def manage_groups(self):
        """Manage client groups"""
        # Create popup
        popup = tk.Toplevel(self.root)
        popup.title("Administrar Grupos")
        popup.geometry("500x500")
        popup.transient(self.root)
        popup.grab_set()
        
        # Center popup
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (width // 2)
        y = (popup.winfo_screenheight() // 2) - (height // 2)
        popup.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        # Title
        tk.Label(popup, text="Grupos de Clientes", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Listbox for groups
        frame = tk.Frame(popup)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        
        group_listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, font=("Arial", 12))
        group_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=group_listbox.yview)
        
        # Load groups into listbox with client type info
        for group in self.groups:
            tipo_info = f" - {group['nombre_tipo']} ({group['descuento']}%)" if group['nombre_tipo'] else " - Sin tipo asignado"
            group_listbox.insert(tk.END, f"{group['clave_grupo']}{tipo_info}")

        # Buttons frame
        button_frame = tk.Frame(popup)
        button_frame.pack(fill="x", pady=10, padx=20)
        
        tk.Button(button_frame, text="Agregar Grupo", 
                 command=lambda: self.add_group(popup, group_listbox), 
                 bg="#4CAF50", fg="white", padx=10, pady=5).pack(side="left", padx=5)
                 
        tk.Button(button_frame, text="Editar Grupo", 
                 command=lambda: self.edit_group(popup, group_listbox), 
                 bg="#FFA500", fg="white", padx=10, pady=5).pack(side="left", padx=5)
                 
        tk.Button(button_frame, text="Eliminar Grupo", 
                 command=lambda: self.delete_group(popup, group_listbox), 
                 bg="#f44336", fg="white", padx=10, pady=5).pack(side="left", padx=5)
                 
        tk.Button(button_frame, text="Cerrar", 
                 command=popup.destroy, 
                 bg="#607D8B", fg="white", padx=10, pady=5).pack(side="right", padx=5)
    
    def manage_client_types(self):
        """Manage client types"""
        # Create popup
        popup = tk.Toplevel(self.root)
        popup.title("Administrar Tipos de Cliente")
        popup.geometry("400x400")
        popup.transient(self.root)
        popup.grab_set()
        
        # Center popup
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (width // 2)
        y = (popup.winfo_screenheight() // 2) - (height // 2)
        popup.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        # Title
        tk.Label(popup, text="Tipos de Cliente", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Listbox for types
        frame = tk.Frame(popup)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        
        type_listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, font=("Arial", 12))
        type_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=type_listbox.yview)
        
        # Load types into listbox
        for client_type in self.client_types:
            type_listbox.insert(tk.END, f"{client_type['nombre_tipo']} (Descuento: {client_type['descuento']}%)")
        
        # Buttons frame
        button_frame = tk.Frame(popup)
        button_frame.pack(fill="x", pady=10, padx=20)
        
        tk.Button(button_frame, text="Agregar Tipo", 
                 command=lambda: self.add_client_type(popup, type_listbox), 
                 bg="#4CAF50", fg="white", padx=10, pady=5).pack(side="left", padx=5)
                 
        tk.Button(button_frame, text="Editar Tipo", 
                 command=lambda: self.edit_client_type(popup, type_listbox), 
                 bg="#FFA500", fg="white", padx=10, pady=5).pack(side="left", padx=5)
                 
        tk.Button(button_frame, text="Eliminar Tipo", 
                 command=lambda: self.delete_client_type(popup, type_listbox), 
                 bg="#f44336", fg="white", padx=10, pady=5).pack(side="left", padx=5)
                 
        tk.Button(button_frame, text="Cerrar", 
                 command=popup.destroy, 
                 bg="#607D8B", fg="white", padx=10, pady=5).pack(side="right", padx=5)

    def add_group(self, parent_popup, group_listbox):
        """Add a new group"""
        # Ask for new group name
        group_name = simpledialog.askstring("Nuevo Grupo", "Clave del nuevo grupo:", parent=parent_popup)
        if not group_name or not group_name.strip():
            return
        
        # Ask for description
        description = simpledialog.askstring("Descripción", "Descripción del grupo (opcional):", parent=parent_popup)
        if description == "":  # User pressed cancel
            description = None
        
        # Ask for client type
        if not self.client_types:
            messagebox.showerror("Error", "No hay tipos de cliente disponibles. Debes crear al menos un tipo de cliente primero.", parent=parent_popup)
            return
        
        # Show client types dialog
        type_popup = tk.Toplevel(parent_popup)
        type_popup.title("Seleccionar Tipo de Cliente")
        type_popup.geometry("350x300")
        type_popup.transient(parent_popup)
        type_popup.grab_set()
        
        tk.Label(type_popup, text="Selecciona el tipo de cliente:", font=("Arial", 12)).pack(pady=10)
        
        type_listbox_local = tk.Listbox(type_popup, selectmode=tk.SINGLE)
        type_listbox_local.pack(fill="both", expand=True, padx=20, pady=10)
        
        for client_type in self.client_types:
            type_listbox_local.insert(tk.END, f"{client_type['nombre_tipo']} ({client_type['descuento']}%)")
        
        type_listbox_local.selection_set(0)  # Select first item by default
        
        selected_type_id = None
        
        def confirm_type():
            nonlocal selected_type_id
            selection = type_listbox_local.curselection()
            if selection:
                selected_type_id = self.client_types[selection[0]]['id_tipo_cliente']
                type_popup.destroy()
        
        tk.Button(type_popup, text="Confirmar", command=confirm_type, 
                 bg="#4CAF50", fg="white", padx=10, pady=5).pack(pady=10)
        
        type_popup.wait_window()  # Wait for the type selection window to close
        
        if selected_type_id is None:
            return
            
        try:
            # Insert new group with client type
            self.cursor.execute("""
                INSERT INTO grupo (clave_grupo, descripcion, id_tipo_cliente) 
                VALUES (%s, %s, %s)
            """, (group_name, description, selected_type_id))
            self.conn.commit()
            
            # Reload groups
            self.load_groups()
            
            # Update listbox
            group_listbox.delete(0, tk.END)
            for group in self.groups:
                tipo_info = f" - {group['nombre_tipo']} ({group['descuento']}%)" if group['nombre_tipo'] else " - Sin tipo asignado"
                group_listbox.insert(tk.END, f"{group['clave_grupo']}{tipo_info}")
                
            self.status_var.set(f"Grupo '{group_name}' agregado correctamente")
                
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error al agregar grupo: {str(e)}")

    def edit_group(self, parent_popup, group_listbox):
        """Edit selected group"""
        # Get selected group
        selection = group_listbox.curselection()
        if not selection:
            messagebox.showwarning("Advertencia", "Por favor selecciona un grupo para editar", parent=parent_popup)
            return
            
        # Get group info
        selected_index = selection[0]
        selected_group = self.groups[selected_index]
        
        # Ask for new name
        new_name = simpledialog.askstring("Editar Grupo", "Nueva clave:", 
                                       initialvalue=selected_group['clave_grupo'], 
                                       parent=parent_popup)
        if not new_name or not new_name.strip():
            return
        
        # Ask for new description
        new_description = simpledialog.askstring("Descripción", "Nueva descripción (opcional):", 
                                               initialvalue=selected_group['descripcion'] or "", 
                                               parent=parent_popup)
        if new_description == "":  # User pressed cancel
            new_description = selected_group['descripcion']
        
        # Ask for new client type
        if not self.client_types:
            messagebox.showerror("Error", "No hay tipos de cliente disponibles.", parent=parent_popup)
            return
        
        # Show client types dialog
        type_popup = tk.Toplevel(parent_popup)
        type_popup.title("Seleccionar Tipo de Cliente")
        type_popup.geometry("350x300")
        type_popup.transient(parent_popup)
        type_popup.grab_set()
        
        tk.Label(type_popup, text="Selecciona el tipo de cliente:", font=("Arial", 12)).pack(pady=10)
        
        type_listbox_local = tk.Listbox(type_popup, selectmode=tk.SINGLE)
        type_listbox_local.pack(fill="both", expand=True, padx=20, pady=10)
        
        current_selection = 0
        for i, client_type in enumerate(self.client_types):
            type_listbox_local.insert(tk.END, f"{client_type['nombre_tipo']} ({client_type['descuento']}%)")
            if client_type['id_tipo_cliente'] == selected_group['id_tipo_cliente']:
                current_selection = i
        
        type_listbox_local.selection_set(current_selection)
        
        selected_type_id = None
        
        def confirm_type():
            nonlocal selected_type_id
            selection = type_listbox_local.curselection()
            if selection:
                selected_type_id = self.client_types[selection[0]]['id_tipo_cliente']
                type_popup.destroy()
        
        tk.Button(type_popup, text="Confirmar", command=confirm_type, 
                 bg="#4CAF50", fg="white", padx=10, pady=5).pack(pady=10)
        
        type_popup.wait_window()
        
        if selected_type_id is None:
            return
            
        try:
            # Update group
            self.cursor.execute("""
                UPDATE grupo 
                SET clave_grupo = %s, descripcion = %s, id_tipo_cliente = %s
                WHERE id_grupo = %s
            """, (new_name, new_description, selected_type_id, selected_group['id_grupo']))
            self.conn.commit()
            
            # Reload groups
            self.load_groups()
            
            # Update listbox
            group_listbox.delete(0, tk.END)
            for group in self.groups:
                tipo_info = f" - {group['nombre_tipo']} ({group['descuento']}%)" if group['nombre_tipo'] else " - Sin tipo asignado"
                group_listbox.insert(tk.END, f"{group['clave_grupo']}{tipo_info}")
                
            self.status_var.set(f"Grupo actualizado correctamente")
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error al actualizar grupo: {str(e)}")

    def delete_group(self, parent_popup, group_listbox):
        """Delete selected group"""
        # Get selected group
        selection = group_listbox.curselection()
        if not selection:
            messagebox.showwarning("Advertencia", "Por favor selecciona un grupo para eliminar", parent=parent_popup)
            return
            
        # Get group info
        selected_index = selection[0]
        selected_group = self.groups[selected_index]
        
        # Check if group is in use
        self.cursor.execute("SELECT COUNT(*) as count FROM cliente WHERE id_grupo = %s", (selected_group['id_grupo'],))
        clients_count = self.cursor.fetchone()['count']
        
        if clients_count > 0:
            messagebox.showerror("Error", 
                              f"No se puede eliminar este grupo porque está en uso por {clients_count} clientes.\n"
                              f"Debes reasignar o eliminar estos clientes primero.", 
                              parent=parent_popup)
            return
            
        # Confirm deletion
        if not messagebox.askyesno("Confirmar Eliminación", 
                                 f"¿Estás seguro de eliminar el grupo '{selected_group['clave_grupo']}'?",
                                 parent=parent_popup):
            return
            
        try:
            # Delete group
            self.cursor.execute("DELETE FROM grupo WHERE id_grupo = %s", (selected_group['id_grupo'],))
            self.conn.commit()
            
            # Reload groups
            self.load_groups()
            
            # Update listbox
            group_listbox.delete(0, tk.END)
            for group in self.groups:
                tipo_info = f" - {group['nombre_tipo']} ({group['descuento']}%)" if group['nombre_tipo'] else " - Sin tipo asignado"
                group_listbox.insert(tk.END, f"{group['clave_grupo']}{tipo_info}")
                
            self.status_var.set(f"Grupo eliminado correctamente")
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error al eliminar grupo: {str(e)}")
            
    def add_client_type(self, parent_popup, type_listbox):
        """Add a new client type"""
        # Ask for new type name and discount
        type_name = simpledialog.askstring("Nuevo Tipo", "Nombre del nuevo tipo:", parent=parent_popup)
        if not type_name or not type_name.strip():
            return
            
        discount = simpledialog.askfloat("Descuento", "Porcentaje de descuento (ej. 10.5):", 
                                        parent=parent_popup, minvalue=0, maxvalue=100)
        if discount is None:  # User cancelled
            return
            
        try:
            # Insert new type
            self.cursor.execute("INSERT INTO tipo_cliente (nombre_tipo, descuento) VALUES (%s, %s)", 
                             (type_name, discount))
            self.conn.commit()
            
            # Reload types
            self.load_client_types()
            
            # Update listbox
            type_listbox.delete(0, tk.END)
            for client_type in self.client_types:
                type_listbox.insert(tk.END, f"{client_type['nombre_tipo']} (Descuento: {client_type['descuento']}%)")
                
            self.status_var.set(f"Tipo '{type_name}' agregado correctamente")
                
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error al agregar tipo: {str(e)}")
    
    def edit_client_type(self, parent_popup, type_listbox):
        """Edit selected client type"""
        # Get selected type
        selection = type_listbox.curselection()
        if not selection:
            messagebox.showwarning("Advertencia", "Por favor selecciona un tipo para editar", parent=parent_popup)
            return
            
        # Get type info
        selected_index = selection[0]
        selected_type = self.client_types[selected_index]
        
        # Ask for new name and discount
        new_name = simpledialog.askstring("Editar Tipo", "Nuevo nombre:", 
                                       initialvalue=selected_type['nombre_tipo'], 
                                       parent=parent_popup)
        if not new_name or not new_name.strip():
            return
            
        new_discount = simpledialog.askfloat("Editar Descuento", "Nuevo porcentaje de descuento:", 
                                           initialvalue=float(selected_type['descuento']),
                                           parent=parent_popup, minvalue=0, maxvalue=100)
        if new_discount is None:  # User cancelled
            return
            
        try:
            # Update type
            self.cursor.execute("""
                UPDATE tipo_cliente 
                SET nombre_tipo = %s, descuento = %s
                WHERE id_tipo_cliente = %s
            """, (new_name, new_discount, selected_type['id_tipo_cliente']))
            self.conn.commit()
            
            # Reload types
            self.load_client_types()
            
            # Update listbox
            type_listbox.delete(0, tk.END)
            for client_type in self.client_types:
                type_listbox.insert(tk.END, f"{client_type['nombre_tipo']} (Descuento: {client_type['descuento']}%)")
                
            self.status_var.set(f"Tipo actualizado correctamente")
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error al actualizar tipo: {str(e)}")
    
    def delete_client_type(self, parent_popup, type_listbox):
        """Delete selected client type"""
        # Get selected type
        selection = type_listbox.curselection()
        if not selection:
            messagebox.showwarning("Advertencia", "Por favor selecciona un tipo para eliminar", parent=parent_popup)
            return
            
        # Get type info
        selected_index = selection[0]
        selected_type = self.client_types[selected_index]
        
        # Check if type is in use by groups
        self.cursor.execute("SELECT COUNT(*) as count FROM grupo WHERE id_tipo_cliente = %s", (selected_type['id_tipo_cliente'],))
        groups_count = self.cursor.fetchone()['count']
        
        if groups_count > 0:
            messagebox.showerror("Error", 
                              f"No se puede eliminar este tipo porque está en uso por {groups_count} grupos.\n"
                              f"Debes reasignar o eliminar estos grupos primero.", 
                              parent=parent_popup)
            return
            
        # Confirm deletion
        if not messagebox.askyesno("Confirmar Eliminación", 
                                 f"¿Estás seguro de eliminar el tipo '{selected_type['nombre_tipo']}'?",
                                 parent=parent_popup):
            return
            
        try:
            # Delete type
            self.cursor.execute("DELETE FROM tipo_cliente WHERE id_tipo_cliente = %s", (selected_type['id_tipo_cliente'],))
            self.conn.commit()
            
            # Reload types
            self.load_client_types()
            
            # Update listbox
            type_listbox.delete(0, tk.END)
            for client_type in self.client_types:
                type_listbox.insert(tk.END, f"{client_type['nombre_tipo']} (Descuento: {client_type['descuento']}%)")
                
            self.status_var.set(f"Tipo eliminado correctamente")
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error al eliminar tipo: {str(e)}")

    def on_closing(self):
        """Clean up and close connection when closing the app"""
        try:
            self.conn.close()
        except:
            pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ClientManagerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()