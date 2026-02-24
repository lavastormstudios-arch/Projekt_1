import tkinter as tk
from tkinter import ttk, messagebox

from src.data.excel_store import ExcelStore
from src.services.fob_service import FobService


class FobWindow:
    """Standalone window for FOB-Kalkulation."""

    def __init__(self, current_user=None, permissions=None):
        self.root = tk.Tk()
        self.root.title("FOB-Kalkulation")
        self.root.geometry("1200x700")
        self.root.minsize(900, 560)

        self.current_user = current_user
        self.permissions = permissions

        self.store = ExcelStore()
        self.fob_service = FobService(self.store)

        self._build_toolbar()

        # Status bar
        self._status_var = tk.StringVar(value="")
        status = ttk.Label(self.root, textvariable=self._status_var,
                           relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2))
        status.pack(fill=tk.X, side=tk.BOTTOM)

        # Table
        content = ttk.Frame(self.root)
        content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        from src.ui.fob_table_view import FobTableView
        self._table = FobTableView(content, self.fob_service, permissions=self.permissions)
        self._table.pack(fill=tk.BOTH, expand=True)
        self._table.refresh()
        self._refresh_status()

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------

    def _build_toolbar(self):
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=(5, 0))

        ttk.Button(toolbar, text="← Zurück",
                   command=self._back_to_launcher).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y,
                                                         padx=6, pady=2)

        can_edit = self.permissions.can_edit if self.permissions else True

        if can_edit:
            ttk.Button(toolbar, text="+ Neu",
                       command=self._new_entry).pack(side=tk.LEFT, padx=2)
            ttk.Button(toolbar, text="Bearbeiten",
                       command=self._edit_entry).pack(side=tk.LEFT, padx=2)

        if self.permissions and self.permissions.can_delete:
            ttk.Button(toolbar, text="Löschen",
                       command=self._delete_entry).pack(side=tk.LEFT, padx=2)

        # Archiv toggle on right side
        self._show_archiv_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(toolbar, text="Archiv anzeigen",
                        variable=self._show_archiv_var,
                        command=self._toggle_archiv).pack(side=tk.RIGHT, padx=6)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _new_entry(self):
        from src.ui.fob_form import FobFormDialog
        FobFormDialog(self.root, self.fob_service, entry=None,
                      on_save=self._after_save)

    def _edit_entry(self):
        entry = self._table.selected_entry()
        if entry is None:
            messagebox.showinfo("Hinweis", "Bitte zuerst einen Artikel auswählen.",
                                parent=self.root)
            return
        from src.ui.fob_form import FobFormDialog
        FobFormDialog(self.root, self.fob_service, entry=entry,
                      on_save=self._after_save)

    def _delete_entry(self):
        entry = self._table.selected_entry()
        if entry is None:
            messagebox.showinfo("Hinweis", "Bitte zuerst einen Artikel auswählen.",
                                parent=self.root)
            return
        if not messagebox.askyesno(
            "Löschen bestätigen",
            f"Artikel '{entry.bezeichnung}' ({entry.artnr}) wirklich löschen?",
            parent=self.root,
        ):
            return
        self.fob_service.delete(entry.id)
        self._after_save()

    def _toggle_archiv(self):
        self._table.set_show_archiv(self._show_archiv_var.get())
        self._refresh_status()

    def _after_save(self):
        self._table.refresh()
        self._refresh_status()

    def _refresh_status(self):
        self._status_var.set(self._table.get_status_text())

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _back_to_launcher(self):
        self.root.destroy()
        from src.ui.launcher import LauncherWindow
        app = LauncherWindow()
        app.run()

    def run(self):
        self.root.mainloop()
