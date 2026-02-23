import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import configparser
import shutil
from datetime import datetime
import os

from src.data.excel_store import ExcelStore
from src.services.entry_service import EntryService
from src.services.supplier_service import SupplierService
from src.services.reminder_service import ReminderService
from src.services.email_service import EmailService
from src.utils.constants import DATA_DIR


class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("WKZ & Bonus Tracker")
        self.root.geometry("1100x700")
        self.root.minsize(900, 550)

        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.ini")

        # Services
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

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Neuer Eintrag (Strg+N)", command=self._new_entry)
        file_menu.add_command(label="Export (Strg+E)", command=self._open_export)
        file_menu.add_command(label="CSV Import", command=self._manual_csv_import)
        file_menu.add_separator()
        file_menu.add_command(label="Backup erstellen", command=self._backup)
        file_menu.add_separator()
        file_menu.add_command(label="Beenden (Strg+Q)", command=self.root.quit)
        menubar.add_cascade(label="Datei", menu=file_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="E-Mail-Erinnerung senden", command=self._send_email_reminder)
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
        ttk.Button(toolbar, text="CSV Import", command=self._manual_csv_import).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Export", command=self._open_export).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="← Zurück zum Hauptmenü", command=self._back_to_launcher).pack(side=tk.RIGHT, padx=2)

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
        self.pages["suppliers"] = SupplierOverviewPage(self.content_frame, self)

    def _show_page(self, page_key: str):
        if self.current_page:
            self.pages[self.current_page].hide()
        self.current_page = page_key
        self.pages[page_key].show()

        # Update nav selection
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
        # Try configured path first, otherwise ask user
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

    def _backup(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(DATA_DIR, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        for filename in ("entries.xlsx", "suppliers.xlsx"):
            src = os.path.join(DATA_DIR, filename)
            if os.path.exists(src):
                dst = os.path.join(backup_dir, f"{filename.replace('.xlsx', '')}_{timestamp}.xlsx")
                shutil.copy2(src, dst)
        messagebox.showinfo("Backup", f"Backup erstellt in:\n{backup_dir}")

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
        # Re-check every 60 minutes
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
