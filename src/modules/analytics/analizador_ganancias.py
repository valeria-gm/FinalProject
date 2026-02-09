import os
import tkinter as tk
from tkinter import messagebox, ttk
import mysql.connector
from src.database.conexion import conectar
from decimal import Decimal
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.ticker import FuncFormatter
from collections import defaultdict
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime, timedelta
import numpy as np

class AnalisisGananciasApp:
    def __init__(self, root, user_data):
        self.root = root
        self.root.title("Análisis de Ganancias - Disfruleg")
        self.root.geometry("1000x700")
        
        self.user_data = user_data if isinstance(user_data, dict) else {}
        self.es_admin = (self.user_data.get('rol', '') == 'admin')
        
        # Connect to database
        try:
            self.conn = conectar()
            self.cursor = self.conn.cursor(dictionary=True)
        except mysql.connector.Error as err:
            messagebox.showerror("Error de conexión", f"No se pudo conectar a la base de datos:\n{err}")
            self.root.destroy()
            return
        
        self.all_products = []
        self.create_interface()
        self.load_analysis()
        
    def create_interface(self):
        # Title
        title_frame = tk.Frame(self.root)
        title_frame.pack(fill="x", pady=10)
        
        tk.Label(title_frame, text="ANÁLISIS DE GANANCIAS POR PRODUCTO", 
                font=("Arial", 18, "bold")).pack()
        
        # Buttons frame
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill="x", pady=5, padx=10)
        
        tk.Button(button_frame, text="Actualizar Análisis", command=self.load_analysis, 
                  bg="#4CAF50", fg="white", padx=10, pady=3).pack(side="left", padx=5)
        
        tk.Button(button_frame, text="Exportar PDF", command=self.export_to_pdf, 
                  bg="#2196F3", fg="white", padx=10, pady=3).pack(side="left", padx=5)
        
        tk.Button(button_frame, text="Estadísticas Avanzadas", command=self.show_advanced_stats,
                  bg="#9C27B0", fg="white", padx=10, pady=3).pack(side="left", padx=5)

        # Create main container with two sections
        main_container = tk.Frame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Summary section (top)
        self.create_summary_section(main_container)
        
        # Detail table (bottom)
        self.create_detail_section(main_container)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set(f"Usuario: {self.user_data.get('nombre_completo', '')} | Rol: {self.user_data.get('rol', '')} | Listo")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_summary_section(self, parent):
        # Summary frame
        summary_frame = tk.LabelFrame(parent, text="Resumen General", padx=10, pady=10)
        summary_frame.pack(fill="x", pady=(0, 10))
        
        # Create grid for summary cards
        summary_grid = tk.Frame(summary_frame)
        summary_grid.pack(fill="x")
        
        # Variables for summary
        self.total_ventas_var = tk.StringVar(value="$0.00")
        self.total_costos_var = tk.StringVar(value="$0.00")
        self.ganancia_total_var = tk.StringVar(value="$0.00")
        self.margen_promedio_var = tk.StringVar(value="0%")
        
        # Create summary cards
        self.create_summary_card(summary_grid, "Ventas Totales", self.total_ventas_var, "#4CAF50", 0, 0)
        self.create_summary_card(summary_grid, "Costos Totales", self.total_costos_var, "#f44336", 0, 1)
        self.create_summary_card(summary_grid, "Ganancia Total", self.ganancia_total_var, "#2196F3", 0, 2)
        self.create_summary_card(summary_grid, "Margen Promedio", self.margen_promedio_var, "#FF5722", 0, 3)
    
    def create_summary_card(self, parent, title, text_var, color, row, col):
        card = tk.Frame(parent, bg=color, relief=tk.RAISED, bd=2)
        card.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
        parent.columnconfigure(col, weight=1)
        
        tk.Label(card, text=title, font=("Arial", 10), bg=color, fg="white").pack(pady=5)
        tk.Label(card, textvariable=text_var, font=("Arial", 14, "bold"), 
                bg=color, fg="white").pack(pady=5)
    
    def create_detail_section(self, parent):
        # Detail frame
        detail_frame = tk.LabelFrame(parent, text="Detalles por Producto", padx=10, pady=10)
        detail_frame.pack(fill="both", expand=True)
        
        # Search frame
        search_frame = tk.Frame(detail_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(search_frame, text="Buscar producto:").pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side="left", padx=5)
        self.search_var.trace("w", self.filter_products)
        
        # Filter buttons
        filter_frame = tk.Frame(search_frame)
        filter_frame.pack(side="right")
        
        tk.Button(filter_frame, text="Solo con Ganancia", command=lambda: self.apply_filter("ganancia"),
                  bg="#4CAF50", fg="white", padx=10, pady=3).pack(side="left", padx=2)
        tk.Button(filter_frame, text="Solo con Pérdida", command=lambda: self.apply_filter("perdida"),
                  bg="#f44336", fg="white", padx=10, pady=3).pack(side="left", padx=2)
        tk.Button(filter_frame, text="Mostrar Todo", command=lambda: self.apply_filter("todos"),
                  bg="#607D8B", fg="white", padx=10, pady=3).pack(side="left", padx=2)
        
        # Create treeview
        self.create_treeview(detail_frame)
    
    def create_treeview(self, parent):
        # Frame for table with scrollbar
        table_frame = tk.Frame(parent)
        table_frame.pack(fill="both", expand=True)
        
        # Scrollbars
        v_scrollbar = tk.Scrollbar(table_frame)
        v_scrollbar.pack(side="right", fill="y")
        
        h_scrollbar = tk.Scrollbar(table_frame, orient="horizontal")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Treeview
        columns = ("id", "producto", "unidad", "vendido", "precio_venta", 
                  "ingresos", "comprado", "precio_compra", "costos", 
                  "ganancia", "margen", "stock")
        
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                               yscrollcommand=v_scrollbar.set,
                               xscrollcommand=h_scrollbar.set)
        
        # Configure columns
        column_configs = {
            "id": ("ID", 50),
            "producto": ("Producto", 150),
            "unidad": ("Unidad", 70),
            "vendido": ("Cant. Vendida", 80),
            "precio_venta": ("Precio Venta", 90),
            "ingresos": ("Ingresos", 90),
            "comprado": ("Cant. Comprada", 90),
            "precio_compra": ("Precio Compra", 90),
            "costos": ("Costos", 90),
            "ganancia": ("Ganancia", 90),
            "margen": ("Margen %", 80),
            "stock": ("Stock Est.", 80)
        }
        
        for col, (heading, width) in column_configs.items():
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width)
        
        self.tree.pack(side="left", fill="both", expand=True)
        
        # Configure scrollbars
        v_scrollbar.config(command=self.tree.yview)
        h_scrollbar.config(command=self.tree.xview)
    
    def load_analysis(self):
        """Load profitability analysis using the new database structure with views"""
        try:
            # Use the new vista_ganancias_por_producto view for analysis
            self.cursor.execute("""
                SELECT 
                    vgp.id_producto,
                    vgp.nombre_producto,
                    vgp.unidad_producto as unidad,
                    vgp.stock,
                    COALESCE(vgp.cantidad_vendida, 0) as cantidad_vendida,
                    CASE 
                        WHEN COALESCE(vgp.cantidad_vendida, 0) > 0 
                        THEN ROUND(vgp.ingresos_totales / vgp.cantidad_vendida, 2)
                        ELSE 0
                    END as precio_promedio_venta,
                    COALESCE(vgp.ingresos_totales, 0) as ingresos_totales,
                    COALESCE(vgp.cantidad_comprada, 0) as cantidad_comprada,
                    CASE 
                        WHEN COALESCE(vgp.cantidad_comprada, 0) > 0 
                        THEN ROUND(vgp.costos_totales / vgp.cantidad_comprada, 2)
                        ELSE 0
                    END as precio_promedio_compra,
                    COALESCE(vgp.costos_totales, 0) as costos_totales,
                    COALESCE(vgp.ganancia_total, 0) as ganancia_total,
                    COALESCE(vgp.margen_ganancia_porcentaje, 0) as margen_ganancia_porcentaje
                FROM vista_ganancias_por_producto vgp
                ORDER BY vgp.ganancia_total DESC
            """)
            
            products = self.cursor.fetchall()
            self.all_products = products
            
            # Clear existing data
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Calculate totals for summary
            total_ventas = sum(float(p['ingresos_totales'] or 0) for p in products)
            total_costos = sum(float(p['costos_totales'] or 0) for p in products)
            ganancia_total = total_ventas - total_costos
            
            # Calculate average margin
            productos_con_margen = [p for p in products 
                                   if p['margen_ganancia_porcentaje'] and float(p['margen_ganancia_porcentaje']) != 0]
            margen_promedio = (sum(float(p['margen_ganancia_porcentaje']) for p in productos_con_margen) / 
                              len(productos_con_margen)) if productos_con_margen else 0
            
            # Update summary with formatted numbers
            self.total_ventas_var.set(f"${total_ventas:,.2f}")
            self.total_costos_var.set(f"${total_costos:,.2f}")
            self.ganancia_total_var.set(f"${ganancia_total:,.2f}")
            self.margen_promedio_var.set(f"{margen_promedio:,.1f}%")
            
            # Populate tree
            for product in products:
                # Color coding for ganancia
                ganancia = float(product['ganancia_total'] or 0)
                if ganancia > 0:
                    tags = ('positive',)
                elif ganancia < 0:
                    tags = ('negative',)
                else:
                    tags = ('neutral',)
                
                self.tree.insert("", "end", values=(
                    product['id_producto'],
                    product['nombre_producto'],
                    product['unidad'],
                    f"{float(product['cantidad_vendida'] or 0):,.2f}",
                    f"${float(product['precio_promedio_venta'] or 0):,.2f}",
                    f"${float(product['ingresos_totales'] or 0):,.2f}",
                    f"{float(product['cantidad_comprada'] or 0):,.2f}",
                    f"${float(product['precio_promedio_compra'] or 0):,.2f}",
                    f"${float(product['costos_totales'] or 0):,.2f}",
                    f"${ganancia:,.2f}",
                    f"{float(product['margen_ganancia_porcentaje'] or 0):,.1f}%",
                    f"{float(product['stock'] or 0):,.2f}"
                ), tags=tags)
            
            # Configure tags for color coding
            self.tree.tag_configure('positive', background='#E8F5E9')
            self.tree.tag_configure('negative', background='#FFEBEE')
            self.tree.tag_configure('neutral', background='#F5F5F5')
            
            self.status_var.set(f"Análisis actualizado - {len(products)} productos analizados")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar análisis: {str(e)}")
            print(f"Error: {e}")
    
    def filter_products(self, *args):
        """Filter products based on search text"""
        search_text = self.search_var.get().lower()
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Filter products
        for product in self.all_products:
            if search_text in product['nombre_producto'].lower():
                ganancia = float(product['ganancia_total'] or 0)
                if ganancia > 0:
                    tags = ('positive',)
                elif ganancia < 0:
                    tags = ('negative',)
                else:
                    tags = ('neutral',)
                
                self.tree.insert("", "end", values=(
                    product['id_producto'],
                    product['nombre_producto'],
                    product['unidad'],
                    f"{float(product['cantidad_vendida'] or 0):,.2f}",
                    f"${float(product['precio_promedio_venta'] or 0):,.2f}",
                    f"${float(product['ingresos_totales'] or 0):,.2f}",
                    f"{float(product['cantidad_comprada'] or 0):,.2f}",
                    f"${float(product['precio_promedio_compra'] or 0):,.2f}",
                    f"${float(product['costos_totales'] or 0):,.2f}",
                    f"${ganancia:,.2f}",
                    f"{float(product['margen_ganancia_porcentaje'] or 0):,.1f}%",
                    f"{float(product['stock'] or 0):,.2f}"
                ), tags=tags)
    
    def apply_filter(self, filter_type):
        """Apply specific filters"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Filter based on type
        for product in self.all_products:
            ganancia = float(product['ganancia_total'] or 0)
            
            should_include = False
            if filter_type == "ganancia" and ganancia > 0:
                should_include = True
            elif filter_type == "perdida" and ganancia < 0:
                should_include = True
            elif filter_type == "todos":
                should_include = True
            
            if should_include:
                if ganancia > 0:
                    tags = ('positive',)
                elif ganancia < 0:
                    tags = ('negative',)
                else:
                    tags = ('neutral',)
                
                self.tree.insert("", "end", values=(
                    product['id_producto'],
                    product['nombre_producto'],
                    product['unidad'],
                    f"{float(product['cantidad_vendida'] or 0):,.2f}",
                    f"${float(product['precio_promedio_venta'] or 0):,.2f}",
                    f"${float(product['ingresos_totales'] or 0):,.2f}",
                    f"{float(product['cantidad_comprada'] or 0):,.2f}",
                    f"${float(product['precio_promedio_compra'] or 0):,.2f}",
                    f"${float(product['costos_totales'] or 0):,.2f}",
                    f"${ganancia:,.2f}",
                    f"{float(product['margen_ganancia_porcentaje'] or 0):,.1f}%",
                    f"{float(product['stock'] or 0):,.2f}"
                ), tags=tags)

    def show_advanced_stats(self):
        """Muestra estadísticas avanzadas con visualizaciones interactivas mejoradas."""
        
        class StatsWindow:
            def __init__(self, parent, db_cursor, db_connection):
                self.parent = parent
                self.cursor = db_cursor
                self.conn = db_connection
                self.window = tk.Toplevel(parent)
                self.window.title("Estadísticas Avanzadas - Disfruleg")
                self.window.geometry("1300x900")
                self.window.protocol("WM_DELETE_WINDOW", self.cleanup)
                
                # Variables para navegación histórica
                self.current_period_index = 0
                self.available_periods = []
                
                # Configuración de estilo
                self.style = ttk.Style()
                self.style.configure("TNotebook.Tab", font=('Arial', 10, 'bold'))
                
                self.setup_ui()
                self.load_data()

            def ensure_decimal(self, value):
                """Asegura que el valor sea Decimal, convirtiéndolo si es necesario."""
                if value is None:
                    return Decimal('0.0')
                if isinstance(value, Decimal):
                    return value
                try:
                    return Decimal(str(value))
                except:
                    return Decimal('0.0')
                
            def convert_decimal(self, value):
                """Convierte valores Decimal de MySQL a float para matplotlib."""
                if value is None:
                    return 0.0
                try:
                    return float(self.ensure_decimal(value))
                except:
                    return 0.0
                
            def setup_ui(self):
                """Configura la interfaz de usuario principal."""
                self.notebook = ttk.Notebook(self.window)
                self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
                
                # Pestañas principales
                self.tabs = {
                    "sales": self.create_tab("Ventas y Pérdidas por Producto"),
                    "profits": self.create_tab("Ganancias por Producto"),
                    "temporal": self.create_tab("Tendencias Temporales"),
                    "clients": self.create_tab("Clientes"),
                    "groups": self.create_tab("Grupos de Clientes")
                }
                
                # Barra de estado
                self.status_var = tk.StringVar()
                self.status_bar = ttk.Label(
                    self.window, 
                    textvariable=self.status_var,
                    relief="sunken",
                    anchor="w"
                )
                self.status_bar.pack(side="bottom", fill="x")
                
            def create_tab(self, name):
                """Crea una pestaña con contenedor para gráficos."""
                frame = ttk.Frame(self.notebook)
                self.notebook.add(frame, text=name)
                
                container = ttk.Frame(frame)
                container.pack(fill="both", expand=True)
                
                return {
                    "frame": frame,
                    "container": container,
                    "current_figure": None
                }
                
            def load_data(self):
                """Carga los datos y genera visualizaciones."""
                self.status_var.set("Cargando datos...")
                self.window.update_idletasks()
                
                try:
                    # Cargar datos en segundo plano para no bloquear la UI
                    self.window.after(100, self.generate_all_charts)
                except Exception as e:
                    messagebox.showerror("Error", f"Error al cargar datos: {str(e)}")
                    self.window.destroy()
                    
            def generate_all_charts(self):
                """Genera todas las visualizaciones."""
                try:
                    self.generate_sales_chart()
                    self.generate_profits_chart()
                    self.generate_temporal_chart()
                    self.generate_clients_chart()
                    self.generate_groups_chart()
                    self.status_var.set("Listo")
                except Exception as e:
                    self.status_var.set(f"Error: {str(e)}")
                    messagebox.showerror("Error", f"No se pudieron generar todos los gráficos: {str(e)}")
                    
            def generate_sales_chart(self):
                """Genera gráficos de productos rentables y con pérdidas usando las vistas."""
                try:
                    # Usar la vista vista_ganancias_por_producto
                    self.cursor.execute("""
                        SELECT 
                            nombre_producto,
                            COALESCE(ganancia_total, 0) AS ganancia_total
                        FROM vista_ganancias_por_producto
                        WHERE ganancia_total IS NOT NULL
                        ORDER BY ganancia_total DESC
                    """)
                    all_products = self.cursor.fetchall()
                    
                    # Filtrar productos rentables (top 10)
                    profitable_products = sorted([p for p in all_products if float(p['ganancia_total']) > 0],
                                            key=lambda x: float(x['ganancia_total']), reverse=True)[:10]
                    
                    # Filtrar productos con pérdidas (top 10)
                    loss_products = sorted([p for p in all_products if float(p['ganancia_total']) < 0],
                                        key=lambda x: float(x['ganancia_total']))[:10]
                    
                    if not profitable_products and not loss_products:
                        self.show_no_data_message(self.tabs["sales"]["container"])
                        return
                    
                    fig = plt.Figure(figsize=(14, 10), tight_layout=True)
                    
                    # Gráfico de productos rentables
                    if profitable_products:
                        ax1 = fig.add_subplot(2, 1, 1)
                        names = [p['nombre_producto'][:20] + '...' if len(p['nombre_producto']) > 20 
                                else p['nombre_producto'] for p in profitable_products]
                        ganancias = [float(p['ganancia_total']) for p in profitable_products]
                        
                        bars = ax1.barh(names, ganancias, color='#A5D6A7')
                        ax1.set_title('Top 10 Productos Más Rentables', fontsize=14, fontweight='bold')
                        ax1.set_xlabel('Ganancia ($)', fontsize=12)
                        
                        # Añadir etiquetas de valor mejoradas
                        max_val = max(abs(g) for g in ganancias) if ganancias else 0
                        for bar, ganancia in zip(bars, ganancias):
                            width = bar.get_width()
                            ax1.text(width + (max_val * 0.01),
                                    bar.get_y() + bar.get_height()/2,
                                    f'${ganancia:,.2f}', 
                                    ha='left', va='center', fontsize=10, fontweight='bold')
                        
                        ax1.grid(axis='x', alpha=0.3)
                    
                    # Gráfico de productos con pérdidas
                    if loss_products:
                        ax2 = fig.add_subplot(2, 1, 2)
                        names = [p['nombre_producto'][:20] + '...' if len(p['nombre_producto']) > 20 
                                else p['nombre_producto'] for p in loss_products]
                        perdidas = [abs(float(p['ganancia_total'])) for p in loss_products]
                        
                        bars = ax2.barh(names, perdidas, color='#EF9A9A')
                        ax2.set_title('Top 10 Productos con Mayor Pérdida', fontsize=14, fontweight='bold')
                        ax2.set_xlabel('Pérdida ($)', fontsize=12)
                        
                        # Añadir etiquetas de valor mejoradas
                        max_val = max(abs(g) for g in perdidas) if perdidas else 0
                        for bar, perdida in zip(bars, perdidas):
                            width = bar.get_width()
                            ax2.text(width + (max_val * 0.01),
                                    bar.get_y() + bar.get_height()/2,
                                    f'${perdida:,.2f}', 
                                    ha='left', va='center', fontsize=10, fontweight='bold')
                        
                        ax2.grid(axis='x', alpha=0.3)
                    
                    self.embed_plot(fig, self.tabs["sales"]["container"])
                    
                except Exception as e:
                    self.show_error_message(self.tabs["sales"]["container"], str(e))

            def generate_profits_chart(self):
                """Genera gráfico de ganancias por producto usando vista."""
                try:
                    self.cursor.execute("""
                        SELECT 
                            nombre_producto,
                            COALESCE(ganancia_total, 0) AS ganancia,
                            COALESCE(margen_ganancia_porcentaje, 0) AS margen
                        FROM vista_ganancias_por_producto
                        WHERE ganancia_total IS NOT NULL
                        ORDER BY ganancia_total DESC
                        LIMIT 15
                    """)
                    data = self.cursor.fetchall()
                
                    if not data:
                        self.show_no_data_message(self.tabs["profits"]["container"])
                        return
                    
                    fig, ax = plt.subplots(figsize=(14, 8))
                    
                    # Formateador para valores monetarios
                    formatter = FuncFormatter(lambda x, _: f"${x:,.2f}" if x is not None else "$0.00")
                    ax.xaxis.set_major_formatter(formatter)
                    
                    ganancias = [float(p['ganancia']) for p in data]
                    nombres = [p['nombre_producto'][:25] + ('...' if len(p['nombre_producto']) > 25 else '') 
                              for p in data]
                    
                    # Colores según ganancia/pérdida
                    colors = ['#A5D6A7' if g >= 0 else '#EF9A9A' for g in ganancias]
                    
                    bars = ax.barh(nombres, ganancias, color=colors)
                    ax.set_title("Ganancia por Producto (Top 15)\nVerde: Ganancia | Rojo: Pérdida", 
                               fontsize=14, fontweight='bold')
                    ax.set_xlabel("Ganancia Total ($)", fontsize=12)
                    
                    # Añadir etiquetas de valor mejoradas
                    max_val = max(abs(g) for g in ganancias) if ganancias else 0
                    for bar, ganancia, producto in zip(bars, ganancias, data):
                        width = bar.get_width()
                        margen = float(producto['margen'])
                        
                        # Posición de etiqueta
                        if ganancia >= 0:
                            x_pos = width + (max_val * 0.01)
                            ha = 'left'
                        else:
                            x_pos = width - (max_val * 0.01)
                            ha = 'right'
                            
                        ax.text(x_pos, bar.get_y() + bar.get_height()/2,
                                f"${ganancia:,.2f}\n({margen:.1f}%)",
                                va='center', ha=ha, fontsize=9, fontweight='bold')
                    
                    ax.grid(axis='x', alpha=0.3)
                    ax.axvline(x=0, color='black', linewidth=1, alpha=0.5)
                    
                    plt.tight_layout()
                    self.embed_plot(fig, self.tabs["profits"]["container"])
                    
                except Exception as e:
                    self.show_error_message(self.tabs["profits"]["container"], str(e))
                
            def generate_temporal_chart(self):
                """Genera gráfico temporal con selector de período y tipo de análisis mejorado."""
                try:
                    frame = self.tabs["temporal"]["frame"]
                    
                    # Frame de controles
                    control_frame = ttk.Frame(frame)
                    control_frame.pack(fill="x", padx=10, pady=5)
                    
                    # Primera fila de controles
                    ttk.Label(control_frame, text="Agrupar por:").grid(row=0, column=0, padx=5, sticky="w")
                    
                    self.time_var = tk.StringVar(value="Mes")
                    time_options = ["Día", "Semana", "Mes", "Trimestre", "Año"]
                    
                    time_combo = ttk.Combobox(
                        control_frame,
                        textvariable=self.time_var,
                        values=time_options,
                        state="readonly",
                        width=15
                    )
                    time_combo.grid(row=0, column=1, padx=5)
                    
                    ttk.Label(control_frame, text="Tipo de análisis:").grid(row=0, column=2, padx=5, sticky="w")
                    
                    self.analysis_type_var = tk.StringVar(value="General")
                    analysis_options = ["General", "Por Producto", "Por Grupo de Clientes"]
                    
                    analysis_combo = ttk.Combobox(
                        control_frame,
                        textvariable=self.analysis_type_var,
                        values=analysis_options,
                        state="readonly",
                        width=20
                    )
                    analysis_combo.grid(row=0, column=3, padx=5)
                    
                    # Botón para actualizar
                    ttk.Button(control_frame, text="Actualizar", command=self.update_temporal_chart).grid(row=0, column=4, padx=10)
                    
                    # Segunda fila - Navegación histórica
                    nav_frame = ttk.Frame(control_frame)
                    nav_frame.grid(row=1, column=0, columnspan=5, pady=10, sticky="ew")
                    
                    ttk.Label(nav_frame, text="Navegación:").pack(side="left", padx=5)
                    
                    self.prev_button = ttk.Button(nav_frame, text="← Anterior", command=self.navigate_previous)
                    self.prev_button.pack(side="left", padx=5)
                    
                    self.period_label = ttk.Label(nav_frame, text="", background="white", relief="sunken", width=30)
                    self.period_label.pack(side="left", padx=5)
                    
                    self.next_button = ttk.Button(nav_frame, text="Siguiente →", command=self.navigate_next)
                    self.next_button.pack(side="left", padx=5)

                    # Frame del gráfico
                    self.tabs["temporal"]["graph_frame"] = ttk.Frame(frame)
                    self.tabs["temporal"]["graph_frame"].pack(fill="both", expand=True)
                    
                    self.update_temporal_chart()
                    
                except Exception as e:
                    self.show_error_message(self.tabs["temporal"]["container"], str(e))
            
            def get_period_data(self, period_type):
                """Obtiene los períodos disponibles según el tipo seleccionado."""
                period_queries = {
                    "Año": """
                        SELECT DISTINCT YEAR(f.fecha_factura) AS periodo 
                        FROM factura f
                        WHERE f.fecha_factura IS NOT NULL
                        ORDER BY periodo DESC
                        LIMIT 5
                    """,
                    "Trimestre": """
                        SELECT DISTINCT CONCAT(YEAR(f.fecha_factura), '-Q', QUARTER(f.fecha_factura)) AS periodo 
                        FROM factura f
                        WHERE f.fecha_factura IS NOT NULL
                        AND YEAR(f.fecha_factura) >= YEAR(CURRENT_DATE) - 2
                        ORDER BY periodo DESC
                        LIMIT 8
                    """,
                    "Mes": """
                        SELECT DISTINCT DATE_FORMAT(f.fecha_factura, '%Y-%m') AS periodo 
                        FROM factura f
                        WHERE f.fecha_factura IS NOT NULL
                        AND f.fecha_factura >= DATE_SUB(CURRENT_DATE, INTERVAL 12 MONTH)
                        ORDER BY periodo DESC
                        LIMIT 12
                    """,
                    "Semana": """
                        SELECT DISTINCT DATE_FORMAT(f.fecha_factura, '%x-W%v') AS periodo 
                        FROM factura f
                        WHERE f.fecha_factura IS NOT NULL
                        AND f.fecha_factura >= DATE_SUB(CURRENT_DATE, INTERVAL 12 WEEK)
                        ORDER BY periodo DESC
                        LIMIT 12
                    """,
                    "Día": """
                        SELECT DISTINCT DATE_FORMAT(f.fecha_factura, '%Y-%m-%d') AS periodo 
                        FROM factura f
                        WHERE f.fecha_factura IS NOT NULL
                        AND f.fecha_factura >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY)
                        ORDER BY periodo DESC
                        LIMIT 30
                    """
                }
                
                try:
                    query = period_queries.get(period_type, period_queries["Mes"])
                    self.cursor.execute(query)
                    periods = [str(row['periodo']) for row in self.cursor.fetchall()]
                    return periods
                except Exception as e:
                    print(f"Error obteniendo períodos: {e}")
                    return []
            
            def navigate_previous(self):
                """Navega al período anterior."""
                if self.current_period_index > 0:
                    self.current_period_index -= 1
                    self.update_temporal_chart()
            
            def navigate_next(self):
                """Navega al período siguiente."""
                max_periods = len(self.available_periods) - 5  # Mostrar 5 períodos por vez
                if self.current_period_index < max_periods:
                    self.current_period_index += 1
                    self.update_temporal_chart()
                    
            def update_temporal_chart(self, event=None):
                """Actualiza el gráfico temporal con mejoras implementadas."""
                try:
                    selected_period = self.time_var.get()
                    analysis_type = self.analysis_type_var.get()
                    
                    # Obtener períodos disponibles
                    self.available_periods = self.get_period_data(selected_period)
                    
                    if not self.available_periods:
                        self.show_no_data_message(self.tabs["temporal"]["graph_frame"])
                        return
                    
                    # Determinar períodos a mostrar
                    start_idx = self.current_period_index
                    end_idx = min(start_idx + 5, len(self.available_periods))
                    current_periods = self.available_periods[start_idx:end_idx]
                    
                    # Actualizar etiqueta de navegación
                    if current_periods:
                        period_range = f"{current_periods[-1]} - {current_periods[0]}"
                        self.period_label.config(text=f"Mostrando: {period_range}")
                    
                    # Actualizar botones de navegación
                    self.prev_button.config(state="normal" if self.current_period_index > 0 else "disabled")
                    self.next_button.config(state="normal" if end_idx < len(self.available_periods) else "disabled")
                    
                    if analysis_type == "General":
                        self.generate_general_temporal_chart(selected_period, current_periods)
                    elif analysis_type == "Por Producto":
                        self.generate_product_temporal_chart(selected_period, current_periods)
                    elif analysis_type == "Por Grupo de Clientes":
                        self.generate_group_temporal_chart(selected_period, current_periods)
                        
                except Exception as e:
                    self.show_error_message(self.tabs["temporal"]["graph_frame"], str(e))
            
            def generate_general_temporal_chart(self, period_type, periods):
                """Genera gráfico temporal general con ganancias y pérdidas separadas."""
                try:
                    period_func_map = {
                        "Día": "DATE(f.fecha_factura)",
                        "Semana": "DATE_FORMAT(f.fecha_factura, '%x-W%v')",
                        "Mes": "DATE_FORMAT(f.fecha_factura, '%Y-%m')",
                        "Trimestre": "CONCAT(YEAR(f.fecha_factura), '-Q', QUARTER(f.fecha_factura))",
                        "Año": "YEAR(f.fecha_factura)"
                    }
                    
                    period_func = period_func_map.get(period_type, "DATE_FORMAT(f.fecha_factura, '%Y-%m')")
                    
                    # Query mejorado usando vistas
                    self.cursor.execute(f"""
                        SELECT 
                            {period_func} AS periodo,
                            SUM(vd.subtotal_con_descuento) AS ventas_totales,
                            (SELECT COALESCE(SUM(c.cantidad_compra * c.precio_unitario_compra), 0)
                             FROM compra c 
                             WHERE {period_func.replace('f.fecha_factura', 'c.fecha_compra')} = periodo) AS compras_totales,
                            SUM(vd.subtotal_con_descuento) - 
                            (SELECT COALESCE(SUM(c.cantidad_compra * c.precio_unitario_compra), 0)
                             FROM compra c 
                             WHERE {period_func.replace('f.fecha_factura', 'c.fecha_compra')} = periodo) AS ganancia_neta
                        FROM factura f
                        JOIN detalle_factura df ON f.id_factura = df.id_factura
                        JOIN vista_detalle_factura_con_descuento vd ON df.id_detalle = vd.id_detalle
                        WHERE {period_func} IN ({','.join([f"'{p}'" for p in periods])})
                        GROUP BY {period_func}
                        ORDER BY periodo
                    """)
                    
                    data = self.cursor.fetchall()
                    
                    if not data:
                        self.show_no_data_message(self.tabs["temporal"]["graph_frame"])
                        return
                    
                    # Preparar datos
                    periods_data = [d['periodo'] for d in data]
                    ventas = [float(d['ventas_totales'] or 0) for d in data]
                    compras = [float(d['compras_totales'] or 0) for d in data]
                    ganancias = [float(d['ganancia_neta'] or 0) for d in data]
                    
                    # Crear gráfico
                    fig, ax = plt.subplots(figsize=(14, 8))
                    
                    x = np.arange(len(periods_data))
                    width = 0.35
                    
                    # Barras para ventas (positivas) y compras (negativas)
                    bars_ventas = ax.bar(x - width/2, ventas, width, label='Ingresos', color='#A5D6A7', alpha=0.8)
                    bars_compras = ax.bar(x + width/2, [-c for c in compras], width, label='Compras', color='#EF9A9A', alpha=0.8)
                    
                    # Línea de ganancia neta
                    line = ax.plot(x, ganancias, marker='o', color='#2196F3', linewidth=3, markersize=8, label='Ganancia Neta')
                    
                    # Etiquetas de montos en todas las barras
                    for i, (bar_v, bar_c, v, c, g) in enumerate(zip(bars_ventas, bars_compras, ventas, compras, ganancias)):
                        # Etiqueta de ventas
                        ax.text(bar_v.get_x() + bar_v.get_width()/2, bar_v.get_height() + max(ventas) * 0.02,
                               f'${v:,.0f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
                        
                        # Etiqueta de compras
                        ax.text(bar_c.get_x() + bar_c.get_width()/2, bar_c.get_height() - max(compras) * 0.02,
                               f'${c:,.0f}', ha='center', va='top', fontsize=9, fontweight='bold')
                        
                        # Etiqueta de ganancia neta
                        y_offset = max(ventas) * 0.05 if g >= 0 else -max(compras) * 0.05
                        ax.text(i, g + y_offset, f'${g:,.0f}', ha='center', 
                               va='bottom' if g >= 0 else 'top', fontsize=10, fontweight='bold', 
                               color='#2196F3')
                    
                    ax.set_xlabel(f'{period_type}', fontsize=12)
                    ax.set_ylabel('Monto ($)', fontsize=12)
                    ax.set_title(f'Análisis General por {period_type}\nVerde: Ingresos | Rojo: Compras | Azul: Ganancia Neta', 
                               fontsize=14, fontweight='bold')
                    ax.set_xticks(x)
                    ax.set_xticklabels(periods_data, rotation=45 if len(periods_data) > 5 else 0)
                    ax.legend(fontsize=11)
                    ax.grid(axis='y', alpha=0.3)
                    ax.axhline(y=0, color='black', linewidth=1, alpha=0.5)
                    
                    # Formatear ejes
                    formatter = FuncFormatter(lambda x, _: f"${x:,.0f}")
                    ax.yaxis.set_major_formatter(formatter)
                    
                    plt.tight_layout()
                    self.embed_plot(fig, self.tabs["temporal"]["graph_frame"])
                    
                except Exception as e:
                    self.show_error_message(self.tabs["temporal"]["graph_frame"], str(e))
            
            def generate_product_temporal_chart(self, period_type, periods):
                """Genera gráfico temporal por producto mostrando top 5 con separación de ganancias/pérdidas."""
                try:
                    # Mapeo de funciones de período
                    period_func_map = {
                        "Día": "DATE_FORMAT(f.fecha_factura, '%Y-%m-%d')",
                        "Semana": "DATE_FORMAT(f.fecha_factura, '%x-W%v')",
                        "Mes": "DATE_FORMAT(f.fecha_factura, '%Y-%m')",
                        "Trimestre": "CONCAT(YEAR(f.fecha_factura), '-Q', QUARTER(f.fecha_factura))",
                        "Año": "YEAR(f.fecha_factura)"
                    }
                    
                    period_func = period_func_map.get(period_type, "DATE_FORMAT(f.fecha_factura, '%Y-%m')")
                    periods_str = ','.join([f"'{p}'" for p in periods])
                    
                    # Obtener top productos por ganancia total en el período
                    self.cursor.execute(f"""
                        SELECT 
                            p.nombre_producto,
                            SUM(vd.subtotal_con_descuento) AS ingresos_totales
                        FROM producto p
                        JOIN detalle_factura df ON p.id_producto = df.id_producto
                        JOIN vista_detalle_factura_con_descuento vd ON df.id_detalle = vd.id_detalle
                        JOIN factura f ON df.id_factura = f.id_factura
                        WHERE {period_func} IN ({periods_str})
                        GROUP BY p.id_producto, p.nombre_producto
                        ORDER BY ingresos_totales DESC
                        LIMIT 5
                    """)
                    
                    top_products = [row['nombre_producto'] for row in self.cursor.fetchall()]
                    
                    if not top_products:
                        self.show_no_data_message(self.tabs["temporal"]["graph_frame"])
                        return
                    
                    # Obtener datos detallados por período para los top productos
                    products_in = ','.join([f"'{p}'" for p in top_products])
                    
                    self.cursor.execute(f"""
                        SELECT 
                            {period_func} AS periodo,
                            p.nombre_producto,
                            SUM(vd.subtotal_con_descuento) AS ingresos
                        FROM producto p
                        JOIN detalle_factura df ON p.id_producto = df.id_producto
                        JOIN vista_detalle_factura_con_descuento vd ON df.id_detalle = vd.id_detalle
                        JOIN factura f ON df.id_factura = f.id_factura
                        WHERE {period_func} IN ({periods_str})
                        AND p.nombre_producto IN ({products_in})
                        GROUP BY {period_func}, p.id_producto, p.nombre_producto
                        ORDER BY periodo, ingresos DESC
                    """)
                    
                    data = self.cursor.fetchall()
                    
                    if not data:
                        self.show_no_data_message(self.tabs["temporal"]["graph_frame"])
                        return
                    
                    # Organizar datos
                    period_data = defaultdict(dict)
                    for row in data:
                        period_data[str(row['periodo'])][row['nombre_producto']] = float(row['ingresos'] or 0)
                    
                    # Crear gráfico
                    fig, ax = plt.subplots(figsize=(14, 8))
                    
                    periods_sorted = sorted([str(p) for p in periods])
                    x = np.arange(len(periods_sorted))
                    width = 0.15
                    colors = ['#A5D6A7', '#90CAF9', '#FFE082', '#CE93D8', '#F48FB1']
                    
                    # Crear barras para cada producto
                    for i, product in enumerate(top_products):
                        product_short = product[:15] + '...' if len(product) > 15 else product
                        values = []
                        
                        for period in periods_sorted:
                            values.append(period_data.get(period, {}).get(product, 0))
                        
                        bars = ax.bar(x + i * width, values, width, 
                                    label=product_short, 
                                    color=colors[i % len(colors)], alpha=0.8)
                        
                        # Etiquetas de valores
                        for j, (bar, value) in enumerate(zip(bars, values)):
                            if value > 0:
                                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values) * 0.01,
                                    f'${value:,.0f}', ha='center', va='bottom', fontsize=8, rotation=90)
                    
                    ax.set_xlabel(f'{period_type}', fontsize=12)
                    ax.set_ylabel('Ingresos ($)', fontsize=12)
                    ax.set_title(f'Top 5 Productos por {period_type} - Ingresos', 
                            fontsize=14, fontweight='bold')
                    ax.set_xticks(x + width * 2)
                    ax.set_xticklabels(periods_sorted, rotation=45 if len(periods_sorted) > 3 else 0)
                    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
                    ax.grid(axis='y', alpha=0.3)
                    
                    # Formatear ejes
                    formatter = FuncFormatter(lambda x, _: f"${x:,.0f}")
                    ax.yaxis.set_major_formatter(formatter)
                    
                    plt.tight_layout()
                    self.embed_plot(fig, self.tabs["temporal"]["graph_frame"])
                    
                except Exception as e:
                    self.show_error_message(self.tabs["temporal"]["graph_frame"], str(e))
                    print(f"Error en generate_product_temporal_chart: {e}")
                    
            def generate_group_temporal_chart(self, period_type, periods):
                """Genera gráfico temporal por grupo de clientes con barras separadas."""
                try:
                    period_func_map = {
                        "Día": "DATE_FORMAT(f.fecha_factura, '%Y-%m-%d')",
                        "Semana": "DATE_FORMAT(f.fecha_factura, '%x-W%v')",
                        "Mes": "DATE_FORMAT(f.fecha_factura, '%Y-%m')",
                        "Trimestre": "CONCAT(YEAR(f.fecha_factura), '-Q', QUARTER(f.fecha_factura))",
                        "Año": "YEAR(f.fecha_factura)"
                    }
                    
                    period_func = period_func_map.get(period_type, "DATE_FORMAT(f.fecha_factura, '%Y-%m')")
                    periods_str = ','.join([f"'{p}'" for p in periods])
                    
                    self.cursor.execute(f"""
                        SELECT 
                            {period_func} AS periodo,
                            g.clave_grupo,
                            SUM(vd.subtotal_con_descuento) AS ventas_totales,
                            COUNT(DISTINCT c.id_cliente) AS clientes_activos,
                            COUNT(DISTINCT f.id_factura) AS facturas_emitidas
                        FROM grupo g
                        JOIN cliente c ON g.id_grupo = c.id_grupo
                        JOIN factura f ON c.id_cliente = f.id_cliente
                        JOIN detalle_factura df ON f.id_factura = df.id_factura
                        JOIN vista_detalle_factura_con_descuento vd ON df.id_detalle = vd.id_detalle
                        WHERE {period_func} IN ({periods_str})
                        GROUP BY {period_func}, g.id_grupo, g.clave_grupo
                        ORDER BY periodo, ventas_totales DESC
                    """)
                    
                    data = self.cursor.fetchall()
                    
                    if not data:
                        self.show_no_data_message(self.tabs["temporal"]["graph_frame"])
                        return
                    
                    # Organizar datos por grupo
                    groups = list(set(row['clave_grupo'] for row in data))
                    period_data = defaultdict(dict)
                    client_data = defaultdict(dict)
                    
                    for row in data:
                        period_str = str(row['periodo'])
                        period_data[period_str][row['clave_grupo']] = float(row['ventas_totales'] or 0)
                        client_data[period_str][row['clave_grupo']] = int(row['clientes_activos'] or 0)
                    
                    # Crear gráfico con barras separadas
                    fig, ax = plt.subplots(figsize=(14, 8))
                    
                    periods_sorted = sorted([str(p) for p in periods])
                    x = np.arange(len(periods_sorted))
                    width = 0.8 / max(len(groups), 1)  # Ancho de cada barra
                    colors = ['#A5D6A7', '#90CAF9', '#FFE082', '#CE93D8', '#F48FB1', '#FFAB91']
                    
                    # Crear barras separadas para cada grupo
                    for i, group in enumerate(groups):
                        values = []
                        clients = []
                        
                        for period in periods_sorted:
                            values.append(period_data.get(period, {}).get(group, 0))
                            clients.append(client_data.get(period, {}).get(group, 0))
                        
                        # Posición de las barras para cada grupo
                        x_pos = x + i * width - (len(groups) - 1) * width / 2
                        
                        bars = ax.bar(x_pos, values, width, 
                                    label=group, color=colors[i % len(colors)], alpha=0.8)
                        
                        # Etiquetas con monto y número de clientes
                        max_value = max(values) if values else 0
                        for j, (bar, value, client_count) in enumerate(zip(bars, values, clients)):
                            if value > 0:
                                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max_value * 0.01,
                                    f'${value:,.0f}\n({client_count}c)',
                                    ha='center', va='bottom', fontsize=8, fontweight='bold')
                    
                    ax.set_xlabel(f'{period_type}', fontsize=12)
                    ax.set_ylabel('Ventas ($)', fontsize=12)
                    ax.set_title(f'Ventas por Grupo de Clientes - {period_type}\nBarras separadas por grupo', 
                            fontsize=14, fontweight='bold')
                    ax.set_xticks(x)
                    ax.set_xticklabels(periods_sorted, rotation=45 if len(periods_sorted) > 3 else 0)
                    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                    ax.grid(axis='y', alpha=0.3)
                    
                    # Formatear ejes
                    formatter = FuncFormatter(lambda x, _: f"${x:,.0f}")
                    ax.yaxis.set_major_formatter(formatter)
                    
                    plt.tight_layout()
                    self.embed_plot(fig, self.tabs["temporal"]["graph_frame"])
                    
                except Exception as e:
                    self.show_error_message(self.tabs["temporal"]["graph_frame"], str(e))
                    print(f"Error en generate_group_temporal_chart: {e}")
                
            def generate_clients_chart(self):
                """Genera gráfico de ventas por cliente con colores según tipo de cliente."""
                try:
                    frame = self.tabs["clients"]["frame"]
                    
                    # Limpiar frame de controles si ya existe
                    for widget in frame.winfo_children():
                        widget.destroy()
                        
                    # Frame de controles
                    self.client_control_frame = ttk.Frame(frame)
                    self.client_control_frame.pack(fill="x", padx=10, pady=5)
                    
                    # Obtener lista de clientes usando vista
                    self.cursor.execute("""
                        SELECT 
                            c.id_cliente, 
                            c.nombre_cliente,
                            g.clave_grupo,
                            tc.nombre_tipo
                        FROM cliente c
                        JOIN grupo g ON c.id_grupo = g.id_grupo
                        JOIN tipo_cliente tc ON g.id_tipo_cliente = tc.id_tipo_cliente
                        ORDER BY c.nombre_cliente
                    """)
                    self.all_clients = self.cursor.fetchall()
                    
                    # Inicializar variables
                    self.selected_clients = []
                    self.client_vars = [tk.StringVar() for _ in range(5)]
                    
                    # Frame para etiqueta y combos
                    label_frame = ttk.Frame(self.client_control_frame)
                    label_frame.pack(side="left")
                    
                    ttk.Label(label_frame, text="Seleccionar clientes:").pack(side="top")
                    
                    combo_frame = ttk.Frame(self.client_control_frame)
                    combo_frame.pack(side="left", padx=10)
                    
                    # Crear combos
                    self.client_combos = []
                    for i in range(5):
                        combo = ttk.Combobox(
                            combo_frame,
                            textvariable=self.client_vars[i],
                            state="readonly",
                            width=25
                        )
                        combo.pack(side="left", padx=2)
                        combo.bind("<<ComboboxSelected>>", self.create_client_handler(i))
                        self.client_combos.append(combo)
                    
                    # Frame para botones
                    button_frame = ttk.Frame(self.client_control_frame)
                    button_frame.pack(side="left", padx=10)
                    
                    ttk.Button(button_frame, text="Top 5 Clientes", 
                            command=self.load_top_clients).pack(side="left", padx=2)
                    ttk.Button(button_frame, text="Limpiar Todo", 
                            command=self.clear_all_clients).pack(side="left", padx=2)
                    
                    # Frame del gráfico
                    self.tabs["clients"]["graph_frame"] = ttk.Frame(frame)
                    self.tabs["clients"]["graph_frame"].pack(fill="both", expand=True)
                    
                    # Cargar top 5 clientes por defecto
                    self.load_top_clients()
                    
                except Exception as e:
                    self.show_error_message(self.tabs["clients"]["container"], str(e))

            def create_client_handler(self, index):
                """Crea un manejador de eventos para un combo específico."""
                def handler(event):
                    self.on_client_combo_change(index)
                return handler

            def on_client_combo_change(self, combo_index):
                """Maneja el cambio en un combo de cliente."""
                try:
                    selected_value = self.client_vars[combo_index].get()
                    
                    # Asegurar que la lista tenga el tamaño correcto
                    while len(self.selected_clients) <= combo_index:
                        self.selected_clients.append(None)
                    
                    if selected_value == "Ninguno" or not selected_value:
                        # Limpiar solo esta posición específica
                        self.selected_clients[combo_index] = None
                    else:
                        # Buscar cliente por nombre
                        client_name = selected_value.split(' (')[0]
                        found_client = None
                        for client in self.all_clients:
                            if client['nombre_cliente'] == client_name:
                                found_client = client
                                break
                        
                        if found_client:
                            # Reemplazar cliente en esta posición específica
                            self.selected_clients[combo_index] = found_client
                    
                    # NO limpiar elementos None del final - mantener posiciones
                    
                    # Actualizar combos y gráfico
                    self.refresh_client_combos()
                    self.update_clients_chart()
                    
                except Exception as e:
                    print(f"Error en combo change: {e}")

            def refresh_client_combos(self):
                """Actualiza las opciones de todos los combos sin cambiar selecciones válidas."""
                try:
                    # Obtener IDs de clientes ya seleccionados
                    selected_ids = set()
                    for client in self.selected_clients:
                        if client:
                            selected_ids.add(client['id_cliente'])
                    
                    # Actualizar cada combo manteniendo las selecciones actuales
                    for i, combo in enumerate(self.client_combos):
                        current_selection = self.client_vars[i].get()
                        options = ["Ninguno"]
                        
                        # Agregar clientes disponibles
                        for client in self.all_clients:
                            # Incluir cliente si:
                            # 1. No está seleccionado en ningún otro combo, O
                            # 2. Está seleccionado en ESTE combo específicamente
                            include_client = (
                                client['id_cliente'] not in selected_ids or 
                                (i < len(self.selected_clients) and 
                                self.selected_clients[i] and 
                                self.selected_clients[i]['id_cliente'] == client['id_cliente'])
                            )
                            
                            if include_client:
                                client_text = f"{client['nombre_cliente']} ({client['clave_grupo']})"
                                options.append(client_text)
                        
                        # Actualizar opciones
                        combo['values'] = options
                        
                        # Mantener selección actual si es válida, sino limpiar
                        if current_selection not in options:
                            self.client_vars[i].set("Ninguno")
                            if i < len(self.selected_clients):
                                self.selected_clients[i] = None
                            
                except Exception as e:
                    print(f"Error refrescando combos: {e}")

            def load_top_clients(self):
                """Carga los top 5 clientes con más ventas."""
                try:
                    self.cursor.execute("""
                        SELECT 
                            c.id_cliente, 
                            c.nombre_cliente,
                            g.clave_grupo,
                            tc.nombre_tipo,
                            SUM(vd.subtotal_con_descuento) AS total_vendido
                        FROM cliente c
                        JOIN grupo g ON c.id_grupo = g.id_grupo
                        JOIN tipo_cliente tc ON g.id_tipo_cliente = tc.id_tipo_cliente
                        JOIN factura f ON c.id_cliente = f.id_cliente
                        JOIN detalle_factura df ON f.id_factura = df.id_factura
                        JOIN vista_detalle_factura_con_descuento vd ON df.id_detalle = vd.id_detalle
                        GROUP BY c.id_cliente, c.nombre_cliente, g.clave_grupo, tc.nombre_tipo
                        ORDER BY total_vendido DESC
                        LIMIT 5
                    """)
                    top_clients = self.cursor.fetchall()
                    
                    # Limpiar y actualizar
                    self.selected_clients = []
                    for i in range(5):
                        if i < len(top_clients):
                            self.selected_clients.append(top_clients[i])
                            client_text = f"{top_clients[i]['nombre_cliente']} ({top_clients[i]['clave_grupo']})"
                            self.client_vars[i].set(client_text)
                        else:
                            self.selected_clients.append(None)
                            self.client_vars[i].set("Ninguno")
                    
                    self.refresh_client_combos()
                    self.update_clients_chart()
                    
                except Exception as e:
                    print(f"Error cargando top clientes: {e}")

            def clear_all_clients(self):
                """Limpia todas las selecciones de clientes."""
                # Mantener la lista con 5 posiciones vacías
                self.selected_clients = [None] * 5
                for var in self.client_vars:
                    var.set("Ninguno")
                self.refresh_client_combos()
                self.update_clients_chart()

            def update_clients_chart(self):
                """Actualiza el gráfico de clientes manteniendo el orden de posiciones."""
                try:
                    # Limpiar frame
                    for widget in self.tabs["clients"]["graph_frame"].winfo_children():
                        widget.destroy()
                    
                    # Obtener clientes en orden de posición (manteniendo None para posiciones vacías)
                    clients_to_show = []
                    client_positions = []
                    
                    for i, client in enumerate(self.selected_clients):
                        if client is not None:
                            clients_to_show.append(client)
                            client_positions.append(i)
                    
                    if not clients_to_show:
                        label = ttk.Label(
                            self.tabs["clients"]["graph_frame"],
                            text="Seleccione al menos un cliente para mostrar el gráfico",
                            font=('Arial', 12, 'italic'),
                            foreground='gray'
                        )
                        label.pack(expand=True)
                        return
                    
                    # Obtener datos manteniendo el orden
                    client_ids = ','.join([str(c['id_cliente']) for c in clients_to_show])
                    
                    self.cursor.execute(f"""
                        SELECT 
                            c.id_cliente,
                            c.nombre_cliente,
                            g.clave_grupo,
                            tc.nombre_tipo,
                            tc.descuento,
                            SUM(vd.subtotal_con_descuento) AS total_vendido
                        FROM cliente c
                        JOIN grupo g ON c.id_grupo = g.id_grupo
                        JOIN tipo_cliente tc ON g.id_tipo_cliente = tc.id_tipo_cliente
                        JOIN factura f ON c.id_cliente = f.id_cliente
                        JOIN detalle_factura df ON f.id_factura = df.id_factura
                        JOIN vista_detalle_factura_con_descuento vd ON df.id_detalle = vd.id_detalle
                        WHERE c.id_cliente IN ({client_ids})
                        GROUP BY c.id_cliente, c.nombre_cliente, g.clave_grupo, tc.nombre_tipo, tc.descuento
                    """)
                    raw_data = self.cursor.fetchall()
                    
                    if not raw_data:
                        label = ttk.Label(
                            self.tabs["clients"]["graph_frame"],
                            text="No hay datos de ventas para los clientes seleccionados",
                            font=('Arial', 12, 'italic'),
                            foreground='orange'
                        )
                        label.pack(expand=True)
                        return
                    
                    # Crear diccionario para acceso rápido por ID
                    data_by_id = {d['id_cliente']: d for d in raw_data}
                    
                    # Ordenar datos según el orden de selección en los combos
                    ordered_data = []
                    ordered_positions = []
                    for i, client in enumerate(clients_to_show):
                        if client['id_cliente'] in data_by_id:
                            ordered_data.append(data_by_id[client['id_cliente']])
                            ordered_positions.append(client_positions[i])
                    
                    # Crear gráfico
                    fig, ax = plt.subplots(figsize=(12, 6))
                    
                    # Colores fijos por posición para mantener consistencia visual
                    position_colors = ['#A5D6A7', '#90CAF9', '#FFE082', '#CE93D8', '#F48FB1']
                    
                    names = []
                    amounts = []
                    bar_colors = []
                    
                    for i, (data, pos) in enumerate(zip(ordered_data, ordered_positions)):
                        names.append(f"Pos.{pos+1}: {data['nombre_cliente']}\n({data['clave_grupo']})")
                        amounts.append(float(data['total_vendido'] or 0))
                        bar_colors.append(position_colors[pos % len(position_colors)])
                    
                    bars = ax.bar(names, amounts, color=bar_colors, alpha=0.8)
                    
                    # Añadir etiquetas
                    max_amount = max(amounts) if amounts else 0
                    for i, (bar, amount, data) in enumerate(zip(bars, amounts, ordered_data)):
                        # Etiqueta de monto
                        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max_amount * 0.01,
                            f'${amount:,.0f}', ha='center', va='bottom', fontweight='bold', fontsize=10)
                        
                        # Etiqueta de descuento
                        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 0.5,
                            f'Desc: {data["descuento"]}%\n{data["nombre_tipo"]}', 
                            ha='center', va='center', fontsize=8,
                            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
                    
                    ax.set_title('Ventas por Cliente Seleccionado\n(Posiciones mantenidas por combo)', 
                            fontsize=14, fontweight='bold')
                    ax.set_ylabel('Total Vendido ($)', fontsize=12)
                    ax.grid(axis='y', alpha=0.3)
                    
                    # Formato
                    formatter = FuncFormatter(lambda x, _: f"${x:,.0f}")
                    ax.yaxis.set_major_formatter(formatter)
                    
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()
                    
                    self.embed_plot(fig, self.tabs["clients"]["graph_frame"])
                    
                except Exception as e:
                    print(f"Error actualizando gráfico clientes: {e}")
                    self.show_error_message(self.tabs["clients"]["graph_frame"], str(e))
                    
            def update_combo_options(self):
                """Actualiza las opciones de los combobox evitando duplicados."""
                try:
                    # Obtener clientes ya seleccionados
                    selected_ids = [c['id_cliente'] for c in self.selected_clients if c]
                    
                    for i, combo in enumerate(self.client_combos):
                        # Crear lista de opciones disponibles
                        available_options = []
                        
                        # Para el primer combo, no incluir "Ninguno"
                        if i > 0:
                            available_options.append("Ninguno")
                        
                        # Agregar clientes no seleccionados
                        for cliente in self.all_clients:
                            if cliente['id_cliente'] not in selected_ids or (i < len(self.selected_clients) and 
                                self.selected_clients[i] and cliente['id_cliente'] == self.selected_clients[i]['id_cliente']):
                                cliente_text = f"{cliente['nombre_cliente']} ({cliente['clave_grupo']})"
                                available_options.append(cliente_text)
                        
                        # Actualizar opciones del combo
                        combo['values'] = available_options
                        
                        # Mantener selección actual si es válida
                        current_value = self.client_vars[i].get()
                        if current_value not in available_options:
                            self.client_vars[i].set("Ninguno" if i > 0 else available_options[0] if available_options else "")
                            
                except Exception as e:
                    print(f"Error actualizando opciones: {e}")

            def update_client_selection(self, idx):
                """Actualiza la selección de clientes cuando se cambia un combobox."""
                try:
                    selected_name = self.client_vars[idx].get()
                    
                    # Extender la lista si es necesario
                    while len(self.selected_clients) <= idx:
                        self.selected_clients.append(None)
                    
                    # Si se selecciona "Ninguno", eliminar esa posición
                    if selected_name == "Ninguno":
                        self.selected_clients[idx] = None
                    else:
                        # Extraer nombre del cliente (antes del paréntesis)
                        nombre_cliente = selected_name.split(' (')[0]
                        
                        # Buscar el cliente seleccionado
                        cliente_encontrado = None
                        for cliente in self.all_clients:
                            if cliente['nombre_cliente'] == nombre_cliente:
                                cliente_encontrado = cliente
                                break
                        
                        if cliente_encontrado:
                            self.selected_clients[idx] = cliente_encontrado
                    
                    # Limpiar valores None del final de la lista
                    while self.selected_clients and self.selected_clients[-1] is None:
                        self.selected_clients.pop()
                    
                    # Actualizar opciones de combobox
                    self.update_combo_options()
                    
                    # Actualizar el gráfico automáticamente
                    self.update_clients_chart()
                    
                except Exception as e:
                    print(f"Error en update_client_selection: {e}")

            def generate_groups_chart(self):
                """Genera gráfico simplificado de ventas por grupo de clientes."""
                try:
                    # Usar vista vista_ganancias_por_grupo para datos simplificados
                    self.cursor.execute("""
                        SELECT 
                            g.clave_grupo,
                            tc.nombre_tipo,
                            tc.descuento,
                            COUNT(DISTINCT c.id_cliente) AS cantidad_clientes,
                            SUM(vd.subtotal_con_descuento) AS total_ventas,
                            COUNT(DISTINCT f.id_factura) AS cantidad_facturas
                        FROM grupo g
                        JOIN tipo_cliente tc ON g.id_tipo_cliente = tc.id_tipo_cliente
                        LEFT JOIN cliente c ON g.id_grupo = c.id_grupo
                        LEFT JOIN factura f ON c.id_cliente = f.id_cliente
                        LEFT JOIN detalle_factura df ON f.id_factura = df.id_factura
                        LEFT JOIN vista_detalle_factura_con_descuento vd ON df.id_detalle = vd.id_detalle
                        GROUP BY g.id_grupo, g.clave_grupo, tc.nombre_tipo, tc.descuento
                        HAVING total_ventas > 0
                        ORDER BY total_ventas DESC
                    """)
                    grupos = self.cursor.fetchall()
                    
                    if not grupos:
                        self.show_no_data_message(self.tabs["groups"]["container"])
                        return
                    
                    fig, ax = plt.subplots(figsize=(12, 8))
                    
                    # Colores diferenciados
                    colors = ['#A5D6A7', '#90CAF9', '#FFE082', '#CE93D8', '#80CBC4', '#F48FB1']
                    
                    # Preparar datos
                    group_names = [f"{g['clave_grupo']}\n({g['nombre_tipo']})" for g in grupos]
                    group_totals = [float(g['total_ventas'] or 0) for g in grupos]
                    group_clients = [int(g['cantidad_clientes'] or 0) for g in grupos]
                    group_invoices = [int(g['cantidad_facturas'] or 0) for g in grupos]
                    
                    # Gráfico de barras para los grupos
                    bars = ax.bar(group_names, group_totals, color=colors[:len(group_names)])
                    
                    # Añadir etiquetas informativas en la parte superior
                    for bar, total, clients, invoices, grupo in zip(bars, group_totals, group_clients, group_invoices, grupos):
                        height = bar.get_height()
                        descuento = float(grupo['descuento'] or 0)
                        
                        # Etiqueta principal con monto
                        ax.text(bar.get_x() + bar.get_width()/2., height + max(group_totals) * 0.01,
                               f"${total:,.0f}",
                               ha='center', va='bottom', fontsize=11, fontweight='bold')
                        
                        # Etiqueta secundaria con información del grupo
                        ax.text(bar.get_x() + bar.get_width()/2., height * 0.5,
                               f"{clients} clientes\n{invoices} facturas\nDesc: {descuento}%",
                               ha='center', va='center', fontsize=9, 
                               bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
                    
                    ax.set_title("Ventas Totales por Grupo de Clientes\nMonto total por grupo (simplificado)", 
                               fontsize=14, fontweight='bold')
                    ax.set_ylabel("Ventas Totales ($)", fontsize=12)
                    ax.grid(axis='y', alpha=0.3)
                    
                    # Formatear eje Y
                    formatter = FuncFormatter(lambda x, _: f"${x:,.0f}")
                    ax.yaxis.set_major_formatter(formatter)
                    
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()
                    self.embed_plot(fig, self.tabs["groups"]["container"])
                    
                except Exception as e:
                    self.show_error_message(self.tabs["groups"]["container"], str(e))
                    
            def embed_plot(self, fig, container):
                """Inserta un gráfico matplotlib en el frame especificado."""
                for widget in container.winfo_children():
                    widget.destroy()
                    
                try:
                    canvas = FigureCanvasTkAgg(fig, master=container)
                    canvas.draw()
                    canvas.get_tk_widget().pack(fill="both", expand=True)
                    
                    # Añadir barra de herramientas
                    toolbar = NavigationToolbar2Tk(canvas, container)
                    toolbar.update()
                    
                    # Guardar referencia para evitar garbage collection
                    if hasattr(self, 'current_figure'):
                        # Cerrar la figura anterior si existe
                        old_fig, old_canvas, old_toolbar = self.current_figure
                        plt.close(old_fig)
                    
                    self.current_figure = (fig, canvas, toolbar)
                    
                except Exception as e:
                    self.show_error_message(container, f"Error al mostrar gráfico: {str(e)}")
                    
            def show_no_data_message(self, container):
                """Muestra mensaje cuando no hay datos disponibles."""
                for widget in container.winfo_children():
                    widget.destroy()
                    
                label = ttk.Label(
                    container,
                    text="No hay datos disponibles para esta visualización",
                    font=('Arial', 10, 'italic'),
                    foreground='gray'
                )
                label.pack(expand=True)
                
            def show_error_message(self, container, error):
                """Muestra mensaje de error."""
                for widget in container.winfo_children():
                    widget.destroy()
                    
                label = ttk.Label(
                    container,
                    text=f"Error: {error}",
                    font=('Arial', 10),
                    foreground='red'
                )
                label.pack(expand=True)
                
            def cleanup(self):
                """Limpia recursos antes de cerrar la ventana."""
                try:
                    if hasattr(self, 'current_figure'):
                        fig, canvas, toolbar = self.current_figure
                        plt.close(fig)
                    
                    self.window.destroy()
                except Exception as e:
                    print(f"Error durante cleanup: {e}")
                    self.window.destroy()
        
        # Crear e iniciar la ventana de estadísticas
        StatsWindow(self.root, self.cursor, self.conn)
    
    def export_to_pdf(self):
        """Exporta las estadísticas del día a un archivo PDF usando las nuevas vistas."""
        try:
            # Crear la carpeta reportes si no existe
            reportes_dir = "reportes"
            if not os.path.exists(reportes_dir):
                os.makedirs(reportes_dir)

            # Obtener la fecha actual
            fecha_actual = datetime.now().strftime("%Y-%m-%d")
            
            # Crear el nombre del archivo PDF
            filename = os.path.join(reportes_dir, f"Reporte_Diario_{fecha_actual}.pdf")
            
            # Crear el documento PDF
            doc = SimpleDocTemplate(filename, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Título del reporte
            title = Paragraph(f"Reporte Diario - {fecha_actual}", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Obtener datos de ventas del día usando vista
            self.cursor.execute("""
                SELECT 
                    vd.nombre_producto,
                    vd.cantidad_factura as cantidad,
                    vd.unidad_producto as unidad,
                    vd.precio_registrado as precio_unitario_venta,
                    vd.subtotal_con_descuento as subtotal,
                    c.nombre_cliente,
                    vd.clave_grupo,
                    vd.porcentaje_descuento as descuento_aplicado,
                    f.fecha_factura
                FROM vista_detalle_factura_con_descuento vd
                JOIN factura f ON vd.id_factura = f.id_factura
                JOIN cliente c ON f.id_cliente = c.id_cliente
                WHERE DATE(f.fecha_factura) = CURDATE()
                ORDER BY f.id_factura
            """)
            ventas = self.cursor.fetchall()
            
            # Obtener datos de compras del día
            self.cursor.execute("""
                SELECT 
                    p.nombre_producto,
                    c.cantidad_compra as cantidad,
                    p.unidad_producto as unidad,
                    c.precio_unitario_compra,
                    (c.cantidad_compra * c.precio_unitario_compra) as subtotal
                FROM compra c
                JOIN producto p ON c.id_producto = p.id_producto
                WHERE DATE(c.fecha_compra) = CURDATE()
                ORDER BY c.id_compra
            """)
            compras = self.cursor.fetchall()
            
            # Calcular totales
            total_ventas = sum(float(v['subtotal'] or 0) for v in ventas)
            total_compras = sum(float(c['subtotal'] or 0) for c in compras)
            ganancia_neta = total_ventas - total_compras
            
            # Sección de Ventas
            story.append(Paragraph("Ventas del Día (con descuentos aplicados)", styles['Heading2']))
            
            if ventas:
                # Preparar datos para la tabla de ventas
                ventas_data = [["Producto", "Cantidad", "Unidad", "Precio/U", "Descuento", "Subtotal", "Cliente", "Grupo"]]
                for v in ventas:
                    ventas_data.append([
                        v['nombre_producto'],
                        f"{float(v['cantidad'] or 0):.2f}",
                        v['unidad'],
                        f"${float(v['precio_unitario_venta'] or 0):.2f}",
                        f"{float(v['descuento_aplicado'] or 0)}%",
                        f"${float(v['subtotal'] or 0):.2f}",
                        v['nombre_cliente'],
                        v['clave_grupo'] or "Sin grupo"
                    ])
                
                # Crear tabla de ventas
                ventas_table = Table(ventas_data)
                ventas_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(ventas_table)
                story.append(Spacer(1, 12))
                
                # Total ventas
                story.append(Paragraph(f"Total Ventas (con descuentos): ${total_ventas:.2f}", styles['Heading3']))
                story.append(Spacer(1, 12))
            else:
                story.append(Paragraph("No hubo ventas hoy.", styles['Normal']))
                story.append(Spacer(1, 12))
            
            # Sección de Compras
            story.append(Paragraph("Compras del Día", styles['Heading2']))
            
            if compras:
                # Preparar datos para la tabla de compras
                compras_data = [["Producto", "Cantidad", "Unidad", "Precio/U", "Subtotal"]]
                for c in compras:
                    compras_data.append([
                        c['nombre_producto'],
                        f"{float(c['cantidad'] or 0):.2f}",
                        c['unidad'],
                        f"${float(c['precio_unitario_compra'] or 0):.2f}",
                        f"${float(c['subtotal'] or 0):.2f}"
                    ])
                
                # Crear tabla de compras
                compras_table = Table(compras_data)
                compras_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(compras_table)
                story.append(Spacer(1, 12))
                
                # Total compras
                story.append(Paragraph(f"Total Compras: ${total_compras:.2f}", styles['Heading3']))
                story.append(Spacer(1, 12))
            else:
                story.append(Paragraph("No hubo compras hoy.", styles['Normal']))
                story.append(Spacer(1, 12))
            
            # Sección de Ganancias Netas
            story.append(Paragraph("Resumen Financiero", styles['Heading2']))
            story.append(Paragraph(f"Total Ventas (con descuentos): ${total_ventas:.2f}", styles['Normal']))
            story.append(Paragraph(f"Total Compras: ${total_compras:.2f}", styles['Normal']))
            
            ganancia_style = styles['Heading3'] if ganancia_neta >= 0 else styles['Normal']
            story.append(Paragraph(f"Ganancia Neta: ${ganancia_neta:.2f}", ganancia_style))
            
            # Generar el PDF
            doc.build(story)
            messagebox.showinfo("Éxito", f"Reporte generado exitosamente en: {filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el PDF:\n{str(e)}")
            
    def on_closing(self):
        """Clean up and close connection when closing the app"""
        try:
            if hasattr(self, 'conn'):
                self.conn.close()
        except:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    user_data = {
        'nombre_completo': 'Usuario Prueba',
        'rol': 'usuario'  # Cambiar a 'admin' para probar funciones administrativas
    }
    app = AnalisisGananciasApp(root, user_data)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()