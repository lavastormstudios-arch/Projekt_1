import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from src.models.enums import EntryType, EntryStatus
from src.data.export import export_entries


class ExportDialog:
    def __init__(self, parent, app):
        self.app = app

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Export")
        self.dialog.geometry("400x350")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._build()

    def _build(self):
        f = ttk.Frame(self.dialog, padding=15)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text="Excel-Export", font=("Segoe UI", 14, "bold")).pack(anchor=tk.W, pady=(0, 10))

        # Filters
        filter_frame = ttk.LabelFrame(f, text="Filter", padding=10)
        filter_frame.pack(fill=tk.X, pady=5)

        ttk.Label(filter_frame, text="Typ:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.type_var = tk.StringVar(value="Alle")
        ttk.Combobox(filter_frame, textvariable=self.type_var, width=20, state="readonly",
                     values=["Alle"] + [t.value for t in EntryType]).grid(
            row=0, column=1, padx=10, pady=3)

        ttk.Label(filter_frame, text="Status:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.status_var = tk.StringVar(value="Alle")
        ttk.Combobox(filter_frame, textvariable=self.status_var, width=20, state="readonly",
                     values=["Alle"] + [s.value for s in EntryStatus]).grid(
            row=1, column=1, padx=10, pady=3)

        # Title
        ttk.Label(f, text="Report-Titel:").pack(anchor=tk.W, pady=(10, 2))
        self.title_var = tk.StringVar(value="WKZ & Bonus Report")
        ttk.Entry(f, textvariable=self.title_var, width=40).pack(anchor=tk.W)

        # Buttons
        btn_frame = ttk.Frame(f)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Exportieren", command=self._export).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Abbrechen", command=self.dialog.destroy).pack(side=tk.LEFT, padx=10)

    def _export(self):
        # Get filtered entries
        entry_type = None
        if self.type_var.get() != "Alle":
            entry_type = EntryType(self.type_var.get())
        status = None
        if self.status_var.get() != "Alle":
            status = EntryStatus(self.status_var.get())

        entries = self.app.entry_service.filter_entries(entry_type=entry_type, status=status)

        if not entries:
            messagebox.showinfo("Export", "Keine Einträge zum Exportieren gefunden.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel-Dateien", "*.xlsx")],
            title="Export speichern als"
        )
        if not filepath:
            return

        try:
            result = export_entries(entries, filepath=filepath, title=self.title_var.get())
            messagebox.showinfo("Export", f"Export erfolgreich:\n{result}")
            self.dialog.destroy()
        except Exception as ex:
            messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{ex}")
