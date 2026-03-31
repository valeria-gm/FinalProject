# MARKET — Business Management System

#### Video Demo:


#### Description:
 
Market is a desktop business management application built with Python, Tkinter, and MySQL. It provides a complete suite of tools for managing commercial operations: invoicing with multi-tab order management, group-based product pricing, inventory tracking through purchase registration, profit analysis with interactive charts, client and debt management, and user administration with role-based access control. The application was developed as my final project for CS50 and is based on a system originally built as a freelance project by a team of three programmers, including myself. This version is a separate, simplified adaptation that I built independently, using Claude as an assistive tool for code revisions, debugging, and refinements.


## Architecture

The project follows a modular architecture where each business function operates as an independent module launched from a central dashboard. The entry point is `main.py`, which initializes the application and delegates to `src/main_application.py` for window creation, login handling, and the module grid. Each module runs in its own subprocess via `launch_module.py`, which maps module keys to their respective initialization functions and passes user data as serialized JSON. This subprocess design means that if a module crashes, the main dashboard remains unaffected.
 
Configuration lives in `src/config.py`, where feature flags control login enforcement, session management, canvas scrolling, and hover effects. The UI layer in `src/ui/` contains `module_launcher.py` (module definitions with titles, colors, and role requirements) and `ui_components.py` (header, scrollable content, module cards, and status bar).


## File Descriptions

**Authentication (`src/auth/`):** `login_window.py` renders the login screen with credential validation and a remember-me feature. `auth_manager.py` handles password hashing with bcrypt (12 rounds), failed attempt tracking, automatic account lockout after three consecutive failures, and access logging. `session_manager.py` implements a 30-minute inactivity timeout with a live countdown in the status bar. `hash_passwords.py` and `crear_usuario.py` are utility scripts for initial user setup.

**Database (`src/database/`):** `cloud_config.py` stores the MySQL connection parameters. `conexion.py` establishes and verifies database connections. `db_manager.py` provides a shared connection manager used by the authentication system. The SQL files in `sql/` define the complete database: `schema.sql` creates 15 tables with foreign keys, CHECK constraints, and indexes; `triggers.sql` defines 5 triggers that automate debt generation on invoice creation, stock updates on purchase registration, and order validation; `views.sql` creates 9 views that pre-compute discount calculations, client account summaries, profit margins, and payment histories.

**Generate Receipts (`src/modules/receipts/`):** This is the largest module. `receipt_generator.py` provides a multi-tab interface where users can work on up to five simultaneous orders. Each tab has its own client selection, product search, and shopping cart. `components/carrito_module.py` implements the cart with named sections — products can be organized into categories like Produce or Beverages, and sections can be added, renamed, or moved. `components/orden_manager.py` handles order persistence using a folio sequence table with row-level locking to guarantee unique folio numbers. `components/ventana_ordenes.py` displays active drafts and completed order history with search, edit, and delete capabilities. `components/database.py` contains the SQL queries for client lookup, product search, and invoice creation. `components/generador_pdf.py` and `components/generador_excel.py` export receipts in both formats, supporting simple and sectioned layouts. `fecha_utils.py` provides date validation and a calendar popup.

**Price Editor (`src/modules/pricing/`):** `price_editor.py` allows administrators to manage product prices on a per-group basis. Each product can have a different base price for each client group, enabling differentiated pricing strategies. The interface shows discount previews, supports batch editing with save/discard, and includes product creation and deletion with referential integrity warnings.

**Purchase Registry (`src/modules/inventory/`):** `registro_compras.py` records product purchases with automatic stock updates via database trigger. It validates dates, protects special products from non-admin modification, and maintains a filterable purchase history with edit and delete support.

**Profit Analysis (`src/modules/analytics/`):** `analizador_ganancias.py` is the analytics engine. Its main window shows a summary dashboard and a filterable product profitability table. The Advanced Statistics window offers five chart tabs built with Matplotlib: top profitable and loss-making products, profit by product with margin annotations, temporal trends configurable by day/week/month/quarter/year with three analysis modes, client comparison with a top-5 auto-selector, and group-level sales overview. It can also export a daily PDF report with sales, purchases, and net profit.

**Manage Clients (`src/modules/clients/`):** `client_manager.py` provides full CRUD for the three-level hierarchy: client types (with discount percentages), groups (linked to a type), and individual clients (belonging to a group). Deletion is protected when records have existing invoices.

**Debt Management (`src/modules/deudas/`):** `debt_manager.py` handles the business logic for partial payments — debts are created automatically by a database trigger when invoice details are inserted, and payments can be registered incrementally with support for cash, transfer, check, or other methods. `debt_window.py` provides the interface with a summary dashboard, per-client debt detail, payment registration, and collection statistics.

**Manage Users (`src/modules/users/`):** `user_manager.py` enables administrators to create, edit, activate/deactivate, and delete user accounts. It enforces username validation, password requirements, and prevents self-deletion or self-deactivation.


## Design Choices
 
The most significant design decision was implementing **group-based pricing** rather than a single price per product. In the original freelance project, the business needed different prices for wholesale, retail, and special clients. I implemented this through a `precio_por_grupo` junction table that pairs each product with each client group, combined with a `tipo_cliente` table that defines discount percentages. This adds complexity but accurately models real-world pricing — when a sale is made, the system looks up the base price for that client's group and applies the client type's discount automatically.
 
I chose to use **database triggers** for debt generation and stock updates rather than handling these in application code. This ensures data consistency even if the application crashes mid-transaction or if records are inserted through a different client. The tradeoff is that the business logic is split between Python and SQL, but for critical operations like financial record-keeping, database-level enforcement felt more reliable.
 
The **folio numbering system** uses a dedicated single-row table with `SELECT ... FOR UPDATE` locking rather than MySQL's `AUTO_INCREMENT`. This was necessary because folio numbers need to be reserved when an order is saved as a draft, not just when a sale is completed. Auto-increment would leave gaps when drafts are deleted, and the business required strictly sequential folios.
 
I debated whether to use **soft deletes** (setting `activo = FALSE`) or hard deletes for saved orders. I chose soft deletes because completed orders should never disappear from the system — they represent financial records. A trigger prevents physical deletion of registered orders, while draft orders can be fully deleted. This preserves the audit trail without cluttering the active order list.
 
Finally, **products marked as special** receive additional access controls: only administrators can override their price at the point of sale or modify their purchase records. This was designed for high-value or sensitive items where pricing errors could be costly. The flag is a simple boolean column, but its effect propagates across the receipts, pricing, and inventory modules.
