# carrito_module_mejorado.py
# Versión modificada para compatibilidad con nueva estructura de BD

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import uuid
from typing import Dict, List, Optional

class SeccionCarrito:
    """Representa una sección del carrito"""
    def __init__(self, id_seccion: str, nombre: str):
        self.id = id_seccion
        self.nombre = nombre

class ItemCarrito:
    """Representa un item en el carrito"""
    def __init__(self, id_producto: int, nombre_producto: str, cantidad: float, precio_unitario: float, unidad_producto: str, seccion_id: Optional[str] = None):
        self.id_producto = id_producto
        self.nombre_producto = nombre_producto
        self.cantidad = cantidad
        self.precio_unitario = precio_unitario
        self.unidad_producto = unidad_producto
        self.seccion_id = seccion_id
        self.subtotal = cantidad * precio_unitario

class CarritoConSecciones:
    def __init__(self, parent_frame, on_change_callback=None):
        """
        Inicializa el carrito con sistema de secciones.
        :param parent_frame: El frame de Tkinter donde se dibujará el carrito.
        :param on_change_callback: Una función que se llamará cuando el carrito cambie.
        """
        self.parent = parent_frame
        self.on_change_callback = on_change_callback
        
        # Datos del carrito
        self.items: Dict[str, ItemCarrito] = {}
        self.secciones: Dict[str, SeccionCarrito] = {}
        self.sectioning_enabled = False
        
        # Crear interfaz
        self._crear_interfaz()
        
        # Crear una sección por defecto
        self._crear_seccion_defecto()

    def _crear_interfaz(self):
        """Crea la interfaz del carrito"""
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill="both", expand=True)
        
        self.frame_controles = ttk.Frame(main_frame)
        self.frame_controles.pack(fill="x", padx=5, pady=5)
        
        self.sectioning_var = tk.BooleanVar()
        self.check_secciones = ttk.Checkbutton(
            self.frame_controles, 
            text="Habilitar Secciones", 
            variable=self.sectioning_var,
            command=self._toggle_sectioning
        )
        self.check_secciones.pack(side="left")
        
        self.btn_gestionar = ttk.Button(
            self.frame_controles,
            text="Gestionar Secciones",
            command=self._gestionar_secciones
        )
        
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        cols = ("cantidad",  "unidad", "precio_unitario", "total", "del")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="tree headings")

        self.tree.heading("#0", text="Producto / Sección")
        self.tree.column("#0", width=200, stretch=True)
        self.tree.heading("cantidad", text="Cantidad")
        self.tree.column("cantidad", width=80, anchor="center")
        self.tree.heading("unidad", text="Unidad")
        self.tree.column("unidad", width=60, anchor="center")
        self.tree.heading("precio_unitario", text="Precio Unitario")
        self.tree.column("precio_unitario", width=110, anchor="e")
        self.tree.heading("total", text="Total")
        self.tree.column("total", width=110, anchor="e")
        self.tree.heading("del", text="🗑️")
        self.tree.column("del", width=40, anchor="center", stretch=False)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Vincular eventos de clic y doble clic
        self.tree.bind("<ButtonRelease-1>", self._handle_click)
        self.tree.bind("<Double-1>", self._handle_double_click)

    def _handle_double_click(self, event):
        """Maneja el doble clic para editar la cantidad de un item."""
        
        # Identificar la fila y columna donde ocurrió el evento
        item_id = self.tree.identify_row(event.y)
        column_id = self.tree.identify_column(event.x)

        # Salir si no se hizo clic en un item válido o en la columna de cantidad
        if not item_id or self.tree.column(column_id, "id") != "cantidad":
            return
            
        tags = self.tree.item(item_id, "tags")
        # Salir si se hizo clic en una fila de sección
        if not tags or "seccion" in tags:
            return

        item_key = tags[0]
        
        # Obtener las coordenadas de la celda para ubicar el cuadro de edición
        x, y, width, height = self.tree.bbox(item_id, column_id)

        # Crear un cuadro de texto (Entry) temporal sobre la celda
        entry = ttk.Entry(self.tree)
        entry.place(x=x, y=y, width=width, height=height)
        
        current_quantity = self.items[item_key].cantidad
        entry.insert(0, f"{current_quantity:.2f}")
        entry.select_range(0, 'end')
        entry.focus_set()

        def on_edit_done(event_obj):
            """Se ejecuta al presionar Enter o al perder el foco."""
            try:
                new_quantity = float(entry.get())
                if new_quantity > 0:
                    item = self.items[item_key]
                    item.cantidad = new_quantity
                    item.subtotal = item.cantidad * item.precio_unitario
                    self._actualizar_display()
                    self._notificar_cambio()
                else:
                    messagebox.showwarning("Valor inválido", "La cantidad debe ser un número positivo.")
            except ValueError:
                messagebox.showwarning("Entrada inválida", "Por favor, ingrese un número válido.")
            finally:
                entry.destroy()

        def on_edit_cancel(event_obj):
            """Se ejecuta al presionar Escape."""
            entry.destroy()

        # Vincular los eventos al cuadro de texto temporal
        entry.bind("<Return>", on_edit_done)
        entry.bind("<FocusOut>", on_edit_done)
        entry.bind("<Escape>", on_edit_cancel)

    def _crear_seccion_defecto(self):
        """Crea una sección por defecto"""
        seccion_id = str(uuid.uuid4())
        self.secciones[seccion_id] = SeccionCarrito(seccion_id, "General")

    def _toggle_sectioning(self):
        """Activa o desactiva el modo de secciones"""
        self.sectioning_enabled = self.sectioning_var.get()
        
        if self.sectioning_enabled:
            self.btn_gestionar.pack(side="left", padx=(10, 0))
            primera_seccion = self._get_primera_seccion_id()
            for item in self.items.values():
                item.seccion_id = primera_seccion
        else:
            self.btn_gestionar.pack_forget()
            for item in self.items.values():
                item.seccion_id = None
        
        self._actualizar_display()

    def _get_primera_seccion_id(self) -> Optional[str]:
        """Obtiene el ID de la primera sección disponible"""
        return next(iter(self.secciones.keys())) if self.secciones else None

    def _gestionar_secciones(self):
        """Abre el diálogo de gestión de secciones"""
        GestorSecciones(self.parent, self)

    def agregar_item(self, id_producto: int, nombre_prod: str, cantidad: float, precio_unit: float, unidad_producto: str, seccion_id: Optional[str] = None):
        """Añade o actualiza un producto en el carrito"""
        if self.sectioning_enabled:
            if seccion_id is None:
                seccion_id = self._get_primera_seccion_id()
            # Usar ID de producto + sección como clave para evitar duplicados en diferentes secciones
            key = f"{id_producto}_{seccion_id}" if seccion_id else str(id_producto)
        else:
            key = str(id_producto)
            seccion_id = None
        
        if key in self.items:
            self.items[key].cantidad += cantidad
            self.items[key].subtotal = self.items[key].cantidad * self.items[key].precio_unitario
        else:
            self.items[key] = ItemCarrito(id_producto, nombre_prod, cantidad, precio_unit, unidad_producto, seccion_id)
        
        self._actualizar_display()
        self._notificar_cambio()

    def obtener_items(self):
        """Retorna una lista con todos los items del carrito (formato original)"""
        items_lista = []
        for item in self.items.values():
            items_lista.append([
                f"{item.cantidad:.2f}", 
                item.nombre_producto,
                f"${item.precio_unitario:.2f}",
                f"${item.subtotal:.2f}",
                item.unidad_producto,
                item.id_producto  # Incluir ID para procesamiento posterior
            ])
        return items_lista

    def obtener_items_por_seccion(self) -> Dict[str, List]:
        """Retorna los items organizados por sección"""
        if not self.sectioning_enabled:
            return {"General": self.obtener_items()}
        
        items_por_seccion = {}
        
        for seccion_id, seccion in self.secciones.items():
            items_seccion = []
            subtotal_seccion = 0.0
            
            for item in self.items.values():
                if item.seccion_id == seccion_id:
                    items_seccion.append([
                        f"{item.cantidad:.2f}",
                        item.nombre_producto,
                        f"${item.precio_unitario:.2f}",
                        f"${item.subtotal:.2f}",
                        item.unidad_producto,
                        item.id_producto  # Incluir ID para procesamiento posterior
                    ])
                    subtotal_seccion += item.subtotal
            
            if items_seccion:
                items_por_seccion[seccion.nombre] = {
                    'items': items_seccion,
                    'subtotal': subtotal_seccion
                }
        
        return items_por_seccion

    def obtener_total(self):
        """Calcula y retorna el total de la compra"""
        return sum(item.subtotal for item in self.items.values())
    
    def obtener_cantidad_total(self):
        """Calcula y retorna la cantidad total de productos"""
        return sum(item.cantidad for item in self.items.values())

    def limpiar_carrito(self):
        """Elimina todos los productos del carrito"""
        if not self.items:
            return
            
        if messagebox.askyesno("Confirmar", "¿Limpiar todo el carrito?"):
            self.items.clear()
            self._actualizar_display()
            self._notificar_cambio()

    def agregar_seccion(self, nombre: str) -> str:
        """Agrega una nueva sección"""
        seccion_id = str(uuid.uuid4())
        self.secciones[seccion_id] = SeccionCarrito(seccion_id, nombre)
        self._actualizar_display()
        return seccion_id

    def eliminar_seccion(self, seccion_id: str) -> bool:
        """Elimina una sección"""
        if seccion_id not in self.secciones:
            return False
        
        items_en_seccion = [item for item in self.items.values() if item.seccion_id == seccion_id]
        
        if items_en_seccion:
            if len(self.secciones) == 1:
                messagebox.showerror("Error", "No se puede eliminar la única sección")
                return False
            
            respuesta = messagebox.askyesnocancel(
                "Sección con productos",
                f"La sección '{self.secciones[seccion_id].nombre}' contiene {len(items_en_seccion)} productos.\n\n"
                "Sí = Mover a otra sección\n"
                "No = Eliminar productos\n"
                "Cancelar = No eliminar sección"
            )
            
            if respuesta is None:
                return False
            elif respuesta:
                otra_seccion = next((sid for sid in self.secciones.keys() if sid != seccion_id), None)
                if otra_seccion:
                    for item in items_en_seccion:
                        item.seccion_id = otra_seccion
            else:
                keys_to_remove = [key for key, item in self.items.items() if item.seccion_id == seccion_id]
                for key in keys_to_remove:
                    del self.items[key]
        
        del self.secciones[seccion_id]
        self._actualizar_display()
        self._notificar_cambio()
        return True

    def renombrar_seccion(self, seccion_id: str, nuevo_nombre: str) -> bool:
        """Renombra una sección"""
        if seccion_id in self.secciones:
            self.secciones[seccion_id].nombre = nuevo_nombre
            self._actualizar_display()
            return True
        return False

    def _actualizar_display(self):
        """Actualiza la visualización del carrito"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not self.sectioning_enabled:
            for key, item in self.items.items():
                self.tree.insert("", "end",
                                 text=item.nombre_producto,
                                 values=(f"{item.cantidad:.2f}",
                                         item.unidad_producto,
                                         f"${item.precio_unitario:.2f}",
                                         f"${item.subtotal:.2f}",
                                         "🗑️"),
                                 tags=(key,))
        else:
            for seccion_id, seccion in self.secciones.items():
                items_seccion = [item for item in self.items.values() if item.seccion_id == seccion_id]
                
                if items_seccion:
                    subtotal_seccion = sum(item.subtotal for item in items_seccion)
                    seccion_node = self.tree.insert("", "end", text=seccion.nombre,
                                                  values=("", "", "", f"${subtotal_seccion:.2f}", ""),
                                                  tags=("seccion",), open=True)
                    
                    for key, item in self.items.items():
                        if item.seccion_id == seccion_id:
                            self.tree.insert(seccion_node, "end",
                                             text=item.nombre_producto,
                                             values=(f"{item.cantidad:.2f}",
                                                     item.unidad_producto,
                                                     f"${item.precio_unitario:.2f}",
                                                     f"${item.subtotal:.2f}",
                                                     "🗑️"),
                                             tags=(key,))

    def _handle_click(self, event):
        """Maneja los clics en el árbol para eliminar items"""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        
        item_id = self.tree.focus()
        if not item_id:
            return

        col_id = self.tree.identify_column(event.x)
        col_symbolic_id = self.tree.column(col_id, "id")

        if col_symbolic_id == "del":
            tags = self.tree.item(item_id, "tags")
            if tags and tags[0] != "seccion":
                key = tags[0]
                if key in self.items:
                    nombre_prod = self.items[key].nombre_producto
                    if messagebox.askyesno("Confirmar", f"¿Eliminar '{nombre_prod}' del carrito?"):
                        del self.items[key]
                        self._actualizar_display()
                        self._notificar_cambio()

    def _notificar_cambio(self):
        """Llama a la función callback si existe"""
        if self.on_change_callback:
            self.on_change_callback()

class DialogoSeccion:
    """Diálogo para seleccionar sección al agregar producto"""
    def __init__(self, parent, secciones: List[SeccionCarrito], on_seleccionar):
        self.on_seleccionar = on_seleccionar
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Seleccionar Sección")
        self.dialog.geometry("300x150")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        ttk.Label(self.dialog, text="Seleccione una sección:", font=("Arial", 11)).pack(pady=10)
        
        self.seccion_var = tk.StringVar()
        self.combo_secciones = ttk.Combobox(self.dialog, textvariable=self.seccion_var, 
                                            values=[s.nombre for s in secciones], 
                                            state="readonly", width=20)
        self.combo_secciones.pack(pady=10)
        self.combo_secciones.set(secciones[0].nombre if secciones else "")
        
        self.seccion_map = {s.nombre: s.id for s in secciones}
        
        frame_botones = ttk.Frame(self.dialog)
        frame_botones.pack(pady=10)
        
        ttk.Button(frame_botones, text="Aceptar", command=self._aceptar).pack(side="left", padx=5)
        ttk.Button(frame_botones, text="Cancelar", command=self.dialog.destroy).pack(side="left", padx=5)

    def _aceptar(self):
        nombre_seccion = self.seccion_var.get()
        if nombre_seccion in self.seccion_map:
            self.on_seleccionar(self.seccion_map[nombre_seccion])
        self.dialog.destroy()

class GestorSecciones:
    """Diálogo para gestionar secciones"""
    def __init__(self, parent, carrito: CarritoConSecciones):
        self.carrito = carrito
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Gestionar Secciones")
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._crear_interfaz()
        self._actualizar_lista()

    def _crear_interfaz(self):
        """Crea la interfaz del gestor"""
        ttk.Label(self.dialog, text="Secciones:", font=("Arial", 11, "bold")).pack(pady=(10, 5))
        
        list_frame = ttk.Frame(self.dialog)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.listbox = tk.Listbox(list_frame)
        scrollbar_list = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar_list.set)
        
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar_list.pack(side="right", fill="y")
        
        frame_botones = ttk.Frame(self.dialog)
        frame_botones.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(frame_botones, text="Agregar Sección", command=self._agregar_seccion).pack(side="left", padx=5)
        ttk.Button(frame_botones, text="Renombrar", command=self._renombrar_seccion).pack(side="left", padx=5)
        ttk.Button(frame_botones, text="Eliminar", command=self._eliminar_seccion).pack(side="left", padx=5)
        ttk.Button(frame_botones, text="Cerrar", command=self.dialog.destroy).pack(side="right", padx=5)

    def _actualizar_lista(self):
        """Actualiza la lista de secciones"""
        self.listbox.delete(0, tk.END)
        self.seccion_ids = []
        
        for seccion_id, seccion in self.carrito.secciones.items():
            count = sum(1 for item in self.carrito.items.values() if item.seccion_id == seccion_id)
            display_text = f"{seccion.nombre} ({count} productos)"
            self.listbox.insert(tk.END, display_text)
            self.seccion_ids.append(seccion_id)

    def _agregar_seccion(self):
        """Agrega una nueva sección"""
        nombre = simpledialog.askstring("Nueva Sección", "Nombre de la sección:")
        if nombre and nombre.strip():
            self.carrito.agregar_seccion(nombre.strip())
            self._actualizar_lista()

    def _renombrar_seccion(self):
        """Renombra la sección seleccionada"""
        seleccion = self.listbox.curselection()
        if not seleccion:
            messagebox.showwarning("Selección requerida", "Seleccione una sección para renombrar")
            return
        
        seccion_id = self.seccion_ids[seleccion[0]]
        nombre_actual = self.carrito.secciones[seccion_id].nombre
        
        nuevo_nombre = simpledialog.askstring("Renombrar Sección", 
                                              "Nuevo nombre:", initialvalue=nombre_actual)
        if nuevo_nombre and nuevo_nombre.strip():
            self.carrito.renombrar_seccion(seccion_id, nuevo_nombre.strip())
            self._actualizar_lista()

    def _eliminar_seccion(self):
        """Elimina la sección seleccionada"""
        seleccion = self.listbox.curselection()
        if not seleccion:
            messagebox.showwarning("Selección requerida", "Seleccione una sección para eliminar")
            return
        
        seccion_id = self.seccion_ids[seleccion[0]]
        if self.carrito.eliminar_seccion(seccion_id):
            self._actualizar_lista()