# Versión actualizada que integra el sistema de órdenes guardadas y nueva estructura de BD - CORREGIDA

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import calendar
from typing import Any, Dict
from src.modules.receipts.components import database
from src.modules.receipts.components import generador_pdf
from src.modules.receipts.components.carrito_module import CarritoConSecciones, DialogoSeccion
from src.modules.receipts.components import generador_excel
from src.modules.receipts.components.orden_manager import obtener_manager, OrdenManager
from src.modules.receipts.components.ventana_ordenes import abrir_ventana_ordenes

class ReciboAppMejorado:
    def __init__(self, parent=None, user_data=None, orden_folio=None):
        """
        Inicializa la aplicación de recibos con soporte para órdenes guardadas.
        
        Args:
            parent: Ventana padre
            user_data: Datos del usuario autenticado
            orden_folio: Folio de orden existente a cargar (opcional)
        """
        self.root = parent if parent else tk.Tk()
        self.user_data = user_data or {}
        
        # Detectar si estamos en contexto de launcher (parent existe = Toplevel window)
        self.is_launcher_context = parent is not None
        
        # Atributos para órdenes guardadas
        self.folio_actual = orden_folio
        self.folios_pestanas = {}  # Diccionario para tracking de folios por pestaña
        self.orden_guardada = None
        self.orden_manager = obtener_manager()
        
        # Configuración de usuario
        self.username = self.user_data.get('username', 'usuario')
        self.es_admin = self.user_data.get('rol', '').lower() == 'admin'
        
        self.root.title("Market - Sales System with Saved Orders")
        self.root.geometry("1100x750")

        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self.style.configure("Total.TLabel", font=("Helvetica", 12, "bold"))
        self.style.configure("Success.TButton", foreground="white")
        
        # Crear canvas scrolleable para todo el contenido
        self._setup_scrollable_interface()

        # Obtener grupos de cliente 
        grupos_raw: Any = database.obtener_grupos()
        self.grupos_data: Dict[str, Any] = {nombre: g_id for g_id, nombre in grupos_raw}
        if not self.grupos_data:
            messagebox.showerror("Database Error", "Could not load client groups.")
            if parent is None:
                self.root.destroy()
            return
            
        self.contador_pestañas = 0
        self._crear_widgets_principales()
        self._agregar_pestaña()
        
        # Cargar orden existente si se especificó
        if self.folio_actual:
            self._cargar_orden_al_inicio()
    
    def _setup_scrollable_interface(self):
        """Configura la interfaz scrolleable con Canvas y Scrollbar"""
        # Crear el canvas principal que ocupará toda la ventana
        self.main_canvas = tk.Canvas(self.root, highlightthickness=0)
        
        # Crear scrollbar vertical
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
        
        # Crear frame scrolleable que contendrá todo el contenido
        self.scrollable_frame = ttk.Frame(self.main_canvas)
        
        # Configurar el scrolling
        def on_frame_configure(event):
            # Refresh scroll region
            self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
            # Mostrar/ocultar scrollbar según sea necesario
            self._update_scrollbar_visibility()
        
        self.scrollable_frame.bind("<Configure>", on_frame_configure)
        
        # Crear ventana en el canvas para el frame scrolleable
        self.canvas_window = self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Configurar el scrollbar
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack del canvas y scrollbar
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind para redimensionar el frame scrolleable cuando cambia el canvas
        def on_canvas_configure(event):
            self._on_canvas_configure(event)
            self._update_scrollbar_visibility()
        
        self.main_canvas.bind("<Configure>", on_canvas_configure)
        
        # Bind para mouse wheel scrolling
        self._bind_mousewheel()
    
    def _update_scrollbar_visibility(self):
        """Muestra u oculta la scrollbar según sea necesario"""
        try:
            bbox = self.main_canvas.bbox("all")
            if bbox:
                content_height = bbox[3] - bbox[1]
                canvas_height = self.main_canvas.winfo_height()
                
                # Si el contenido es más alto que el canvas, mostrar scrollbar
                if content_height > canvas_height:
                    if not self.scrollbar.winfo_viewable():
                        self.scrollbar.pack(side="right", fill="y")
                else:
                    # Si el contenido cabe, ocultar scrollbar
                    if self.scrollbar.winfo_viewable():
                        self.scrollbar.pack_forget()
                        # Resetear scroll position al inicio
                        self.main_canvas.yview_moveto(0)
        except (tk.TclError, AttributeError):
            # Ignorar errores durante la inicialización
            pass
    
    def _on_canvas_configure(self, event):
        """Ajusta el ancho del frame scrolleable al ancho del canvas"""
        canvas_width = event.width
        self.main_canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def _bind_mousewheel(self):
        """Configura el scroll con mouse wheel"""
        def _on_mousewheel(event):
            # Solo hacer scroll si hay contenido que excede la vista
            bbox = self.main_canvas.bbox("all")
            if bbox and bbox[3] > self.main_canvas.winfo_height():
                # Scroll más suave ajustando la velocidad
                delta = -1 * (event.delta / 120) if hasattr(event, 'delta') else -1 if event.num == 4 else 1
                self.main_canvas.yview_scroll(int(delta), "units")
        
        def _on_mousewheel_linux(event):
            # Manejo específico para Linux
            bbox = self.main_canvas.bbox("all")
            if bbox and bbox[3] > self.main_canvas.winfo_height():
                if event.num == 4:
                    self.main_canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.main_canvas.yview_scroll(1, "units")
        
        # Función para aplicar bindings a un widget y sus hijos
        def bind_to_mousewheel(widget):
            # Windows/Mac
            widget.bind("<MouseWheel>", _on_mousewheel)
            # Linux
            widget.bind("<Button-4>", _on_mousewheel_linux)
            widget.bind("<Button-5>", _on_mousewheel_linux)
            
            # Aplicar recursivamente a todos los widgets hijos
            for child in widget.winfo_children():
                bind_to_mousewheel(child)
        
        # Aplicar bindings al canvas y frame scrolleable
        bind_to_mousewheel(self.main_canvas)
        bind_to_mousewheel(self.root)
        
        # También bindear cuando se agreguen nuevos widgets
        original_bind = self.scrollable_frame.bind
        def enhanced_bind(*args, **kwargs):
            result = original_bind(*args, **kwargs)
            # Re-aplicar mouse wheel bindings cuando se modifique el contenido
            self.root.after_idle(lambda: bind_to_mousewheel(self.scrollable_frame))
            return result
        self.scrollable_frame.bind = enhanced_bind

    def _cargar_orden_al_inicio(self):
        """Carga una orden existente al inicializar la aplicación"""
        try:
            if self.folio_actual is None:
                return
            # Cargar datos de la orden
            self.orden_guardada = self.orden_manager.cargar_orden(self.folio_actual)
            
            if self.orden_guardada:
                # Obtener la primera pestaña (que acabamos de crear)
                primera_pestaña = list(self.notebook.tabs())[0]
                widgets = getattr(self, f'widgets_{primera_pestaña.split(".")[-1]}', None)
                
                if widgets:
                    # Usar root.after para asegurar que la interfaz esté completamente inicializada
                    self.root.after(100, lambda: self._cargar_orden_existente(self.folio_actual, widgets))
                    
                    # Refresh título de la ventana
                    self.root.title(f"Market - Editing Order {self.folio_actual:06d}")
            else:
                messagebox.showerror("Error", f"Could not load order with receipt # {self.folio_actual}")
                self.folio_actual = None
                
        except Exception as e:
            messagebox.showerror("Error", f"Error loading order: {str(e)}")
            self.folio_actual = None

    def _crear_widgets_principales(self):
        """Crea los widgets principales de la aplicación"""
        frame_superior = ttk.Frame(self.scrollable_frame, padding=(10, 10, 10, 0))
        frame_superior.pack(fill="x")
        
        # Información de orden actual
        info_frame = ttk.Frame(frame_superior)
        info_frame.pack(fill="x")
        
        # Label para mostrar información de la orden
        self.lbl_orden_info = ttk.Label(
            info_frame, 
            text="New Order", 
            font=("Arial", 12, "bold"),
            foreground="blue"
        )
        self.lbl_orden_info.pack(side="left")
        
        btn_agregar_tab = ttk.Button(
            info_frame, 
            text="➕ Add New Order", 
            command=self._agregar_pestaña
        )
        btn_agregar_tab.pack(side="right")
        
        # Información sobre secciones
        info_label = ttk.Label(
            frame_superior, 
            text="💡 Tip: Active 'Enable Sections' to organize products by category",
            font=("Arial", 9),
            foreground="gray"
        )
        info_label.pack(pady=(5, 0))
        
        self.notebook = ttk.Notebook(self.scrollable_frame)
        self.notebook.pack(pady=(5, 10), padx=10, expand=True, fill="both")

    def _agregar_pestaña(self):
        """Agrega una nueva pestaña de pedido"""
        if self.contador_pestañas >= 5:
            messagebox.showinfo("Limit Reached", "Cannot add more than 5 orders.")
            return
            
        self.contador_pestañas += 1
        nueva_pestaña = ttk.Frame(self.notebook, padding="10")
        
        # Determinar título de la pestaña
        if self.folio_actual and self.contador_pestañas == 1:
            titulo_tab = f"Orden {self.folio_actual:06d}"
        else:
            titulo_tab = f"Order {self.contador_pestañas}"
            
        self.notebook.add(nueva_pestaña, text=titulo_tab)
        widgets = self._crear_contenido_tab(nueva_pestaña)
        
        # Guardar referencia a los widgets de esta pestaña
        tab_id = nueva_pestaña.winfo_name()
        setattr(self, f'widgets_{tab_id}', widgets)

        # Asignar folio único a esta pestaña
        if self.folio_actual and self.contador_pestañas == 1:
            # Primera pestaña con folio existente
            self.folios_pestanas[tab_id] = self.folio_actual
        else:
            # Nueva pestaña sin folio asignado
            self.folios_pestanas[tab_id] = None

        self.notebook.select(nueva_pestaña)
        return widgets

    def _crear_contenido_tab(self, tab_frame):
        """Crea el contenido de una pestaña"""
        widgets: Dict[str, Any] = {"clientes_map": {}}

        # Frame de búsqueda y cliente
        frame_busqueda = ttk.LabelFrame(tab_frame, text="1. Client & Search", padding="10")
        frame_busqueda.pack(fill="x")
        frame_busqueda.columnconfigure(1, weight=1)

        # Widgets de selección de cliente
        ttk.Label(frame_busqueda, text="Group:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        widgets['combo_grupos'] = ttk.Combobox(frame_busqueda, values=list(self.grupos_data.keys()), state="readonly")
        widgets['combo_grupos'].grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(frame_busqueda, text="Client:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        widgets['combo_clientes'] = ttk.Combobox(frame_busqueda, state="disabled")
        widgets['combo_clientes'].grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # Widgets de búsqueda
        ttk.Label(frame_busqueda, text="Search Product:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        widgets['entry_busqueda'] = ttk.Entry(frame_busqueda)
        widgets['entry_busqueda'].grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        widgets['btn_buscar'] = ttk.Button(frame_busqueda, text="🔍 Search")
        widgets['btn_buscar'].grid(row=2, column=2, padx=5, pady=5)
        
        # Frame central para resultados y carrito
        frame_central = ttk.Frame(tab_frame)
        frame_central.pack(fill="both", expand=True, pady=10)
        frame_central.columnconfigure(0, weight=1)
        frame_central.columnconfigure(1, weight=2)
        frame_central.rowconfigure(1, weight=1)
        
        # Resultados de búsqueda
        ttk.Label(frame_central, text="Search Results (Double-click to add)").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )
        
        # Frame para los resultados con scrollbar
        frame_resultados = ttk.Frame(frame_central)
        frame_resultados.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        frame_resultados.rowconfigure(0, weight=1)
        frame_resultados.columnconfigure(0, weight=1)
        
        cols_resultados = ("Product", "Price")
        widgets['tree_resultados'] = ttk.Treeview(
            frame_resultados, 
            columns=cols_resultados, 
            show="headings", 
            height=8
        )
        
        for col in cols_resultados: 
            widgets['tree_resultados'].heading(col, text=col)
        widgets['tree_resultados'].column("Price", width=100, anchor="e")
        widgets['tree_resultados'].grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar para resultados
        scrollbar_resultados = ttk.Scrollbar(
            frame_resultados, 
            orient="vertical", 
            command=widgets['tree_resultados'].yview
        )
        widgets['tree_resultados'].configure(yscrollcommand=scrollbar_resultados.set)
        scrollbar_resultados.grid(row=0, column=1, sticky="ns")

        # Frame fecha
        frame_fecha = ttk.LabelFrame(tab_frame, text="Registration Date", padding="10")
        frame_fecha.pack(fill="x", pady=(5, 0))
        frame_fecha.columnconfigure(1, weight=1)

        ttk.Label(frame_fecha, text="Date:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        widgets['fecha_var'] = tk.StringVar()
        # Establecer fecha actual como default
        from datetime import date
        widgets['fecha_var'].set(date.today().strftime("%Y-%m-%d"))

        widgets['entry_fecha'] = ttk.Entry(frame_fecha, textvariable=widgets['fecha_var'], width=12)
        widgets['entry_fecha'].grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(frame_fecha, text="(YYYY-MM-DD)", font=("Arial", 8), foreground="gray").grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # Función de validación para fechas
        def validar_fecha(event, fecha_var=widgets['fecha_var']):
            try:
                fecha_str = fecha_var.get()
                if fecha_str:
                    fecha_ingresada = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                    if fecha_ingresada > date.today():
                        messagebox.showwarning("Invalid Date", 
                                            "Future dates are not allowed.\n"
                                            "Today's date will be set.")
                        fecha_var.set(date.today().strftime("%Y-%m-%d"))
            except ValueError:
                messagebox.showwarning("Invalid Format", 
                                    "Use the format YYYY-MM-DD")
                fecha_var.set(date.today().strftime("%Y-%m-%d"))

        # Vincular validación al entry de fecha
        widgets['entry_fecha'].bind('<FocusOut>', validar_fecha)
        widgets['entry_fecha'].bind('<Return>', validar_fecha)

        # **CARRITO CON SECCIONES**
        frame_carrito = ttk.LabelFrame(frame_central, text="Shopping Cart", padding="5")
        frame_carrito.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(5, 0))
        
        # Crear el carrito con secciones
        widgets['carrito_obj'] = CarritoConSecciones(
            frame_carrito, 
            on_change_callback=lambda w=widgets: self._actualizar_total(w)
        )

        # Frame de total y acciones
        frame_acciones = ttk.LabelFrame(tab_frame, text="2. Order Total", padding="10")
        frame_acciones.pack(fill="x", pady=(10, 0))
        
        # Total
        widgets['lbl_total_valor'] = ttk.Label(frame_acciones, text="$0.00", style="Total.TLabel")
        widgets['lbl_total_valor'].pack(side="right")
        ttk.Label(frame_acciones, text="Total:", style="Total.TLabel").pack(side="right", padx=(20, 5))
        
        # Contador de productos
        widgets['lbl_contador'] = ttk.Label(frame_acciones, text="0 products")
        widgets['lbl_contador'].pack(side="left")
        
        # Frame de botones finales
        frame_final = ttk.LabelFrame(tab_frame, text="3. Finalize Sale", padding="10")
        frame_final.pack(fill="x", pady=10)
        
        # *** BOTONES EXISTENTES Y NUEVOS ***
        frame_botones = ttk.Frame(frame_final)
        frame_botones.pack(fill="x")
        
        # Fila superior - Acciones de orden
        frame_botones_superior = ttk.Frame(frame_botones)
        frame_botones_superior.pack(fill="x", pady=(0, 10))
        
        # NUEVOS BOTONES DE ÓRDENES
        widgets['btn_guardar_orden'] = ttk.Button(
            frame_botones_superior, 
            text="💾 Save Order",
            command=lambda w=widgets: self._guardar_orden_actual(w),
            style="Success.TButton"
        )
        widgets['btn_guardar_orden'].pack(side="left", padx=(0, 10))
        
        widgets['btn_ver_ordenes'] = ttk.Button(
            frame_botones_superior, 
            text="📋 View Orders",
            command=self._abrir_ventana_ordenes
        )
        widgets['btn_ver_ordenes'].pack(side="left", padx=(0, 10))
        
        # Separador visual
        ttk.Separator(frame_botones_superior, orient="vertical").pack(side="left", fill="y", padx=10)
        
        # Información de orden actual
        widgets['lbl_folio_info'] = ttk.Label(
            frame_botones_superior, 
            text="New order", 
            font=("Arial", 10, "italic"),
            foreground="blue"
        )
        widgets['lbl_folio_info'].pack(side="left", padx=(10, 0))
        
        # Fila inferior - Acciones tradicionales
        frame_botones_inferior = ttk.Frame(frame_botones)
        frame_botones_inferior.pack(fill="x")
        
        widgets['btn_limpiar'] = ttk.Button(
            frame_botones_inferior, 
            text="🗑️ Clear cart",
            command=lambda w=widgets: self._limpiar_carrito(w)
        )
        widgets['btn_limpiar'].pack(side="left", padx=(0, 10))

        widgets['btn_generar_excel'] = ttk.Button(
            frame_botones_inferior, 
            text="📊 Generate Excel",
            command=lambda w=widgets: self._generar_excel(w)
        )
        widgets['btn_generar_excel'].pack(side="left", padx=(0, 10))
        
        widgets['btn_generar_pdf'] = ttk.Button(
            frame_botones_inferior, 
            text="📄 Generate PDF",
            command=lambda w=widgets: self._generar_pdf_solo(w)
        )
        widgets['btn_generar_pdf'].pack(side="left", padx=(0, 10))
        
        widgets['btn_procesar_venta'] = ttk.Button(
            frame_botones_inferior, 
            text="✅ Register Sale",
            style="Accent.TButton"
        )
        widgets['btn_procesar_venta'].pack(side="right")

        # --- VINCULAR EVENTOS ---
        widgets['combo_grupos'].bind("<<ComboboxSelected>>", 
                            lambda event, w=widgets: self._on_grupo_selected(event, w))
        widgets['btn_buscar'].config(command=lambda w=widgets: self._buscar_insumos(w))
        widgets['btn_procesar_venta'].config(command=lambda w=widgets: self._procesar_venta(w))
        widgets['tree_resultados'].bind("<Double-1>", 
                                      lambda event, w=widgets: self._abrir_ventana_cantidad(event, w))
        
        # Permitir búsqueda con Enter
        widgets['entry_busqueda'].bind("<Return>", 
                                     lambda event, w=widgets: self._buscar_insumos(w))

        return widgets

    # ==================== NUEVOS MÉTODOS PARA ÓRDENES GUARDADAS ====================

    def _guardar_orden_actual(self, widgets):
        """Guarda el estado actual del carrito como una orden"""
        try:
            # Verificar que hay cliente seleccionado
            nombre_cliente = widgets['combo_clientes'].get()
            if not nombre_cliente:
                messagebox.showwarning("Missing Client", "Please, select a client before saving.")
                return

            # Verificar que el carrito no está vacío
            carrito = widgets['carrito_obj']
            if not carrito.items:
                messagebox.showwarning("Empty Cart", "No products in the cart to save.")
                return

            id_cliente = widgets['clientes_map'][nombre_cliente]
            total = carrito.obtener_total()

            # Obtener tab actual y su folio
            tab_actual = self.notebook.select()
            tab_id = tab_actual.split(".")[-1]
            folio_actual_pestana = self.folios_pestanas.get(tab_id)

            # SIEMPRE obtener un nuevo folio único al guardar (independientemente si ya tiene uno)
            folio_a_usar = None
            
            # Si es una orden completamente nueva (sin folio previo)
            if not folio_actual_pestana:
                # Obtener nuevo folio con múltiples intentos para evitar duplicados
                max_intentos_folio = 10
                for intento in range(max_intentos_folio):
                    folio_candidato = self.orden_manager.obtener_siguiente_folio_disponible()
                    if not folio_candidato:
                        messagebox.showerror("Error", "Could not get an available receipt #.")
                        return
                    
                    # Verificar disponibilidad inmediatamente antes de usar
                    if self.orden_manager._verificar_folio_disponible(folio_candidato):
                        folio_a_usar = folio_candidato
                        print(f"✓ Folio {folio_a_usar} obtained and verified as available")
                        break
                    else:
                        print(f"⚠ Folio {folio_candidato} is no longer available, retrying... ({intento + 1}/{max_intentos_folio})")
                        
                if not folio_a_usar:
                    messagebox.showerror("Error", "Could not get a unique receipt # after multiple attempts.")
                    return
                    
            else:
                # Es una actualización de orden existente
                folio_a_usar = folio_actual_pestana

            # Serializar estado del carrito
            datos_carrito = self._serializar_estado_carrito(widgets)

            # Guardar en base de datos
            if self.orden_guardada and self.folio_actual == folio_a_usar:
                # Refresh orden existente
                exito = self.orden_manager.actualizar_orden(folio_a_usar, datos_carrito, total)
                mensaje_exito = "Order updated successfully"
            else:
                # Crear nueva orden con validación adicional
                # Doble verificación antes de reservar
                if not self.orden_manager._verificar_folio_disponible(folio_a_usar):
                    messagebox.showerror("Error", f"Receipt # {folio_a_usar} is no longer available. Please try again.")
                    return
                    
                exito = self.orden_manager.reservar_folio(
                    folio_a_usar, id_cliente, self.username, datos_carrito, total
                )
                mensaje_exito = "Order saved successfully"

            if exito:
                # Refresh estado interno SOLO si fue exitoso
                self.folios_pestanas[tab_id] = folio_a_usar
                self.folio_actual = folio_a_usar  # Mantener para compatibilidad
                self.orden_guardada = True
                
                # Refresh interfaz
                widgets['lbl_folio_info'].config(
                    text=f"Order saved - Receipt #: {self.folio_actual:06d}",
                    foreground="green"
                )
                
                # Refresh título de ventana y pestaña
                self.root.title(f"Market - Editing Order {self.folio_actual:06d}")
                tab_actual = self.notebook.select()
                self.notebook.tab(tab_actual, text=f"Order {self.folio_actual:06d}")
                
                # Refresh label principal
                self.lbl_orden_info.config(
                    text=f"Editing Order {self.folio_actual:06d}",
                    foreground="green"
                )

                messagebox.showinfo("Success", 
                                f"{mensaje_exito}\n\n"
                                f"Folio assigned: {self.folio_actual:06d}\n"
                                f"Client: {nombre_cliente}\n"
                                f"Total: ${total:,.2f}")
                
                # Notificar al padre sobre el cambio si estamos en contexto de launcher
                if self.is_launcher_context:
                    self._notificar_cambio_orden()
            else:
                messagebox.showerror("Error", f"Could not save order with receipt # {folio_a_usar}.")

        except Exception as e:
            messagebox.showerror("Error", f"Error saving order: {str(e)}")
            import traceback
            traceback.print_exc()  # Para debugging
    
    def _notificar_cambio_orden(self):
        """Notifica a la ventana principal sobre cambios en la orden"""
        try:
            # Crear evento personalizado en la ventana raíz
            if hasattr(self.root, 'master') and self.root.master:
                self.root.master.event_generate("<<OrdenCambiada>>")
                print("📤 Order change notification sent")
        except Exception as e:
            print(f"Error notifying order change: {e}")

    def _cargar_orden_existente(self, folio, widgets):
        """Carga una orden existente en la interfaz"""
        try:
            # Cargar datos de la orden
            orden_data = self.orden_manager.cargar_orden(folio)
            
            if not orden_data:
                messagebox.showerror("Error", f"Order not found with receipt # {folio}")
                return False

            # Refresh estado interno
            self.folio_actual = folio
            self.orden_guardada = True

            # Restaurar cliente seleccionado desde datos_carrito_obj
            datos_carrito = orden_data.get('datos_carrito_obj', {})
            cliente_info = datos_carrito.get('cliente_info', {})
            
            id_cliente = cliente_info.get('id_cliente')
            nombre_cliente = cliente_info.get('nombre_cliente')
            grupo_seleccionado = cliente_info.get('grupo_seleccionado')
            
            # Buscar y seleccionar el grupo del cliente
            grupo_encontrado = None
            for nombre_grupo, id_grupo in self.grupos_data.items():
                clientes = database.obtener_clientes_por_grupo(id_grupo)
                if any(c_id == id_cliente for c_id, c_nombre in clientes):
                    grupo_encontrado = nombre_grupo
                    break

            if grupo_encontrado:
                # Seleccionar grupo
                widgets['combo_grupos'].set(grupo_encontrado)
                self._on_grupo_selected(None, widgets)

             # Esperar a que se carguen los clientes y luego seleccionar el correcto
            def seleccionar_cliente():
                if nombre_cliente in widgets['combo_clientes']['values']:
                    widgets['combo_clientes'].set(nombre_cliente)
                    # Refresh el mapping de clientes
                    if nombre_cliente not in widgets['clientes_map'] and grupo_encontrado is not None:
                        # Reconstruir el mapping si es necesario
                        grupo_id = self.grupos_data[grupo_encontrado]
                        clientes = database.obtener_clientes_por_grupo(grupo_id)
                        widgets['clientes_map'] = {nombre: id_cliente for id_cliente, nombre in clientes}
            
            # Usar after para asegurar que el combobox esté poblado
            self.root.after(100, seleccionar_cliente)

            # Restaurar estado del carrito
            datos_carrito_obj = orden_data.get('datos_carrito_obj')
            if datos_carrito_obj:
                OrdenManager.json_a_carrito(datos_carrito_obj, widgets['carrito_obj'])
            
            # Refresh interfaz
            widgets['lbl_folio_info'].config(
                text=f"Order loaded - Receipt #: {folio:06d}",
                foreground="green"
            )
            
            self.lbl_orden_info.config(
                text=f"Editing Order {folio:06d}",
                foreground="green"
            )

            # Refresh total
            self._actualizar_total(widgets)

            # Refresh folio de la pestaña actual
            tab_actual = self.notebook.select()
            tab_id = tab_actual.split(".")[-1] 
            self.folios_pestanas[tab_id] = folio

            print(f"Orden {folio} uploaded successfully")
            return True

        except Exception as e:
            messagebox.showerror("Error", f"Error loading order: {str(e)}")
            return False

    def _serializar_estado_carrito(self, widgets):
        """Convierte el estado actual del carrito a formato JSON serializable"""
        try:
            carrito = widgets['carrito_obj']
            
            # Obtener información del cliente
            nombre_cliente = widgets['combo_clientes'].get()
            id_cliente = widgets['clientes_map'].get(nombre_cliente)
            
            # Usar el método estático del OrdenManager
            datos_carrito = OrdenManager.carrito_a_json(carrito)
            
            # Add información adicional
            datos_carrito['cliente_info'] = {
                'id_cliente': id_cliente,
                'nombre_cliente': nombre_cliente,
                'grupo_seleccionado': widgets['combo_grupos'].get()
            }
            
            return datos_carrito

        except Exception as e:
            print(f"Error serializing cart: {e}")
            return {}

    def _abrir_ventana_ordenes(self):
        """Abre la ventana de gestión de órdenes o retorna al hub del launcher"""
        try:
            # Si estamos en contexto de launcher, simplemente cerrar esta ventana
            # para retornar al hub principal de VentanaOrdenes
            if self.is_launcher_context:
                print("🔄 Returning to the main orders hub...")
                self.root.destroy()
                return
            
            # Si no estamos en contexto de launcher, usar el comportamiento original
            # Callbacks para la ventana de órdenes
            def callback_nueva_orden():
                # Cerrar ventana actual si es modal
                if hasattr(self, '_ventana_ordenes'):
                    self._ventana_ordenes.destroy()
                
                # Crear nueva instancia sin folio
                nueva_app = ReciboAppMejorado(
                    parent=self.root.master if self.root.master else None,
                    user_data=self.user_data
                )
                
                # Cerrar ventana actual
                self.root.destroy()
                
                # Mostrar nueva ventana
                nueva_app.run()

            def callback_editar_orden(folio):
                # Cerrar ventana de órdenes si existe
                if hasattr(self, '_ventana_ordenes'):
                    self._ventana_ordenes.destroy()
                
                # Crear nueva instancia con el folio específico
                nueva_app = ReciboAppMejorado(
                    parent=self.root.master if self.root.master else None,
                    user_data=self.user_data,
                    orden_folio=folio
                )
                
                # Cerrar ventana actual
                self.root.destroy()
                
                # Mostrar nueva ventana
                nueva_app.run()

            # Abrir ventana de órdenes (solo en modo standalone)
            self._ventana_ordenes = abrir_ventana_ordenes(
                parent=self.root,
                user_data=self.user_data,
                on_nueva_orden=callback_nueva_orden,
                on_editar_orden=callback_editar_orden
            )

        except Exception as e:
            messagebox.showerror("Error", f"Error opening orders window: {str(e)}")

    # ==================== MÉTODOS EXISTENTES (MODIFICADOS PARA ÓRDENES) ====================

    def _procesar_venta(self, widgets):
        """Registra la venta en la base de datos y opcionalmente genera PDF"""
        nombre_cliente = widgets['combo_clientes'].get()
        if not nombre_cliente:
            messagebox.showwarning("Missing Client", "Please, select a client.")
            return

        carrito = widgets['carrito_obj']
        if not carrito.items:
            messagebox.showwarning("Empty Cart", "No products in the cart.")
            return
        
        total = carrito.obtener_total()
        
        # Mensaje diferente si es una orden guardada
        if self.folio_actual and self.orden_guardada:
            mensaje_confirmacion = f"Register order {self.folio_actual:06d} as a completed sale?\n\n"
        else:
            mensaje_confirmacion = f"Register order to '{nombre_cliente}'?\n\n"
        
        mensaje_confirmacion += f"Total: ${total:.2f}"
        
        if not messagebox.askyesno("Confirm Sale", mensaje_confirmacion):
            return

        try:
            id_cliente = widgets['clientes_map'][nombre_cliente]
            
            # Preparar items para registrar en BD - FORMATO CORREGIDO
            items_para_bd = []
            for item_key, item in carrito.items.items():
                # Formato: [id_producto, nombre, precio, cantidad, subtotal]
                items_para_bd.append([
                    item.id_producto,  # ID del producto
                    item.nombre_producto,
                    item.precio_unitario,
                    item.cantidad,
                    item.subtotal
                ])
            
            # Obtener fecha seleccionada de la pestaña
            fecha_str = widgets['fecha_var'].get()
            try:
                from datetime import datetime
                fecha_venta = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("Invalid Date", "Please use the format YYYY-MM-DD")
                return

            # Registrar venta en BD con fecha específica
            #resultado_venta = database.crear_factura_completa(id_cliente, items_para_bd, fecha_venta)
            # Usar folio específico si es una orden guardada
            folio_a_usar = self.folio_actual if (self.folio_actual and self.orden_guardada) else None
            resultado_venta = database.crear_factura_completa(id_cliente, items_para_bd, fecha_venta, folio_a_usar)

            if resultado_venta and resultado_venta['id_factura']:
                venta_id = resultado_venta['id_factura']
                folio_factura = resultado_venta['folio_numero']
                
                # Si era una orden guardada, marcarla como completada
                if self.folio_actual and self.orden_guardada:
                    self.orden_manager.marcar_como_completada(self.folio_actual, venta_id)
                
                # Generate PDF automáticamente
                self._generar_pdf_venta(widgets, venta_id, folio_factura)
                
                # Limpiar carrito directamente sin confirmaciones después de venta exitosa
                widgets['carrito_obj'].items.clear()
                widgets['carrito_obj']._actualizar_display()
                widgets['carrito_obj']._notificar_cambio()  # Trigger UI updates

                # Determinar si era una orden guardada ANTES de resetear estado
                era_orden_guardada = self.folio_actual and self.orden_guardada
                folio_orden = self.folio_actual

                # Resetear estado de orden guardada si aplica
                if era_orden_guardada:
                    tab_actual = self.notebook.select()
                    tab_id = tab_actual.split(".")[-1]
                    self.orden_guardada = False
                    self.folios_pestanas[tab_id] = None
                    self.folio_actual = None

                # Si era una orden guardada, mostrar confirmación y cerrar ventana automáticamente
                if era_orden_guardada:
                    messagebox.showinfo("Sale Completed",
                                    f"Sale registered successfully\n"
                                    f"ID de factura: {venta_id}\n"
                                    f"Folio: {folio_factura:06d}\n"
                                    f"Order {folio_orden:06d} marked as completed.\n\n"
                                    f"The window will close automatically.")

                    # Notificar al padre y cerrar ventana automáticamente
                    if self.is_launcher_context:
                        self._notificar_cambio_orden()
                    self.root.destroy()
                else:
                    messagebox.showinfo("Sale Successful",
                                      f"Sale registered successfully\n"
                                      f"ID: {venta_id}\n"
                                      f"Folio: {folio_factura:06d}\n\n"
                                      f"The cart has been cleared automatically.")
            else:
                messagebox.showerror("Error", "Could not register the sale in the database.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error processing sale: {str(e)}")
            import traceback
            traceback.print_exc()  # Para debugging

    def _limpiar_carrito(self, widgets):
        """Limpia el carrito y restablece el estado de la interfaz"""
        if not widgets['carrito_obj'].items:
            return
            
        if not messagebox.askyesno("Confirm Clear", 
                                 "Are you sure you want to clear the cart?"):
            return
            
        widgets['carrito_obj'].limpiar_carrito()
        self._actualizar_total(widgets)
        
        # Si estamos editando una orden guardada, resetear el estado
        tab_actual = self.notebook.select()
        tab_id = tab_actual.split(".")[-1]
        folio_actual_pestana = self.folios_pestanas.get(tab_id)

        if folio_actual_pestana and self.orden_guardada:
            self.orden_guardada = False
            self.folios_pestanas[tab_id] = None
            # Solo resetear folio_actual si es la misma pestaña
            if self.folio_actual == folio_actual_pestana:
                self.folio_actual = None
            
            # Refresh interfaz
            widgets['lbl_folio_info'].config(
                text="New order (unsaved changes)",
                foreground="orange"
            )
            
            # Refresh título de pestaña
            tab_actual = self.notebook.select()
            self.notebook.tab(tab_actual, text="Order 1")
            
            self.lbl_orden_info.config(
                text="New order (unsaved changes)",
                foreground="orange"
            )
            
            self.root.title("Market - Sales System with Saved Orders")

    # ==================== MÉTODOS EXISTENTES (SIN CAMBIOS) ====================

    def _on_grupo_selected(self, event, widgets):
        """Maneja la selección de grupo de cliente"""
        grupo_seleccionado = widgets['combo_grupos'].get()
        if grupo_seleccionado:
            grupo_id = self.grupos_data[grupo_seleccionado]
            clientes = database.obtener_clientes_por_grupo(grupo_id)
            
            nombres_clientes = [nombre for _, nombre in clientes]
            widgets['combo_clientes']['values'] = nombres_clientes
            widgets['combo_clientes']['state'] = 'readonly'
            
            # Guardar mapping de nombres a IDs
            widgets['clientes_map'] = {nombre: id_cliente for id_cliente, nombre in clientes}
        else:
            widgets['combo_clientes']['state'] = 'disabled'
            widgets['combo_clientes'].set('')

    def _buscar_insumos(self, widgets):
        """Busca insumos en la base de datos"""
        query = widgets['entry_busqueda'].get().strip()
        
        grupo_seleccionado = widgets['combo_grupos'].get()
        if not grupo_seleccionado:
            messagebox.showwarning("Missing Group", "Please select a group first.")
            return
            
        grupo_id = self.grupos_data[grupo_seleccionado]
        
        # Si la búsqueda está vacía, mostrar todos los productos
        if not query:
            resultados: list[Any] = database.buscar_todos_insumos(grupo_id)
        else:
            resultados = database.buscar_insumos(query, grupo_id)
        
        # Limpiar resultados anteriores
        for item in widgets['tree_resultados'].get_children():
            widgets['tree_resultados'].delete(item)
            
        # Mostrar nuevos resultados
        for insumo in resultados:
            widgets['tree_resultados'].insert("", "end", values=(
                insumo['nombre'], 
                f"${insumo['precio']:.2f}"
            ), tags=(insumo['id'],))

    def _abrir_ventana_cantidad(self, event, widgets):
        """Abre ventana para seleccionar cantidad del producto"""
        seleccion = widgets['tree_resultados'].selection()
        if not seleccion:
            return
            
        item = widgets['tree_resultados'].item(seleccion[0])
        id_insumo = item['tags'][0]
        nombre_insumo = item['values'][0]
        precio = float(item['values'][1].replace('$', ''))
        
        # Obtener información adicional del producto
        grupo_id = self.grupos_data[widgets['combo_grupos'].get()]
        productos: list[Any] = database.buscar_insumos(nombre_insumo, grupo_id)
        unidad_producto = "unidad"  # Valor por defecto
        es_especial = False
        
        for producto in productos:
            if producto['id'] == int(id_insumo):
                unidad_producto = producto.get('unidad', 'unidad')
                es_especial = producto.get('es_especial', False)
                break
        
        # Abrir diálogo de cantidad
        dialogo = tk.Toplevel(self.root)
        dialogo.title(f"Quantity - {nombre_insumo}")
        
        # Ajustar tamaño según si es especial o no
        if es_especial:
            dialogo.geometry("400x280")
        else:
            dialogo.geometry("350x200")
        
        dialogo.resizable(False, False)
        dialogo.transient(self.root)
        dialogo.grab_set()
        
        # Información del producto
        ttk.Label(dialogo, text=f"Product: {nombre_insumo}").pack(pady=10)
        
        # Mostrar si es producto especial
        if es_especial:
            ttk.Label(dialogo, text="⭐ SPECIAL PRODUCT", 
                    font=("Arial", 10, "bold"), 
                    foreground="orange").pack()
        
        ttk.Label(dialogo, text=f"Base price: ${precio:.2f}").pack()
        
        # Frame para cantidad
        frame_cantidad = ttk.Frame(dialogo)
        frame_cantidad.pack(pady=10)
        
        ttk.Label(frame_cantidad, text="Quantity:").pack(side="left")
        cantidad_var = tk.DoubleVar(value=1.0)
        spinbox = ttk.Spinbox(frame_cantidad, from_=0.1, to=10000.0, increment=0.1, 
                            textvariable=cantidad_var, width=10)
        spinbox.pack(side="left", padx=5)
        
        # Frame para precio (solo si es especial)
        precio_var = tk.DoubleVar(value=precio)
        
        if es_especial:
            frame_precio = ttk.Frame(dialogo)
            frame_precio.pack(pady=10)
            
            ttk.Label(frame_precio, text="Custom price:").pack(side="left")
            entry_precio = ttk.Entry(frame_precio, textvariable=precio_var, width=10)
            entry_precio.pack(side="left", padx=5)
            ttk.Label(frame_precio, text="$").pack(side="left")
            
            # Nota explicativa
            ttk.Label(dialogo, text="💡 You can modify the price for this special product",
                    font=("Arial", 8), foreground="gray").pack(pady=(5, 0))
        
        def agregar_al_carrito():
            cantidad = cantidad_var.get()
            if cantidad <= 0:
                messagebox.showwarning("Invalid Quantity", "Quantity must be greater than 0.")
                return
            
            # Obtener precio final (personalizado si es especial, original si no)
            precio_final = precio_var.get() if es_especial else precio
            
            if es_especial and precio_final <= 0:
                messagebox.showwarning("Invalid Price", "Price must be greater than 0.")
                return
                
            # Verificar si hay secciones habilitadas
            carrito = widgets['carrito_obj']
            if carrito.sectioning_enabled and len(carrito.secciones) > 1:
                # Abrir diálogo de selección de sección
                secciones_list = list(carrito.secciones.values())
                dialogo_seccion = DialogoSeccion(
                    dialogo, 
                    secciones_list,
                    lambda seccion_id: self._agregar_a_seccion_y_cerrar(
                        int(id_insumo), nombre_insumo, cantidad, precio_final, unidad_producto, seccion_id, widgets, dialogo
                    )
                )
            else:
                # Add directamente al carrito
                self._agregar_a_seccion(int(id_insumo), nombre_insumo, cantidad, precio_final, unidad_producto, None, widgets)
                dialogo.destroy()
        
        # Botón Add - SIEMPRE visible
        frame_botones = ttk.Frame(dialogo)
        frame_botones.pack(pady=15)
        
        btn_agregar = ttk.Button(frame_botones, text="Add", command=agregar_al_carrito)
        btn_agregar.pack(side="left", padx=5)
        
        btn_cancelar = ttk.Button(frame_botones, text="Cancel", command=dialogo.destroy)
        btn_cancelar.pack(side="left", padx=5)
        
        # Centrar diálogo
        dialogo.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialogo.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialogo.winfo_height()) // 2
        dialogo.geometry(f"+{x}+{y}")
        
        # Hacer focus en cantidad para fácil edición
        spinbox.focus_set()
        spinbox.selection_range(0, 'end')

    def _agregar_a_seccion(self, id_insumo, nombre_insumo, cantidad, precio, unidad_producto, seccion_id, widgets):
        """Agrega un producto a la sección especificada del carrito"""
        widgets['carrito_obj'].agregar_item(
            id_insumo, nombre_insumo, cantidad, precio, unidad_producto, seccion_id
        )
        self._actualizar_total(widgets)

    def _agregar_a_seccion_y_cerrar(self, id_insumo, nombre_insumo, cantidad, precio, unidad_producto, seccion_id, widgets, dialogo_principal):
        """Agrega un producto a la sección especificada y cierra el diálogo principal"""
        self._agregar_a_seccion(id_insumo, nombre_insumo, cantidad, precio, unidad_producto, seccion_id, widgets)
        dialogo_principal.destroy()

    def _actualizar_total(self, widgets):
        """Actualiza el total y contador de productos"""
        carrito = widgets['carrito_obj']
        total = carrito.obtener_total()
        cantidad_total = carrito.obtener_cantidad_total()
        
        widgets['lbl_total_valor'].config(text=f"${total:.2f}")
        widgets['lbl_contador'].config(text=f"{cantidad_total} productos")
        
        # Refresh estado de botones según si hay unsaved changes
        if self.folio_actual and self.orden_guardada:
            widgets['lbl_folio_info'].config(
                text=f"Order {self.folio_actual:06d} (unsaved changes)",
                foreground="orange"
            )

    def _generar_pdf_venta(self, widgets, venta_id, folio_numero):
        """Genera PDF de la venta registrada"""
        try:
            nombre_cliente = widgets['combo_clientes'].get()
            carrito = widgets['carrito_obj']
            total = carrito.obtener_total()
            
            # Obtener items del carrito en formato correcto
            items_carrito = self._convertir_carrito_a_formato_pdf(carrito)
            
            # Determinar si usar secciones
            if carrito.sectioning_enabled and len(carrito.secciones) > 1:
                items_por_seccion = carrito.obtener_items_por_seccion()
                # Filtrar secciones vacías
                items_por_seccion = {k: v for k, v in items_por_seccion.items() if v['items']}
                
                if len(items_por_seccion) > 1:
                    # Usar formato con secciones
                    ruta_pdf = generador_pdf.crear_recibo_con_secciones(
                        nombre_cliente, items_por_seccion, total, folio_numero
                    )
                else:
                    # Una sola sección, usar formato simple
                    ruta_pdf = generador_pdf.crear_recibo_simple(
                        nombre_cliente, items_carrito, f"${total:.2f}", folio_numero
                    )
            else:
                # Sin secciones, usar formato simple
                ruta_pdf = generador_pdf.crear_recibo_simple(
                    nombre_cliente, items_carrito, f"${total:.2f}", folio_numero
                )
            
            if ruta_pdf:
                messagebox.showinfo("PDF generated", f"PDF saved to: {ruta_pdf}")
            else:
                messagebox.showerror("Error", "Could not generate PDF")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error generating PDF: {str(e)}")
            import traceback
            traceback.print_exc()

    def _generar_pdf_solo(self, widgets):
        """Genera PDF sin registrar venta"""
        try:
            nombre_cliente = widgets['combo_clientes'].get()
            if not nombre_cliente:
                messagebox.showwarning("Missing Client", "Please, select a client.")
                return

            carrito = widgets['carrito_obj']
            if not carrito.items:
                messagebox.showwarning("Empty Cart", "No products in the cart.")
                return
            
            total = carrito.obtener_total()
            
            # Usar folio de orden si existe, sino None (será un borrador)
            folio = self.folio_actual
            
            # Obtener items del carrito en formato correcto
            items_carrito = self._convertir_carrito_a_formato_pdf(carrito)
            
            # Determinar si usar secciones
            if carrito.sectioning_enabled and len(carrito.secciones) > 1:
                items_por_seccion = carrito.obtener_items_por_seccion()
                # Filtrar secciones vacías
                items_por_seccion = {k: v for k, v in items_por_seccion.items() if v['items']}
                
                if len(items_por_seccion) > 1:
                    # Usar formato con secciones
                    ruta_pdf = generador_pdf.crear_recibo_con_secciones(
                        nombre_cliente, items_por_seccion, total, folio
                    )
                else:
                    # Una sola sección, usar formato simple
                    ruta_pdf = generador_pdf.crear_recibo_simple(
                        nombre_cliente, items_carrito, f"${total:.2f}", folio
                    )
            else:
                # Sin secciones, usar formato simple
                ruta_pdf = generador_pdf.crear_recibo_simple(
                    nombre_cliente, items_carrito, f"${total:.2f}", folio
                )
            
            if ruta_pdf:
                messagebox.showinfo("PDF generated", f"PDF saved to: {ruta_pdf}")
            else:
                messagebox.showerror("Error", "Could not generate PDF")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error generating PDF: {str(e)}")
            import traceback
            traceback.print_exc()

    def _generar_excel(self, widgets):
        """Genera archivo Excel del carrito actual"""
        try:
            nombre_cliente = widgets['combo_clientes'].get()
            if not nombre_cliente:
                messagebox.showwarning("Missing Client", "Please, select a client")
                return

            carrito = widgets['carrito_obj']
            if not carrito.items:
                messagebox.showwarning("Empty Cart", "No products in the cart.")
                return
            
            total = carrito.obtener_total()
            
            # Obtener items del carrito en formato correcto
            items_carrito = self._convertir_carrito_a_formato_excel(carrito)
            
            # Determinar si usar secciones
            if carrito.sectioning_enabled and len(carrito.secciones) > 1:
                items_por_seccion = carrito.obtener_items_por_seccion()
                # Filtrar secciones vacías y convertir formato
                items_por_seccion_convertidas = {}
                for nombre_seccion, datos in items_por_seccion.items():
                    if datos['items']:
                        items_convertidos = self._convertir_items_seccion_excel(datos['items'])
                        items_por_seccion_convertidas[nombre_seccion] = {
                            'items': items_convertidos,
                            'subtotal': datos['subtotal']
                        }
                
                if len(items_por_seccion_convertidas) > 1:
                    # Usar formato con secciones
                    ruta_excel = generador_excel.crear_excel_con_secciones(
                        nombre_cliente, items_por_seccion_convertidas, total
                    )
                else:
                    # Una sola sección, usar formato simple
                    ruta_excel = generador_excel.crear_excel_simple(nombre_cliente, items_carrito)
            else:
                # Sin secciones, usar formato simple
                ruta_excel = generador_excel.crear_excel_simple(nombre_cliente, items_carrito)
            
            if ruta_excel:
                messagebox.showinfo("Excel generated", f"Excel saved to: {ruta_excel}")
            else:
                messagebox.showerror("Error", "Could not generate Excel")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error generating Excel: {str(e)}")
            import traceback
            traceback.print_exc()

    def _convertir_carrito_a_formato_pdf(self, carrito):
        """Convierte items del carrito al formato esperado por generador_pdf"""
        items_convertidos = []
        for item_key, item in carrito.items.items():
            # Formato: ['cantidad', 'producto', 'precio_unit', 'subtotal']
            items_convertidos.append([
                f"{item.cantidad:.2f}",
                item.nombre_producto,
                f"${item.precio_unitario:.2f}",
                f"${item.subtotal:.2f}"
            ])
        return items_convertidos
    
    def _convertir_carrito_a_formato_excel(self, carrito):
        """Convierte items del carrito al formato esperado por generador_excel"""
        items_convertidos = []
        for item_key, item in carrito.items.items():
            # Formato: ['cantidad', 'producto', 'precio_unit', 'subtotal', 'unidad']
            items_convertidos.append([
                f"{item.cantidad:.2f}",
                item.nombre_producto,
                f"${item.precio_unitario:.2f}",
                f"${item.subtotal:.2f}",
                item.unidad_producto
            ])
        return items_convertidos
    
    def _convertir_items_seccion_excel(self, items_lista):
        """Convierte items de una sección al formato correcto para Excel"""
        # Los items ya están en formato correcto desde obtener_items_por_seccion()
        return items_lista

    def run(self):
        """Inicia la aplicación"""
        if not self.is_launcher_context:
            self.root.mainloop()
        else:
            # En contexto de launcher, ya está corriendo el mainloop del padre
            pass

def main():
    """Función principal para ejecutar la aplicación de forma independiente"""
    app = ReciboAppMejorado()
    app.run()

if __name__ == "__main__":
    main()