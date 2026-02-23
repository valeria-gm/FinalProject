"""
Debt Management Window
Ventana principal del módulo de gestión de deudas
"""

import tkinter as tk
from tkinter import messagebox, ttk
from src.modules.deudas.debt_manager import obtener_debt_manager
from src.config import debug_print
from decimal import Decimal
import decimal

class DebtManagementWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Debt Management - Market")
        self.root.geometry("1000x700")
        
        # Initialize debt manager
        self.debt_manager = obtener_debt_manager()
        
        # Variables
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_debts)
        self.search_history_var = tk.StringVar()
        self.search_history_var.trace("w", self.filter_payment_history)
        self.clientes_deudas = []
        self.historial_pagos = []
        
        self.create_interface()
        self.load_data()
    
    def create_interface(self):
        """Create the user interface"""
        # Title
        title_frame = tk.Frame(self.root)
        title_frame.pack(fill="x", pady=10)

        tk.Label(title_frame, text="DEBT MANAGEMENT", font=("Arial", 18, "bold")).pack()

        # Statistics frame
        self.create_statistics_frame()

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # Create tabs
        self.create_pending_debts_tab()
        self.create_payment_history_tab()

        # Status bar
        self.status_var = tk.StringVar(value="Listo")
        status_bar = tk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_statistics_frame(self):
        """Create statistics display frame"""
        stats_frame = tk.Frame(self.root, relief=tk.RAISED, bd=1)
        stats_frame.pack(fill="x", padx=10, pady=5)
        
        # Statistics variables
        self.stats_vars = {
            'total_clientes': tk.StringVar(value="0"),
            'clientes_con_deuda': tk.StringVar(value="0"),
            'total_saldo_pendiente': tk.StringVar(value="$0.00"),
            'total_deudas_pendientes': tk.StringVar(value="0")
        }
        
        # Create statistics layout
        stats_grid = tk.Frame(stats_frame)
        stats_grid.pack(pady=10)
        
        # Row 1
        tk.Label(stats_grid, text="Total Clients:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=10)
        tk.Label(stats_grid, textvariable=self.stats_vars['total_clientes'], 
                font=("Arial", 10)).grid(row=0, column=1, sticky="w", padx=10)
        
        tk.Label(stats_grid, text="With Debt:", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky="w", padx=10)
        tk.Label(stats_grid, textvariable=self.stats_vars['clientes_con_deuda'], 
                font=("Arial", 10)).grid(row=0, column=3, sticky="w", padx=10)
        
        # Row 2
        tk.Label(stats_grid, text="Total Pending Balance:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        tk.Label(stats_grid, textvariable=self.stats_vars['total_saldo_pendiente'], 
                font=("Arial", 10, "bold"), fg="red").grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        tk.Label(stats_grid, text="Pending Debts:", font=("Arial", 10, "bold")).grid(row=1, column=2, sticky="w", padx=10, pady=5)
        tk.Label(stats_grid, textvariable=self.stats_vars['total_deudas_pendientes'], 
                font=("Arial", 10)).grid(row=1, column=3, sticky="w", padx=10, pady=5)
    
    def create_pending_debts_tab(self):
        """Create the pending debts tab"""
        # Create tab frame
        pending_frame = ttk.Frame(self.notebook)
        self.notebook.add(pending_frame, text="Pending Debts")

        # Search and actions frame for pending debts
        action_frame = tk.Frame(pending_frame)
        action_frame.pack(fill="x", pady=5, padx=10)

        # Search section
        search_frame = tk.Frame(action_frame)
        search_frame.pack(side="left", fill="x", expand=True)

        tk.Label(search_frame, text="Search Client:", font=("Arial", 12)).pack(side="left", padx=5)
        self.search_entry = tk.Entry(search_frame, width=30, textvariable=self.search_var)
        self.search_entry.pack(side="left", padx=5)

        # Buttons section
        buttons_frame = tk.Frame(action_frame)
        buttons_frame.pack(side="right")

        tk.Button(buttons_frame, text="Refresh", command=self.load_data,
                  bg="#2196F3", fg="white", padx=10, pady=3).pack(side="left", padx=5)
        tk.Button(buttons_frame, text="View Details", command=self.view_client_details,
                  bg="#4CAF50", fg="white", padx=10, pady=3).pack(side="left", padx=5)

        # Main treeview frame for pending debts
        tree_frame = tk.Frame(pending_frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Create treeview with scrollbar for pending debts
        self.create_pending_debts_treeview(tree_frame)

    def create_pending_debts_treeview(self, parent):
        """Create the main treeview for clients with debts"""
        # Create treeview
        self.tree = ttk.Treeview(parent, columns=("cliente", "grupo", "tipo", "saldo", "deudas", "ultima_deuda"), show="headings")

        # Configure columns
        self.tree.heading("cliente", text="Client")
        self.tree.heading("grupo", text="Group")
        self.tree.heading("tipo", text="Client Type")
        self.tree.heading("saldo", text="Outstanding Balance")
        self.tree.heading("deudas", text="Pending Debts")
        self.tree.heading("ultima_deuda", text="Last Debt")

        # Set column widths
        self.tree.column("cliente", width=250)
        self.tree.column("grupo", width=80)
        self.tree.column("tipo", width=120)
        self.tree.column("saldo", width=120)
        self.tree.column("deudas", width=100)
        self.tree.column("ultima_deuda", width=100)

        # Create scrollbar
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Pack treeview and scrollbar
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind double-click event
        self.tree.bind("<Double-1>", self.on_double_click)

    def create_payment_history_tab(self):
        """Create the payment history tab"""
        # Create tab frame
        history_frame = ttk.Frame(self.notebook)
        self.notebook.add(history_frame, text="Payment History")

        # Search and actions frame for payment history
        history_action_frame = tk.Frame(history_frame)
        history_action_frame.pack(fill="x", pady=5, padx=10)

        # Search section for history
        history_search_frame = tk.Frame(history_action_frame)
        history_search_frame.pack(side="left", fill="x", expand=True)

        tk.Label(history_search_frame, text="Search Client:", font=("Arial", 12)).pack(side="left", padx=5)
        self.search_history_entry = tk.Entry(history_search_frame, width=30, textvariable=self.search_history_var)
        self.search_history_entry.pack(side="left", padx=5)

        # Buttons section for history
        history_buttons_frame = tk.Frame(history_action_frame)
        history_buttons_frame.pack(side="right")

        tk.Button(history_buttons_frame, text="Refresh History", command=self.load_payment_history,
                  bg="#2196F3", fg="white", padx=10, pady=3).pack(side="left", padx=5)

        # Main treeview frame for payment history
        history_tree_frame = tk.Frame(history_frame)
        history_tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Create treeview for payment history
        self.create_payment_history_treeview(history_tree_frame)

    def create_payment_history_treeview(self, parent):
        """Create the treeview for payment history"""
        # Create treeview for payment history
        self.history_tree = ttk.Treeview(parent,
                                       columns=("cliente", "grupo", "folio", "monto_total", "monto_pagado",
                                               "fecha_pago", "metodo_pago", "referencia"),
                                       show="headings")

        # Configure columns
        self.history_tree.heading("cliente", text="Client")
        self.history_tree.heading("grupo", text="Group")
        self.history_tree.heading("folio", text="Receipt #")
        self.history_tree.heading("monto_total", text="Total Amount")
        self.history_tree.heading("monto_pagado", text="Amount Paid")
        self.history_tree.heading("fecha_pago", text="Payment Date")
        self.history_tree.heading("metodo_pago", text="Payment Method")
        self.history_tree.heading("referencia", text="Reference")

        # Set column widths
        self.history_tree.column("cliente", width=200)
        self.history_tree.column("grupo", width=80)
        self.history_tree.column("folio", width=90)
        self.history_tree.column("monto_total", width=110)
        self.history_tree.column("monto_pagado", width=110)
        self.history_tree.column("fecha_pago", width=110)
        self.history_tree.column("metodo_pago", width=130)
        self.history_tree.column("referencia", width=120)

        # Create scrollbar for history tree
        history_scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scrollbar.set)

        # Pack treeview and scrollbar
        self.history_tree.pack(side="left", fill="both", expand=True)
        history_scrollbar.pack(side="right", fill="y")
    
    def load_data(self):
        """Load all data: statistics, clients with debts, and payment history"""
        self.status_var.set("Cargando datos...")
        try:
            # Load statistics
            self.load_statistics()

            # Load clients with debts
            self.load_clients_with_debts()

            # Load payment history
            self.load_payment_history()

            self.status_var.set(f"Data loaded - {len(self.clientes_deudas)} clients with debt, {len(self.historial_pagos)} recorded payments")
            debug_print("Debt data loaded successfully")

        except Exception as e:
            self.status_var.set("Error loading data")
            messagebox.showerror("Error", f"Error loading data: {e}")
            debug_print(f"Error loading debt data: {e}")
    
    def load_statistics(self):
        """Load and display debt statistics"""
        try:
            stats = self.debt_manager.obtener_estadisticas_deudas()
            
            self.stats_vars['total_clientes'].set(str(stats.get('total_clientes', 0)))
            self.stats_vars['clientes_con_deuda'].set(str(stats.get('clientes_con_deuda', 0)))
            self.stats_vars['total_saldo_pendiente'].set(f"${stats.get('total_saldo_pendiente', 0):,.2f}")
            self.stats_vars['total_deudas_pendientes'].set(str(stats.get('total_deudas_pendientes', 0)))
            
        except Exception as e:
            debug_print(f"Error loading statistics: {e}")
    
    def load_clients_with_debts(self):
        """Load clients that have pending debts"""
        try:
            self.clientes_deudas = self.debt_manager.obtener_clientes_con_deudas()
            self.update_treeview()
            
        except Exception as e:
            debug_print(f"Error loading clients with debts: {e}")
            raise
    
    def update_treeview(self):
        """Update the treeview with current data"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Filter clients based on search term
        search_term = self.search_var.get().lower()
        
        for cliente in self.clientes_deudas:
            if not search_term or search_term in cliente['nombre_cliente'].lower():
                # Insert client data
                self.tree.insert("", "end", values=(
                    cliente['nombre_cliente'],
                    cliente['clave_grupo'],
                    cliente['tipo_cliente'],
                    f"${cliente['saldo_pendiente']:,.2f}",
                    cliente['deudas_pendientes'],
                    cliente['ultima_deuda_generada'] or "N/A"
                ), tags=(cliente['id_cliente'],))
    
    def load_payment_history(self):
        """Load payment history data"""
        try:
            self.historial_pagos = self.debt_manager.obtener_historial_pagos()
            self.update_payment_history_treeview()
            debug_print(f"Loading payment history: {len(self.historial_pagos)} records")
        except Exception as e:
            debug_print(f"Error loading payment history: {e}")
            messagebox.showerror("Error", f"Error loading payment history: {e}")

    def update_payment_history_treeview(self):
        """Update the payment history treeview with current data"""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        # Filter payments based on search term
        search_term = self.search_history_var.get().lower()

        for pago in self.historial_pagos:
            if not search_term or search_term in pago['nombre_cliente'].lower():
                # Insert payment data
                self.history_tree.insert("", "end", values=(
                    pago['nombre_cliente'],
                    pago['clave_grupo'],
                    pago['folio_numero'],
                    f"${pago['monto_total']:,.2f}",
                    f"${pago['monto_pagado']:,.2f}",
                    pago['fecha_pago'] or "N/A",
                    pago['metodo_pago'] or "N/A",
                    pago['referencia_pago'] or "N/A"
                ), tags=(pago['id_deuda'],))

    def filter_debts(self, *args):
        """Filter debts based on search term"""
        self.update_treeview()

    def filter_payment_history(self, *args):
        """Filter payment history based on search term"""
        self.update_payment_history_treeview()

    
    def on_double_click(self, event):
        """Handle double-click on treeview item"""
        self.view_client_details()
    
    def view_client_details(self):
        """Open client details window for selected client"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a client to view details")
            return
        
        # Get client ID from the selected item
        item = self.tree.item(selection[0])
        id_cliente = item['tags'][0]
        
        # Open client details window
        self.open_client_details_window(id_cliente)
    
    def open_client_details_window(self, id_cliente):
        """Open a window showing detailed debt information for a client"""
        details_window = tk.Toplevel(self.root)
        details_window.title("Client Debt Details")
        details_window.geometry("900x600")
        details_window.transient(self.root)
        details_window.grab_set()
        
        try:
            # Load client debts
            deudas = self.debt_manager.obtener_deudas_cliente(id_cliente)
            
            if not deudas:
                tk.Label(details_window, text="No debts found for this client", 
                        font=("Arial", 12)).pack(pady=50)
                return
            
            # Client information header
            cliente_info = deudas[0]  # First record contains client info
            header_frame = tk.Frame(details_window, relief=tk.RAISED, bd=1)
            header_frame.pack(fill="x", padx=10, pady=5)
            
            tk.Label(header_frame, text=f"CLIENT: {cliente_info['nombre_cliente']}", 
                    font=("Arial", 14, "bold")).pack(pady=5)
            tk.Label(header_frame, text=f"Group: {cliente_info['clave_grupo']} - {cliente_info['tipo_cliente']}", 
                    font=("Arial", 10)).pack()
            
            # Debts treeview
            tree_frame = tk.Frame(details_window)
            tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
            
            # Create debts treeview
            debts_tree = ttk.Treeview(tree_frame, 
                                     columns=("factura", "fecha_factura", "fecha_deuda", "monto_total", "monto_pagado", "saldo", "estado"), 
                                     show="headings")
            
            # Configure columns
            debts_tree.heading("factura", text="Invoice")
            debts_tree.heading("fecha_factura", text="Invoice Date")
            debts_tree.heading("fecha_deuda", text="Debt Date")
            debts_tree.heading("monto_total", text="Total Amount")
            debts_tree.heading("monto_pagado", text="Paid")
            debts_tree.heading("saldo", text="Balance")
            debts_tree.heading("estado", text="Status")
            
            # Set column widths
            debts_tree.column("factura", width=80)
            debts_tree.column("fecha_factura", width=100)
            debts_tree.column("fecha_deuda", width=100)
            debts_tree.column("monto_total", width=100)
            debts_tree.column("monto_pagado", width=100)
            debts_tree.column("saldo", width=100)
            debts_tree.column("estado", width=120)
            
            # Add scrollbar for debts tree
            debts_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=debts_tree.yview)
            debts_tree.configure(yscrollcommand=debts_scrollbar.set)
            
            # Pack debts treeview and scrollbar
            debts_tree.pack(side="left", fill="both", expand=True)
            debts_scrollbar.pack(side="right", fill="y")
            
            # Populate debts treeview
            for deuda in deudas:
                debts_tree.insert("", "end", values=(
                    deuda['id_factura'],
                    deuda['fecha_factura'],
                    deuda['fecha_generada'],
                    f"${deuda['monto_total']:,.2f}",
                    f"${deuda['monto_pagado']:,.2f}",
                    f"${deuda['saldo_pendiente']:,.2f}",
                    deuda['estado_deuda']
                ), tags=(deuda['id_deuda'],))
            
            # Buttons frame
            buttons_frame = tk.Frame(details_window)
            buttons_frame.pack(fill="x", padx=10, pady=10)
            
            def registrar_pago():
                selection = debts_tree.selection()
                if not selection:
                    messagebox.showwarning("Warning", "Select a debt to register payment")
                    return
                
                id_deuda = debts_tree.item(selection[0])['tags'][0]
                self.open_payment_window(id_deuda, details_window)
            
            tk.Button(buttons_frame, text="Register Payment", command=registrar_pago, 
                     bg="#4CAF50", fg="white", padx=15, pady=5).pack(side="left", padx=5)
            tk.Button(buttons_frame, text="Refresh", command=lambda: self.refresh_client_details(details_window, id_cliente), 
                     bg="#2196F3", fg="white", padx=15, pady=5).pack(side="left", padx=5)
            tk.Button(buttons_frame, text="Close", command=details_window.destroy, 
                     bg="#f44336", fg="white", padx=15, pady=5).pack(side="right", padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading client details: {e}")
            details_window.destroy()
    
    def refresh_client_details(self, details_window, id_cliente):
        """Refresh client details window"""
        details_window.destroy()
        self.open_client_details_window(id_cliente)
    
    def open_payment_window(self, id_deuda, parent_window):
        """Open payment registration window"""
        payment_window = tk.Toplevel(parent_window)
        payment_window.title("Register Payment")
        payment_window.geometry("550x500")
        payment_window.transient(parent_window)
        payment_window.grab_set()
        
        try:
            # Load debt information
            deuda = self.debt_manager.obtener_deuda_por_id(id_deuda)
            
            if not deuda:
                messagebox.showerror("Error", "Debt not found")
                payment_window.destroy()
                return
            
            # Debt information frame
            info_frame = tk.Frame(payment_window, relief=tk.RAISED, bd=1)
            info_frame.pack(fill="x", padx=10, pady=5)
            
            tk.Label(info_frame, text="DEBT INFORMATION", font=("Arial", 12, "bold")).pack(pady=5)
            tk.Label(info_frame, text=f"Client: {deuda['nombre_cliente']}").pack(anchor="w", padx=10)
            tk.Label(info_frame, text=f"Invoice number: {deuda['id_factura']}").pack(anchor="w", padx=10)
            tk.Label(info_frame, text=f"Date: {deuda['fecha_factura']}").pack(anchor="w", padx=10)
            tk.Label(info_frame, text=f"Total Amount: ${deuda['monto_total']:,.2f}").pack(anchor="w", padx=10)
            tk.Label(info_frame, text=f"Paid: ${deuda['monto_pagado']:,.2f}").pack(anchor="w", padx=10)
            tk.Label(info_frame, text=f"Balance due: ${deuda['saldo_pendiente']:,.2f}", 
                    font=("Arial", 11, "bold"), fg="red").pack(anchor="w", padx=10, pady=5)
            
            # Payment form frame
            form_frame = tk.Frame(payment_window, relief=tk.RAISED, bd=1)
            form_frame.pack(fill="x", padx=10, pady=5)
            
            tk.Label(form_frame, text="REGISTER PAYMENT", font=("Arial", 12, "bold")).pack(pady=5)
            
            # Form fields
            fields_frame = tk.Frame(form_frame)
            fields_frame.pack(padx=10, pady=5)
            
            # Monto
            tk.Label(fields_frame, text="Amount to pay:", font=("Arial", 10)).grid(row=0, column=0, sticky="w", pady=5)
            monto_var = tk.StringVar()
            tk.Entry(fields_frame, textvariable=monto_var, width=20).grid(row=0, column=1, sticky="ew", pady=5, padx=5)
            
            # Método de pago
            tk.Label(fields_frame, text="Payment Method:", font=("Arial", 10)).grid(row=1, column=0, sticky="w", pady=5)
            metodo_var = tk.StringVar()
            metodo_combo = ttk.Combobox(fields_frame, textvariable=metodo_var, width=17,
                                       values=["Cash", "Bank Transfer", "Credit Card", 
                                              "Debit Card", "Check", "Other"])
            metodo_combo.grid(row=1, column=1, sticky="ew", pady=5, padx=5)
            
            # Referencia
            tk.Label(fields_frame, text="Reference (optional):", font=("Arial", 10)).grid(row=2, column=0, sticky="w", pady=5)
            referencia_var = tk.StringVar()
            tk.Entry(fields_frame, textvariable=referencia_var, width=20).grid(row=2, column=1, sticky="ew", pady=5, padx=5)
            
            fields_frame.columnconfigure(1, weight=1)
            
            # Buttons frame
            buttons_frame = tk.Frame(payment_window)
            buttons_frame.pack(fill="x", padx=10, pady=15)
            
            def procesar_pago():
                try:
                    # Validate input
                    monto_str = monto_var.get().strip()
                    if not monto_str:
                        messagebox.showerror("Error", "Enter the payment amount")
                        return
                    
                    monto = Decimal(monto_str)
                    if monto <= 0:
                        messagebox.showerror("Error", "Amount must be greater than 0")
                        return
                    
                    if monto > deuda['saldo_pendiente']:
                        messagebox.showerror("Error", f"Amount cannot exceed outstanding balance (${deuda['saldo_pendiente']:,.2f})")
                        return
                    
                    metodo = metodo_var.get().strip()
                    if not metodo:
                        messagebox.showerror("Error", "Select a payment method")
                        return
                    
                    referencia = referencia_var.get().strip() if referencia_var.get().strip() else None
                    
                    # Register payment
                    usuario = "admin"  # TODO: Get from user_data
                    self.debt_manager.registrar_pago(id_deuda, monto, metodo, referencia, usuario)
                    
                    messagebox.showinfo("Success", f"Payment of ${monto:,.2f} registered successfully")
                    payment_window.destroy()
                    
                    # Refresh main data
                    self.load_data()

                    # Refresh current window
                    # Get client ID from the debt
                    deuda_info = self.debt_manager.obtener_deuda_por_id(id_deuda)
                    if deuda_info:
                        parent_window.destroy()
                        self.open_client_details_window(deuda_info['id_cliente'])
                    
                except (ValueError, decimal.InvalidOperation):
                    messagebox.showerror("Error", "Enter a valid amount")
                except Exception as e:
                    messagebox.showerror("Error", f"Error registering payment: {e}")
            
            tk.Button(buttons_frame, text="Process Payment", command=procesar_pago, 
                     bg="#4CAF50", fg="white", padx=20, pady=5).pack(side="left", padx=5)
            tk.Button(buttons_frame, text="Cancel", command=payment_window.destroy, 
                     bg="#f44336", fg="white", padx=20, pady=5).pack(side="right", padx=5)
            
            # Set focus to amount field
            fields_frame.children['!entry'].focus_set()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading debt information: {e}")
            payment_window.destroy()

def launch_debt_window(user_data=None):
    """Launch the debt management window"""
    try:
        root = tk.Tk()
        app = DebtManagementWindow(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error", f"Error starting debt module: {e}")

if __name__ == "__main__":
    launch_debt_window()