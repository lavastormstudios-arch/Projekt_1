import tkinter as tk
from tkinter import ttk, messagebox

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

        import os, configparser as _cp
        _config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "config.ini")
        _cfg = _cp.ConfigParser()
        _cfg.read(_config_path)
        _db_url = _cfg.get("Database", "url", fallback="").strip() or None
        if _db_url:
            from src.data.database_store import DatabaseStore
            self.store = DatabaseStore(_db_url)
        else:
            from src.data.excel_store import ExcelStore
            self.store = ExcelStore()
        self.fob_service = FobService(self.store)

        self._build_toolbar()
        self._build_filter_bar()

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
        self._update_filter_dropdowns()
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
            ttk.Button(toolbar, text="Neuer Preis",
                       command=self._new_prices).pack(side=tk.LEFT, padx=2)

        _delete_roles = {"Admin", "Abteilungsleiter", "Teamleiter"}
        _user_role = self.current_user.role if self.current_user else ""
        _can_delete = (
            (self.permissions and self.permissions.can_delete)
            and _user_role in _delete_roles
        )
        if _can_delete:
            ttk.Button(toolbar, text="Löschen",
                       command=self._delete_entry).pack(side=tk.LEFT, padx=2)

        # Archiv toggle on right side
        self._show_archiv_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(toolbar, text="Archiv anzeigen",
                        variable=self._show_archiv_var,
                        command=self._toggle_archiv).pack(side=tk.RIGHT, padx=6)

    def _build_filter_bar(self):
        bar = ttk.Frame(self.root)
        bar.pack(fill=tk.X, padx=5, pady=(2, 0))

        ttk.Label(bar, text="Suche:").pack(side=tk.LEFT, padx=(0, 2))
        self._filter_text_var = tk.StringVar()
        ttk.Entry(bar, textvariable=self._filter_text_var, width=20).pack(
            side=tk.LEFT, padx=(0, 10))
        self._filter_text_var.trace_add("write", self._on_filter_change)

        ttk.Label(bar, text="CM:").pack(side=tk.LEFT, padx=(0, 2))
        self._filter_cm_var = tk.StringVar(value="Alle")
        self._cm_combo = ttk.Combobox(bar, textvariable=self._filter_cm_var,
                                      state="readonly", width=12)
        self._cm_combo.pack(side=tk.LEFT, padx=(0, 10))
        self._cm_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        ttk.Label(bar, text="Lieferant:").pack(side=tk.LEFT, padx=(0, 2))
        self._filter_lief_var = tk.StringVar(value="Alle")
        self._lief_combo = ttk.Combobox(bar, textvariable=self._filter_lief_var,
                                        state="readonly", width=16)
        self._lief_combo.pack(side=tk.LEFT, padx=(0, 10))
        self._lief_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        ttk.Label(bar, text="Warengruppe:").pack(side=tk.LEFT, padx=(0, 2))
        self._filter_wgr_var = tk.StringVar(value="Alle")
        self._wgr_combo = ttk.Combobox(bar, textvariable=self._filter_wgr_var,
                                       state="readonly", width=14)
        self._wgr_combo.pack(side=tk.LEFT, padx=(0, 10))
        self._wgr_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        ttk.Button(bar, text="✕ Zurücksetzen",
                   command=self._reset_filter).pack(side=tk.LEFT)

    # ------------------------------------------------------------------
    # Filter helpers
    # ------------------------------------------------------------------

    def _on_filter_change(self, *_):
        if not hasattr(self, "_table"):
            return
        self._table.apply_filter(
            text=self._filter_text_var.get().strip(),
            cm=self._filter_cm_var.get() if self._filter_cm_var.get() != "Alle" else "",
            lieferant=self._filter_lief_var.get() if self._filter_lief_var.get() != "Alle" else "",
            warengruppe=self._filter_wgr_var.get() if self._filter_wgr_var.get() != "Alle" else "",
        )
        self._refresh_status()

    def _reset_filter(self):
        self._filter_text_var.set("")
        self._filter_cm_var.set("Alle")
        self._filter_lief_var.set("Alle")
        self._filter_wgr_var.set("Alle")
        self._on_filter_change()

    def _update_filter_dropdowns(self):
        for field, combo, var in [
            ("cm",          self._cm_combo,   self._filter_cm_var),
            ("lieferant",   self._lief_combo, self._filter_lief_var),
            ("warengruppe", self._wgr_combo,  self._filter_wgr_var),
        ]:
            values = ["Alle"] + self._table.get_distinct_values(field)
            combo["values"] = values
            if var.get() not in values:
                var.set("Alle")

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

    def _new_prices(self):
        entry = self._table.selected_entry()
        if entry is None:
            messagebox.showinfo("Hinweis", "Bitte zuerst einen Artikel auswählen.",
                                parent=self.root)
            return
        from src.ui.fob_price_dialog import FobPriceDialog
        FobPriceDialog(self.root, entry, self.fob_service,
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
        self._update_filter_dropdowns()
        self._refresh_status()

    def _after_save(self):
        self._table.refresh()
        self._update_filter_dropdowns()
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
