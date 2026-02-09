import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta

def agregar_calendario_popup(parent_widget, fecha_var):
    """Función para agregar un calendario popup (opcional)"""
    try:
        def mostrar_calendario():
            cal_window = tk.Toplevel()
            cal_window.title("Seleccionar Fecha")
            cal_window.geometry("250x200")
            cal_window.transient(parent_widget.winfo_toplevel())
            cal_window.grab_set()
            
            # Frame para año y mes
            frame_nav = ttk.Frame(cal_window)
            frame_nav.pack(pady=5)
            
            # Variables para año y mes
            año_actual = datetime.now().year
            mes_actual = datetime.now().month
            
            año_var = tk.IntVar(value=año_actual)
            mes_var = tk.IntVar(value=mes_actual)
            
            # Spinbox para año
            ttk.Label(frame_nav, text="Año:").grid(row=0, column=0, padx=5)
            spin_año = tk.Spinbox(frame_nav, from_=2020, to=2030, 
                                 textvariable=año_var, width=6)
            spin_año.grid(row=0, column=1, padx=5)
            
            # Combobox para mes
            ttk.Label(frame_nav, text="Mes:").grid(row=0, column=2, padx=5)
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            combo_mes = ttk.Combobox(frame_nav, values=meses, state="readonly", width=10)
            combo_mes.set(meses[mes_actual-1])
            combo_mes.grid(row=0, column=3, padx=5)
            
            # Botón para cerrar
            ttk.Button(frame_nav, text="Cerrar", 
                      command=cal_window.destroy).grid(row=0, column=4, padx=10)
            
            # Ejemplo básico - en una implementación real usarías tkcalendar
            label_info = ttk.Label(cal_window, 
                                  text="Use formato YYYY-MM-DD\nEjemplo: 2024-12-25")
            label_info.pack(pady=20)
        
        # Botón para abrir calendario
        btn_calendario = ttk.Button(parent_widget, text="📅", width=3,
                                   command=mostrar_calendario)
        return btn_calendario
        
    except ImportError:
        return None