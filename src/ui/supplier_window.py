import tkinter as tk
from tkinter import ttk

from src.data.excel_store import ExcelStore
from src.services.supplier_service import SupplierService


class SupplierWindow:
    """Standalone window for Lieferantenmanagement, independent of MainWindow."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Lieferantenmanagement")
        self.root.geometry("1150x720")
        self.root.minsize(900, 580)

        self.store = ExcelStore()
        self.supplier_service = SupplierService(self.store)

        self._build_toolbar()

        self.statusbar = ttk.Label(self.root, text="", relief=tk.SUNKEN,
                                   anchor=tk.W, padding=(5, 2))
        self.statusbar.pack(fill=tk.X, side=tk.BOTTOM)

        content = ttk.Frame(self.root)
        content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        from src.ui.supplier_view import SupplierPage
        self._page = SupplierPage(content, self)
        self._page.show()

    def _build_toolbar(self):
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=(5, 0))
        ttk.Button(toolbar, text="← Zurück zum Hauptmenü",
                   command=self._back_to_launcher).pack(side=tk.RIGHT, padx=2)

    def refresh_current_page(self):
        self._page.refresh()

    def _back_to_launcher(self):
        self.root.destroy()
        from src.ui.launcher import LauncherWindow
        app = LauncherWindow()
        app.run()

    def run(self):
        self.root.mainloop()
