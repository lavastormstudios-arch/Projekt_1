import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from src.models.enums import EntryType, EntryStatus
from src.utils.date_helpers import format_date


class EntryTablePage:
    def __init__(self, parent, app, filter_type: Optional[str] = None):
        self.parent = parent
        self.app = app
        self.filter_type = filter_type
        self.frame = ttk.Frame(parent)
        self._entries = []
        self._sort_col = None
        self._sort_reverse = False
        self._build()

    def _build(self):
        title = self.filter_type if self.filter_type else "Alle Einträge"
        ttk.Label(self.frame, text=title, font=("Segoe UI", 16, "bold")).pack(
            anchor=tk.W, padx=10, pady=(10, 5))

        # Filter bar
        filter_frame = ttk.Frame(self.frame)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)

        if not self.filter_type:
            ttk.Label(filter_frame, text="Typ:").pack(side=tk.LEFT, padx=(0, 5))
            self.type_var = tk.StringVar(value="Alle")
            type_combo = ttk.Combobox(filter_frame, textvariable=self.type_var, width=15, state="readonly",
                                      values=["Alle"] + [t.value for t in EntryType])
            type_combo.pack(side=tk.LEFT, padx=(0, 10))
            type_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(filter_frame, text="Status:").pack(side=tk.LEFT, padx=(0, 5))
        self.status_var = tk.StringVar(value="Alle")
        status_combo = ttk.Combobox(filter_frame, textvariable=self.status_var, width=15, state="readonly",
                                    values=["Alle"] + [s.value for s in EntryStatus])
        status_combo.pack(side=tk.LEFT, padx=(0, 10))
        status_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(filter_frame, text="Suche:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=25)
        search_entry.pack(side=tk.LEFT, padx=(0, 5))
        search_entry.bind("<Return>", lambda e: self.refresh())
        ttk.Button(filter_frame, text="Filtern", command=self.refresh).pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="Zurücksetzen", command=self._reset_filters).pack(side=tk.LEFT)

        # Treeview
        columns = ("id", "type", "supplier", "desc", "status", "amount", "deadline", "billed")
        tree_frame = ttk.Frame(self.frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        headers = {
            "id": ("ID", 70),
            "type": ("Typ", 110),
            "supplier": ("Lieferant", 150),
            "desc": ("Beschreibung", 200),
            "status": ("Status", 100),
            "amount": ("Betrag", 100),
            "deadline": ("Frist", 100),
            "billed": ("Abger. am", 100),
        }
        for col, (text, width) in headers.items():
            self.tree.heading(col, text=text, command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=width, minwidth=50)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Context menu
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_selection_change)

        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="Bearbeiten", command=self._edit_selected)
        self.context_menu.add_command(label="Löschen", command=self._delete_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Als abgerechnet markieren", command=self._mark_billed)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Rechnung erstellen", command=self._create_invoice)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Storno erstellen", command=self._create_storno)
        self.context_menu.add_command(label="Anpassen", command=self._adjust_invoice)

        # Buttons
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(btn_frame, text="+ Neuer Eintrag", command=self._new_entry).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Bearbeiten", command=self._edit_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Löschen", command=self._delete_selected).pack(side=tk.LEFT, padx=2)
        self._invoice_btn_var = tk.StringVar(value="Rechnung erstellen")
        self._invoice_btn = ttk.Button(btn_frame, textvariable=self._invoice_btn_var,
                                       command=self._create_invoice)
        self._invoice_btn.pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Storno", command=self._create_storno).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Anpassen", command=self._adjust_invoice).pack(side=tk.LEFT, padx=2)

    def _reset_filters(self):
        if hasattr(self, "type_var"):
            self.type_var.set("Alle")
        self.status_var.set("Alle")
        self.search_var.set("")
        self.refresh()

    def _sort_by(self, col):
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = False
        self._populate_tree()

    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())

        entries = list(self._entries)

        # Sort
        if self._sort_col:
            col_map = {
                "id": lambda e: e.id,
                "type": lambda e: e.entry_type.value,
                "supplier": lambda e: e.supplier_name.lower(),
                "desc": lambda e: e.description.lower(),
                "status": lambda e: e.status.value,
                "amount": lambda e: e.amount,
                "deadline": lambda e: str(e.billing_deadline or ""),
                "billed": lambda e: str(e.date_billed or ""),
            }
            key_fn = col_map.get(self._sort_col, lambda e: "")
            entries.sort(key=key_fn, reverse=self._sort_reverse)

        for e in entries:
            deadline = e.billing_deadline.strftime("%d.%m.%y") if e.billing_deadline else ""
            billed = e.date_billed.strftime("%d.%m.%y") if e.date_billed else ""
            tags = ()
            if e.status == EntryStatus.UEBERFAELLIG:
                tags = ("overdue",)
            elif e.is_overdue():
                tags = ("overdue",)
            self.tree.insert("", tk.END, iid=e.id, values=(
                e.id, e.entry_type.value, e.supplier_name, e.description,
                e.status.value, f"{e.amount:,.2f}", deadline, billed
            ), tags=tags)

        self.tree.tag_configure("overdue", foreground="#D32F2F")

    def refresh(self):
        entry_type = None
        if self.filter_type:
            entry_type = EntryType(self.filter_type)
        elif hasattr(self, "type_var") and self.type_var.get() != "Alle":
            entry_type = EntryType(self.type_var.get())

        status = None
        if self.status_var.get() != "Alle":
            status = EntryStatus(self.status_var.get())

        search = self.search_var.get() or None

        self._entries = self.app.entry_service.filter_entries(
            entry_type=entry_type, status=status, search_text=search
        )
        self._populate_tree()

    def _get_selected_entry(self):
        """Return first selected entry (for single-item actions)."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Hinweis", "Bitte einen Eintrag auswählen.")
            return None
        return self.app.entry_service.get_by_id(sel[0])

    def _get_selected_entries(self):
        """Return all selected entries."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Hinweis", "Bitte mindestens einen Eintrag auswählen.")
            return []
        return [e for e in (self.app.entry_service.get_by_id(eid) for eid in sel) if e]

    def _resolve_supplier(self, entry):
        """Look up supplier by ID, fall back to name match."""
        supplier = None
        if entry.supplier_id:
            supplier = self.app.supplier_service.get_by_id(entry.supplier_id)
        if not supplier:
            supplier = self.app.supplier_service.get_by_name(entry.supplier_name)
        return supplier

    def _on_double_click(self, event):
        self._edit_selected()

    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            # Keep existing multi-selection if right-clicking an already selected row
            if item not in self.tree.selection():
                self.tree.selection_set(item)
            # Dynamically enable/disable billing-related menu items
            entry = self.app.entry_service.get_by_id(item)
            is_final = entry and entry.status in (EntryStatus.ABGERECHNET, EntryStatus.STORNIERT)
            state = "disabled" if is_final else "normal"
            self.context_menu.entryconfigure("Als abgerechnet markieren", state=state)
            self.context_menu.entryconfigure("Rechnung erstellen", state=state)
            self.context_menu.post(event.x_root, event.y_root)

    def _on_selection_change(self, event=None):
        n = len(self.tree.selection())
        if n > 1:
            self._invoice_btn_var.set(f"Rechnungen erstellen ({n})")
        else:
            self._invoice_btn_var.set("Rechnung erstellen")

    def _new_entry(self):
        from src.ui.entry_form import EntryFormDialog
        default_type = self.filter_type
        EntryFormDialog(self.app.root, self.app, entry=None, default_type=default_type)

    def _edit_selected(self):
        entry = self._get_selected_entry()
        if entry:
            from src.ui.entry_form import EntryFormDialog
            EntryFormDialog(self.app.root, self.app, entry=entry)

    def _delete_selected(self):
        entry = self._get_selected_entry()
        if entry:
            if messagebox.askokcancel("Löschen", f"Eintrag '{entry.description}' wirklich löschen?"):
                self.app.entry_service.delete(entry.id)
                self.app.refresh_current_page()

    def _mark_billed(self):
        entry = self._get_selected_entry()
        if not entry:
            return
        if entry.status in (EntryStatus.ABGERECHNET, EntryStatus.STORNIERT):
            messagebox.showinfo(
                "Nicht möglich",
                "Dieser Eintrag wurde bereits abgerechnet und kann nicht erneut abgerechnet werden.",
                parent=self.app.root,
            )
            return
        from datetime import date
        entry.status = EntryStatus.ABGERECHNET
        entry.date_billed = date.today()
        self.app.entry_service.update(entry)
        if (getattr(entry, "jaehrlich_wiederholen", False)
                and entry.entry_type == EntryType.UMSATZBONUS):
            self.app.entry_service.create_annual_followup(entry)
            messagebox.showinfo(
                "Wiederholeintrag erstellt",
                "Ein neuer Eintrag für das nächste Jahr wurde automatisch erstellt.",
                parent=self.app.root,
            )
        self.app.refresh_current_page()

    def _create_invoice(self):
        entries = self._get_selected_entries()
        if not entries:
            return

        # Filter out already-billed/storniert entries
        billable = [e for e in entries if e.status not in (EntryStatus.ABGERECHNET, EntryStatus.STORNIERT)]
        skipped = [e for e in entries if e not in billable]
        if skipped:
            names = "\n".join(f"  \u2022 {e.description} ({e.status.value})" for e in skipped)
            messagebox.showwarning(
                "Einige übersprungen",
                f"Folgende Einträge sind bereits abgerechnet/storniert und werden übersprungen:\n{names}",
                parent=self.app.root,
            )
        if not billable:
            return
        entries = billable

        from src.services.invoice_service import InvoiceService
        invoice_service = InvoiceService()

        needed = len(entries)
        avail = invoice_service.available_count()
        if avail < needed:
            messagebox.showerror(
                "Keine Rechnungsnummern",
                f"Nicht genug Rechnungsnummern verfügbar.\n\n"
                f"Verfügbar: {avail}   |   Benötigt: {needed}\n\n"
                "Bitte neue Nummern bei der Buchhaltung anfordern\n"
                "und im Admin-Bereich unter 'Rechnungsnummern' hinterlegen.",
                parent=self.app.root,
            )
            return

        if len(entries) == 1:
            entry = entries[0]
            supplier = self._resolve_supplier(entry)
            if not supplier:
                messagebox.showwarning(
                    "Lieferant nicht gefunden",
                    f"Kein Lieferant für '{entry.supplier_name}' gefunden."
                )
                return
            from src.ui.invoice_dialog import InvoiceDialog
            dlg = InvoiceDialog(self.app.root, entry, supplier, self.app.supplier_service,
                                invoice_service, entry_service=self.app.entry_service)
            self.app.root.wait_window(dlg.dialog)
            self.app.refresh_current_page()
        else:
            # Build (entry, supplier) pairs, warn about unresolvable ones
            pairs = []
            missing = []
            for entry in entries:
                supplier = self._resolve_supplier(entry)
                if supplier:
                    pairs.append((entry, supplier))
                else:
                    missing.append(entry.supplier_name)

            if missing:
                messagebox.showwarning(
                    "Lieferanten nicht gefunden",
                    "Folgende Lieferanten konnten nicht gefunden werden und werden übersprungen:\n"
                    + "\n".join(f"  • {n}" for n in missing)
                )
            if not pairs:
                return

            from src.ui.invoice_dialog import BulkInvoiceDialog
            dlg = BulkInvoiceDialog(self.app.root, pairs, invoice_service,
                                    entry_service=self.app.entry_service)
            self.app.root.wait_window(dlg.dialog)
            self.app.refresh_current_page()

    def _create_storno(self):
        entry = self._get_selected_entry()
        if not entry:
            return
        if entry.status != EntryStatus.ABGERECHNET or not entry.invoice_number:
            messagebox.showinfo(
                "Nicht möglich",
                "Storno ist nur für abgerechnete Einträge mit einer Rechnungsnummer möglich.",
                parent=self.app.root
            )
            return
        supplier = self._resolve_supplier(entry)
        if not supplier:
            messagebox.showwarning("Lieferant nicht gefunden",
                                   f"Kein Lieferant für '{entry.supplier_name}' gefunden.")
            return
        from src.services.invoice_service import InvoiceService
        from src.ui.invoice_dialog import StornoDialog
        dlg = StornoDialog(self.app.root, entry, supplier, self.app.entry_service, InvoiceService())
        self.app.root.wait_window(dlg.dialog)
        self.app.refresh_current_page()

    def _adjust_invoice(self):
        entry = self._get_selected_entry()
        if not entry:
            return
        if entry.status != EntryStatus.ABGERECHNET or not entry.invoice_number:
            messagebox.showinfo(
                "Nicht möglich",
                "Anpassen ist nur für abgerechnete Einträge mit einer Rechnungsnummer möglich.",
                parent=self.app.root
            )
            return
        supplier = self._resolve_supplier(entry)
        if not supplier:
            messagebox.showwarning("Lieferant nicht gefunden",
                                   f"Kein Lieferant für '{entry.supplier_name}' gefunden.")
            return
        from src.services.invoice_service import InvoiceService
        from src.ui.invoice_dialog import AdjustInvoiceDialog
        dlg = AdjustInvoiceDialog(self.app.root, entry, supplier, self.app.entry_service, InvoiceService())
        self.app.root.wait_window(dlg.dialog)
        self.app.refresh_current_page()

    def show(self):
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.refresh()

    def hide(self):
        self.frame.pack_forget()
