import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import configparser
import os

from src.services.entry_service import EntryService
from src.services.supplier_service import SupplierService
from src.services.reminder_service import ReminderService
from src.services.email_service import EmailService
from src.utils.constants import DATA_DIR


class MainWindow:
    def __init__(self, current_user=None, permissions=None):
        self.root = tk.Tk()
        self.root.title("WKZ & Bonus Tracker")
        self.root.geometry("1100x700")
        self.root.minsize(900, 550)

        self.current_user = current_user
        self.permissions = permissions

        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.ini")

        # Store: use DatabaseStore if [Database] url is configured, else Excel
        import configparser as _cp
        _cfg = _cp.ConfigParser()
        _cfg.read(self.config_path)
        _db_url = _cfg.get("Database", "url", fallback="").strip() or None
        if _db_url:
            from src.data.database_store import DatabaseStore
            self.store = DatabaseStore(_db_url)
        else:
            from src.data.excel_store import ExcelStore
            self.store = ExcelStore()
        self.entry_service = EntryService(self.store)
        self.supplier_service = SupplierService(self.store)
        self.reminder_service = ReminderService(self.entry_service)
        self.email_service = EmailService()

        self._build_menu()
        self._build_toolbar()
        self._build_main_area()
        self._build_statusbar()

        # Page registry
        self.pages = {}
        self.current_page = None
        self._create_pages()
        self._show_page("dashboard")

        # Keyboard shortcuts
        self.root.bind("<Control-n>", lambda e: self._new_entry())
        self.root.bind("<Control-e>", lambda e: self._open_export())
        self.root.bind("<Control-q>", lambda e: self.root.quit())

        # Auto-import CSV on start
        self._auto_import_csv()

        # Periodic reminder check
        self._check_reminders()

    def _can(self, perm: str) -> bool:
        """Check a permission, defaults to True when no permissions object provided."""
        if self.permissions is None:
            return True
        return bool(getattr(self.permissions, perm, True))

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Neuer Eintrag (Strg+N)", command=self._new_entry)

        export_state = tk.NORMAL if self._can("can_export") else tk.DISABLED
        file_menu.add_command(label="Export (Strg+E)", command=self._open_export,
                              state=export_state)

        import_state = tk.NORMAL if self._can("can_import") else tk.DISABLED
        file_menu.add_command(label="CSV Import", command=self._manual_csv_import,
                              state=import_state)

        file_menu.add_separator()
        file_menu.add_command(label="Beenden (Strg+Q)", command=self.root.quit)
        menubar.add_cascade(label="Datei", menu=file_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="E-Mail-Erinnerung senden",
                               command=self._send_email_reminder)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Über", command=lambda: messagebox.showinfo(
            "Über", "WKZ & Bonus Tracker\nVersion 1.0\n\nVerwaltung von Werbekostenzuschüssen,\nKickbacks und Bonusarten."
        ))
        menubar.add_cascade(label="Hilfe", menu=help_menu)

    def _build_toolbar(self):
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=(5, 0))

        ttk.Button(toolbar, text="+ Neuer Eintrag", command=self._new_entry).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Lieferanten", command=lambda: self._show_page("suppliers")).pack(side=tk.LEFT, padx=2)

        if self._can("can_import"):
            ttk.Button(toolbar, text="CSV Import", command=self._manual_csv_import).pack(side=tk.LEFT, padx=2)
        if self._can("can_export"):
            ttk.Button(toolbar, text="Export", command=self._open_export).pack(side=tk.LEFT, padx=2)

        ttk.Button(toolbar, text="← Zurück zum Hauptmenü",
                   command=self._back_to_launcher).pack(side=tk.RIGHT, padx=2)

    def _build_main_area(self):
        self.main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Navigation
        nav_frame = ttk.Frame(self.main_pane, width=140)
        self.nav_list = tk.Listbox(nav_frame, font=("Segoe UI", 10), activestyle="none",
                                   selectbackground="#4472C4", selectforeground="white")
        self.nav_list.pack(fill=tk.BOTH, expand=True)

        nav_items = [
            ("dashboard", "Dashboard"),
            ("calendar", "Kalender"),
            ("all", "Alle Einträge"),
            ("wkz", "WKZ"),
            ("kickback", "Kickback"),
            ("umsatzbonus", "Umsatzbonus"),
            ("lagerwertausgleich", "Lagerwertausgleich"),
            ("suppliers", "Lieferanten"),
        ]
        self._nav_keys = []
        for key, label in nav_items:
            self.nav_list.insert(tk.END, f"  {label}")
            self._nav_keys.append(key)

        self.nav_list.bind("<<ListboxSelect>>", self._on_nav_select)
        self.nav_list.selection_set(0)

        self.main_pane.add(nav_frame, weight=0)

        # Content area
        self.content_frame = ttk.Frame(self.main_pane)
        self.main_pane.add(self.content_frame, weight=1)

    def _build_statusbar(self):
        self.statusbar = ttk.Label(self.root, text="", relief=tk.SUNKEN, anchor=tk.W,
                                   padding=(5, 2))
        self.statusbar.pack(fill=tk.X, side=tk.BOTTOM)

    def _create_pages(self):
        from src.ui.dashboard import DashboardPage
        from src.ui.entry_table_view import EntryTablePage
        from src.ui.supplier_view import SupplierOverviewPage
        from src.ui.calendar_view import CalendarPage

        self.pages["dashboard"] = DashboardPage(self.content_frame, self)
        self.pages["calendar"] = CalendarPage(self.content_frame, self)
        self.pages["all"] = EntryTablePage(self.content_frame, self, filter_type=None)
        self.pages["wkz"] = EntryTablePage(self.content_frame, self, filter_type="WKZ")
        self.pages["kickback"] = EntryTablePage(self.content_frame, self, filter_type="Kickback")
        self.pages["umsatzbonus"] = EntryTablePage(self.content_frame, self, filter_type="Umsatzbonus")
        self.pages["lagerwertausgleich"] = EntryTablePage(self.content_frame, self, filter_type="Lagerwertausgleich")
        self.pages["suppliers"] = SupplierOverviewPage(self.content_frame, self)

    def _show_page(self, page_key: str):
        if self.current_page:
            self.pages[self.current_page].hide()
        self.current_page = page_key
        self.pages[page_key].show()

        if page_key in self._nav_keys:
            idx = self._nav_keys.index(page_key)
            self.nav_list.selection_clear(0, tk.END)
            self.nav_list.selection_set(idx)

    def _on_nav_select(self, event):
        sel = self.nav_list.curselection()
        if sel:
            key = self._nav_keys[sel[0]]
            self._show_page(key)

    def _new_entry(self):
        from src.ui.entry_form import EntryFormDialog
        EntryFormDialog(self.root, self, entry=None)

    def _open_export(self):
        from src.ui.export_dialog import ExportDialog
        ExportDialog(self.root, self)

    def _open_settings(self):
        from src.ui.settings_dialog import SettingsDialog
        SettingsDialog(self.root, self)

    def _auto_import_csv(self):
        if not self._can("can_import"):
            return
        try:
            config = configparser.ConfigParser()
            config.read(self.config_path, encoding="utf-8")
            csv_path = config.get("Import", "csv_path", fallback="").strip()
            if csv_path and os.path.exists(csv_path):
                result = self.supplier_service.import_from_csv(csv_path)
                self.statusbar.config(text=result)
        except Exception:
            pass

    def _manual_csv_import(self):
        config = configparser.ConfigParser()
        config.read(self.config_path, encoding="utf-8")
        csv_path = config.get("Import", "csv_path", fallback="").strip()

        if not csv_path or not os.path.exists(csv_path):
            csv_path = filedialog.askopenfilename(
                title="CSV-Datei auswählen",
                filetypes=[("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*")]
            )
            if not csv_path:
                return

        result = self.supplier_service.import_from_csv(csv_path)
        messagebox.showinfo("CSV Import", result)
        self.refresh_current_page()

    def _send_email_reminder(self):
        overdue, due_soon = self.reminder_service.check()
        result = self.email_service.send_reminder(overdue, due_soon)
        messagebox.showinfo("E-Mail", result)

    def _check_reminders(self):
        try:
            text = self.reminder_service.get_status_text()
            self.statusbar.config(text=text)
        except Exception:
            pass
        self.root.after(3600000, self._check_reminders)

    def refresh_current_page(self):
        if self.current_page and self.current_page in self.pages:
            self.pages[self.current_page].refresh()
        self._check_reminders()

    def _back_to_launcher(self):
        self.root.destroy()
        from src.ui.launcher import LauncherWindow
        app = LauncherWindow()
        app.run()

    def run(self):
        self.root.mainloop()
