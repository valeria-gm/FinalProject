"""
UI Components Module
Contains all UI building functions and components
"""

import tkinter as tk
from src.config import debug_print, COLORS, USE_LOGIN, USE_SESSION_MANAGER, USE_HOVER_EFFECTS

class UIComponents:
    """Class containing all UI component creation methods"""
    
    def __init__(self, root, user_data):
        self.root = root
        self.user_data = user_data
        self.status_bar = None
    
    def create_header(self, logout_callback):
        """Create application header"""
        try:
            header_frame = tk.Frame(self.root, bg=COLORS['header_bg'], height=120)
            header_frame.pack(fill="x")
            header_frame.pack_propagate(False)
            
            # Container for content
            header_content = tk.Frame(header_frame, bg=COLORS['header_bg'])
            header_content.pack(expand=True, pady=15)
            
            # Main title
            title_label = tk.Label(header_content, 
                                  text="MARKET",
                                  font=("Arial", 24, "bold"),
                                  fg=COLORS['header_text'],
                                  bg=COLORS['header_bg'])
            title_label.pack(pady=(5, 0))
            
            # User information
            user_info = f"Welcome, {self.user_data['nombre_completo']} ({self.user_data['rol'].upper()})"
            user_label = tk.Label(header_content,
                                 text=user_info,
                                 font=("Arial", 12),
                                 fg=COLORS['header_subtitle'],
                                 bg=COLORS['header_bg'])
            user_label.pack(pady=(5, 0))
            
            # Logout button (only if real login is used)
            if USE_LOGIN:
                logout_btn = tk.Button(header_content,
                                      text="Log Out",
                                      command=logout_callback,
                                      font=("Arial", 10),
                                      bg=COLORS['logout_btn'],
                                      fg=COLORS['button_text'],
                                      relief="flat",
                                      cursor="hand2",
                                      padx=15,
                                      pady=5)
                logout_btn.pack(pady=(10, 0))
            
            debug_print("Header created successfully")
            
        except Exception as e:
            debug_print(f"Error creating header: {e}")
            raise
    
    def create_module_card(self, parent, module, row, col, launch_callback):
        """Create a module card"""
        try:
            # Main frame
            card_frame = tk.Frame(parent, 
                                 bg=module['bg_color'],
                                 relief='raised',
                                 bd=2,
                                 cursor='hand2')
            card_frame.grid(row=row, column=col, padx=15, pady=15, sticky="ew")
            
            # Inner frame
            inner_frame = tk.Frame(card_frame, bg=module['bg_color'])
            inner_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Title
            title_label = tk.Label(inner_frame,
                                  text=module['title'],
                                  font=('Arial', 16, 'bold'),
                                  fg='white',
                                  bg=module['bg_color'])
            title_label.pack(pady=(0, 10))
            
            # Description
            desc_label = tk.Label(inner_frame,
                                 text=module['description'],
                                 font=('Arial', 10),
                                 fg='white',
                                 bg=module['bg_color'],
                                 justify='center')
            desc_label.pack(pady=(0, 15))
            
            # Button
            access_btn = tk.Button(inner_frame,
                                  text="OPEN MODULE",
                                  font=('Arial', 10, 'bold'),
                                  bg='white',
                                  fg=module['bg_color'],
                                  relief='flat',
                                  cursor='hand2',
                                  command=lambda: launch_callback(module['module_key']))
            access_btn.pack(pady=(5, 0), ipadx=10, ipady=5)
            
            # Hover effects if enabled
            if USE_HOVER_EFFECTS:
                self.setup_hover_effects(card_frame, inner_frame, title_label, desc_label, module, launch_callback)
            
        except Exception as e:
            debug_print(f"Error creating module card: {e}")
            raise
    
    def setup_hover_effects(self, card_frame, inner_frame, title_label, desc_label, module, launch_callback):
        """Setup hover effects for module cards"""
        def on_enter(event):
            for widget in [card_frame, inner_frame, title_label, desc_label]:
                try:
                    widget.configure(bg=module['hover_color'])
                except:
                    pass
        
        def on_leave(event):
            for widget in [card_frame, inner_frame, title_label, desc_label]:
                try:
                    widget.configure(bg=module['bg_color'])
                except:
                    pass
        
        # Bind events
        for widget in [card_frame, inner_frame, title_label, desc_label]:
            try:
                widget.bind("<Enter>", on_enter)
                widget.bind("<Leave>", on_leave)
                widget.bind("<Button-1>", lambda e: launch_callback(module['module_key']))
            except:
                pass
    
    def create_status_bar(self, close_callback):
        """Create status bar"""
        try:
            if USE_SESSION_MANAGER:
                debug_print("Creating status bar with session manager...")
                from src.auth.session_manager import SessionStatusBar
                self.status_bar = SessionStatusBar(self.root)
            else:
                debug_print("Creating simple status bar...")
                status_frame = tk.Frame(self.root, relief=tk.SUNKEN, bd=1)
                status_frame.pack(side=tk.BOTTOM, fill=tk.X)
                
                user_info = f"User: {self.user_data['nombre_completo']}"
                status_label = tk.Label(status_frame, text=user_info, anchor=tk.W)
                status_label.pack(side=tk.LEFT, padx=5, pady=2)
                
                # Exit button
                exit_btn = tk.Button(status_frame,
                                    text="Exit",
                                    command=close_callback,
                                    bg=COLORS['exit_btn'],
                                    fg=COLORS['button_text'],
                                    relief="flat",
                                    padx=10)
                exit_btn.pack(side=tk.RIGHT, padx=5, pady=2)
                
            debug_print("Status bar created successfully")
            
        except Exception as e:
            debug_print(f"Error creating status bar: {e}")
            # Status bar is not critical
    
    def create_scrollable_content(self, parent):
        """Create scrollable content area with canvas"""
        # Canvas for scroll
        canvas = tk.Canvas(parent, bg="#f5f5f5", highlightthickness=0)
        scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f5f5f5")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mouse wheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        return scrollable_frame