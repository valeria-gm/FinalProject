#!/usr/bin/env python3
"""
Module Launcher Script
Properly launches business modules with correct Python path and imports
Updated to use consolidated receipt module architecture
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def launch_receipts_module(user_data=None):
    """Launch the receipts module with VentanaOrdenes as the main hub"""
    try:
        # Change to project root directory
        os.chdir(project_root)
        
        # Import required modules
        from src.modules.receipts.components.ventana_ordenes import abrir_ventana_ordenes
        from src.modules.receipts.receipt_generator_refactored import ReciboAppMejorado
        print("✅ Using VentanaOrdenes as main hub with ReciboAppMejorado integration")
        
        # Default user data if none provided
        if user_data is None:
            user_data = {
                'nombre_completo': 'Usuario de Prueba',
                'rol': 'admin',
                'username': 'test'
            }
        
        # Keep track of editor instances for proper window management
        editor_instances = []
        ventana_ordenes = None  # Reference to main orders window
        
        def callback_nueva_orden():
            """Callback to create a new order - opens ReciboAppMejorado without folio"""
            try:
                # Create new editor window as Toplevel (allows multiple editors)
                editor_root = tk.Toplevel()
                editor_root.title("Disfruleg - Nueva Orden")
                editor_root.geometry("1100x750")
                
                # Function to handle window closing and refresh
                def on_editor_close():
                    editor_root.destroy()
                    # Force refresh of orders window after a short delay
                    if ventana_ordenes:
                        editor_root.after(100, ventana_ordenes.forzar_actualizacion)
                
                # Create editor app instance
                editor_app = ReciboAppMejorado(editor_root, user_data, orden_folio=None)
                editor_instances.append(editor_app)
                
                # Configure window properties
                editor_root.transient()  # Stay on top of main window
                editor_root.focus_set()  # Give focus to new window
                editor_root.protocol("WM_DELETE_WINDOW", on_editor_close)
                
                # Bind event for order changes
                def on_orden_cambiada(event):
                    if ventana_ordenes:
                        ventana_ordenes.forzar_actualizacion()
                        print("📨 Evento OrdenCambiada recibido - actualizando lista")
                
                editor_root.bind("<<OrdenCambiada>>", on_orden_cambiada)
                
                print(f"✅ Nueva orden creada - Editor instancia #{len(editor_instances)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al crear nueva orden: {str(e)}")
                print(f"Error creating new order: {e}")
        
        def callback_editar_orden(folio):
            """Callback to edit existing order - opens ReciboAppMejorado with specific folio"""
            try:
                # Create editor window for specific order
                editor_root = tk.Toplevel()
                editor_root.title(f"Disfruleg - Editando Orden {folio:06d}")
                editor_root.geometry("1100x750")
                
                # Function to handle window closing and refresh
                def on_editor_close():
                    editor_root.destroy()
                    # Force refresh of orders window after a short delay
                    if ventana_ordenes:
                        root.after(100, ventana_ordenes.forzar_actualizacion)
                
                # Create editor app instance
                editor_app = ReciboAppMejorado(editor_root, user_data, orden_folio=folio)
                editor_instances.append(editor_app)
                
                # Configure window properties
                editor_root.transient()  # Stay on top of main window
                editor_root.focus_set()  # Give focus to new window
                editor_root.protocol("WM_DELETE_WINDOW", on_editor_close)
                
                # Bind event for order changes
                def on_orden_cambiada(event):
                    if ventana_ordenes:
                        ventana_ordenes.forzar_actualizacion()
                        print("📨 Evento OrdenCambiada recibido - actualizando lista")
                
                editor_root.bind("<<OrdenCambiada>>", on_orden_cambiada)
                
                print(f"✅ Editando orden {folio:06d} - Editor instancia #{len(editor_instances)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al editar orden {folio}: {str(e)}")
                print(f"Error editing order {folio}: {e}")
        
        # Create root window first to avoid tkinter initialization issues
        root = tk.Tk()
        root.withdraw()  # Hide the root window since VentanaOrdenes will be the main interface
        
        # Launch VentanaOrdenes as the main hub
        ventana_ordenes = abrir_ventana_ordenes(
            parent=None,  # Main window, not child
            user_data=user_data,
            on_nueva_orden=callback_nueva_orden,
            on_editar_orden=callback_editar_orden
        )
        
        # Start the main event loop
        ventana_ordenes.show()
        
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar el módulo de recibos: {str(e)}")
        print(f"Error launching receipts module: {e}")
        import traceback
        traceback.print_exc()


def launch_pricing_module(user_data=None):
    """Launch the price editor module"""
    try:
        os.chdir(project_root)
        from src.modules.pricing.price_editor import PriceEditorApp
        
        root = tk.Tk()
        
        if user_data is None:
            user_data = {
                'nombre_completo': 'Usuario de Prueba',
                'rol': 'admin',
                'username': 'test'
            }
        
        app = PriceEditorApp(root, user_data)
        root.mainloop()
        
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar el editor de precios: {str(e)}")
        print(f"Error launching pricing module: {e}")

def launch_inventory_module(user_data=None):
    """Launch the inventory/purchases module"""
    try:
        os.chdir(project_root)
        from src.modules.inventory.registro_compras import ComprasApp
        
        root = tk.Tk()
        
        if user_data is None:
            user_data = {
                'nombre_completo': 'Usuario de Prueba',
                'rol': 'admin',
                'username': 'test'
            }
        
        app = ComprasApp(root, user_data)
        root.mainloop()
        
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar el registro de compras: {str(e)}")
        print(f"Error launching inventory module: {e}")

def launch_analytics_module(user_data=None):
    """Launch the analytics module"""
    try:
        os.chdir(project_root)
        from src.modules.analytics.analizador_ganancias import AnalisisGananciasApp
        
        root = tk.Tk()
        
        if user_data is None:
            user_data = {
                'nombre_completo': 'Usuario de Prueba',
                'rol': 'admin',
                'username': 'test'
            }
        
        app = AnalisisGananciasApp(root, user_data)
        root.mainloop()
        
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar el analizador de ganancias: {str(e)}")
        print(f"Error launching analytics module: {e}")

def launch_clients_module(user_data=None):
    """Launch the client management module"""
    try:
        os.chdir(project_root)
        from src.modules.clients.client_manager import ClientManagerApp
        
        root = tk.Tk()
        
        if user_data is None:
            user_data = {
                'nombre_completo': 'Usuario de Prueba',
                'rol': 'admin',
                'username': 'test'
            }
        
        app = ClientManagerApp(root)
        root.mainloop()
        
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar el administrador de clientes: {str(e)}")
        print(f"Error launching clients module: {e}")

def launch_users_module(user_data=None):
    """Launch the user management module"""
    try:
        os.chdir(project_root)
        from src.modules.users.user_manager import UserManagerApp
        
        root = tk.Tk()
        
        if user_data is None:
            user_data = {
                'nombre_completo': 'Usuario de Prueba',
                'rol': 'admin',
                'username': 'test'
            }
        
        app = UserManagerApp(root, user_data)
        root.mainloop()
        
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar el administrador de usuarios: {str(e)}")
        print(f"Error launching users module: {e}")
        import traceback
        traceback.print_exc()

def launch_debts_module(user_data=None):
    """Launch the debt management module"""
    try:
        os.chdir(project_root)
        from src.modules.deudas.debt_window import launch_debt_window
        
        if user_data is None:
            user_data = {
                'nombre_completo': 'Usuario de Prueba',
                'rol': 'admin',
                'username': 'test'
            }
        
        launch_debt_window(user_data)
        
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar el módulo de deudas: {str(e)}")
        print(f"Error launching debts module: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main entry point when script is run directly"""
    if len(sys.argv) < 2:
        print("Usage: python launch_module.py <module_name>")
        print("Available modules: receipts, pricing, inventory, analytics, clients, users, debts")
        sys.exit(1)
    
    module_name = sys.argv[1].lower()
    
    # Get user data from command line if provided (as JSON string)
    user_data = None
    if len(sys.argv) > 2:
        import json
        try:
            user_data = json.loads(sys.argv[2])
        except:
            print("Warning: Invalid user data JSON, using default")
    
    # Launch the appropriate module
    if module_name == "receipts":
        launch_receipts_module(user_data)
    elif module_name == "pricing":
        launch_pricing_module(user_data)
    elif module_name == "inventory":
        launch_inventory_module(user_data)
    elif module_name == "analytics":
        launch_analytics_module(user_data)
    elif module_name == "clients":
        launch_clients_module(user_data)
    elif module_name == "users":
        launch_users_module(user_data)
    elif module_name == "debts":
        launch_debts_module(user_data)
    else:
        print(f"Unknown module: {module_name}")
        print("Available modules: receipts, pricing, inventory, analytics, clients, users, debts")
        sys.exit(1)

if __name__ == "__main__":
    main()