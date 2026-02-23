import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from src.models.base_entry import Entry
from src.models.enums import EntryType, EntryStatus
from src.utils.date_helpers import parse_date, format_date


class EntryFormDialog:
    def __init__(self, parent, app, entry: Optional[Entry] = None, default_type: Optional[str] = None):
        self.app = app
        self.entry = entry
        self.is_edit = entry is not None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Eintrag bearbeiten" if self.is_edit else "Neuer Eintrag")
        self.dialog.geometry("550x700")
        self.dialog.resizable(False, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._vars = {}
        self._type_specific_widgets = []
        self._kickback_rows = []   # list of (frame, art_var, amount_var)
        self._ub_rows = []         # list of (frame, threshold_var, percentage_var)
        self._build(default_type)

        if self.is_edit:
            self._populate()

    def _build(self, default_type):
        canvas = tk.Canvas(self.dialog)
        scrollbar = ttk.Scrollbar(self.dialog, orient=tk.VERTICAL, command=canvas.yview)
        self.form_frame = ttk.Frame(canvas)

        self.form_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.form_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        row = 0
        f = self.form_frame

        # Entry Type
        ttk.Label(f, text="Typ:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self._vars["entry_type"] = tk.StringVar(value=default_type or EntryType.WKZ.value)
        type_combo = ttk.Combobox(f, textvariable=self._vars["entry_type"], width=25, state="readonly",
                                  values=[t.value for t in EntryType])
        type_combo.grid(row=row, column=1, padx=10, pady=5, sticky=tk.W)
        type_combo.bind("<<ComboboxSelected>>", lambda e: self._toggle_type_fields())
        row += 1

        # Supplier
        ttk.Label(f, text="Lieferant:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self._vars["supplier_name"] = tk.StringVar()
        supplier_names = self.app.supplier_service.get_names()
        self.supplier_combo = ttk.Combobox(f, textvariable=self._vars["supplier_name"], width=25,
                                           values=supplier_names)
        self.supplier_combo.grid(row=row, column=1, padx=10, pady=5, sticky=tk.W)
        row += 1

        # Description
        ttk.Label(f, text="Beschreibung:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self._vars["description"] = tk.StringVar()
        ttk.Entry(f, textvariable=self._vars["description"], width=30).grid(
            row=row, column=1, padx=10, pady=5, sticky=tk.W)
        row += 1

        # Status
        ttk.Label(f, text="Status:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self._vars["status"] = tk.StringVar(value=EntryStatus.OFFEN.value)
        ttk.Combobox(f, textvariable=self._vars["status"], width=25, state="readonly",
                     values=[s.value for s in EntryStatus]).grid(
            row=row, column=1, padx=10, pady=5, sticky=tk.W)
        row += 1

        # Amount
        ttk.Label(f, text="Betrag (erwartet):").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self._vars["amount"] = tk.StringVar(value="0.00")
        self._amount_entry = ttk.Entry(f, textvariable=self._vars["amount"], width=15)
        self._amount_entry.grid(row=row, column=1, padx=10, pady=5, sticky=tk.W)
        row += 1

        ttk.Label(f, text="Betrag (abgerechnet):").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self._vars["amount_billed"] = tk.StringVar(value="0.00")
        ttk.Entry(f, textvariable=self._vars["amount_billed"], width=15).grid(
            row=row, column=1, padx=10, pady=5, sticky=tk.W)
        row += 1

        # Dates
        for field, label in [("date_start", "Beginn (JJJJ-MM-TT):"),
                             ("date_end", "Ende (JJJJ-MM-TT):"),
                             ("billing_deadline", "Abrechnungsfrist (JJJJ-MM-TT):"),
                             ("date_billed", "Abgerechnet am (JJJJ-MM-TT):")]:
            ttk.Label(f, text=label).grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
            self._vars[field] = tk.StringVar()
            ttk.Entry(f, textvariable=self._vars[field], width=15).grid(
                row=row, column=1, padx=10, pady=5, sticky=tk.W)
            row += 1

        # Type-specific fields
        self._type_rows_start = row

        # Kickback fields - dynamic article list
        self._kb_frame_label = ttk.Label(f, text="Kickback-Artikel:", font=("Segoe UI", 10, "bold"))
        self._kb_container = ttk.Frame(f)
        self._kb_articles_frame = ttk.Frame(self._kb_container)
        self._kb_articles_frame.pack(fill=tk.X)
        self._kb_add_btn = ttk.Button(self._kb_container, text="+ Artikel hinzufügen",
                                       command=self._add_kickback_row)
        self._kb_add_btn.pack(anchor=tk.W, pady=(5, 0))
        self._kb_row = row
        row += 1

        # Umsatzbonus fields - dynamic tier list
        self._ub_frame_label = ttk.Label(f, text="Umsatzbonus-Staffeln:", font=("Segoe UI", 10, "bold"))
        self._ub_container = ttk.Frame(f)
        self._ub_staffeln_frame = ttk.Frame(self._ub_container)
        self._ub_staffeln_frame.pack(fill=tk.X)
        self._ub_add_btn = ttk.Button(self._ub_container, text="+ Staffel hinzufügen",
                                       command=self._add_umsatzbonus_row)
        self._ub_add_btn.pack(anchor=tk.W, pady=(5, 0))
        self._ub_row = row
        row += 1

        # WKZ-specific fields
        self._wkz_widgets = []

        # WKZ Category
        wkz_cat_lbl = ttk.Label(f, text="WKZ Kategorie:")
        self._vars["wkz_category"] = tk.StringVar()
        wkz_cat_combo = ttk.Combobox(f, textvariable=self._vars["wkz_category"], width=25, state="readonly",
                                      values=["Hauptkatalog", "Newsletter", "Bannerwerbung", "Flyer"])
        self._wkz_cat_row = row
        self._wkz_widgets.append((wkz_cat_lbl, wkz_cat_combo, row))
        row += 1

        # WKZ Percentage toggle
        wkz_pct_lbl = ttk.Label(f, text="Berechnungsart:")
        self._vars["wkz_is_percentage"] = tk.BooleanVar(value=False)
        wkz_pct_frame = ttk.Frame(f)
        self._wkz_rb_fixed = ttk.Radiobutton(wkz_pct_frame, text="Festbetrag",
                                               variable=self._vars["wkz_is_percentage"],
                                               value=False, command=self._toggle_wkz_percentage)
        self._wkz_rb_fixed.pack(side=tk.LEFT, padx=(0, 10))
        self._wkz_rb_percent = ttk.Radiobutton(wkz_pct_frame, text="Prozentual",
                                                 variable=self._vars["wkz_is_percentage"],
                                                 value=True, command=self._toggle_wkz_percentage)
        self._wkz_rb_percent.pack(side=tk.LEFT)
        self._wkz_widgets.append((wkz_pct_lbl, wkz_pct_frame, row))
        row += 1

        # WKZ Percentage value
        wkz_pctval_lbl = ttk.Label(f, text="Prozentsatz (%):")
        self._vars["wkz_percentage"] = tk.StringVar(value="0.0")
        wkz_pctval_entry = ttk.Entry(f, textvariable=self._vars["wkz_percentage"], width=10)
        self._wkz_pctval_row = row
        self._wkz_pctval_widgets = (wkz_pctval_lbl, wkz_pctval_entry, row)
        self._wkz_widgets.append(self._wkz_pctval_widgets)
        row += 1

        # Notes
        ttk.Label(f, text="Notizen:").grid(row=row, column=0, sticky=tk.NW, padx=10, pady=5)
        self.notes_text = tk.Text(f, width=30, height=4)
        self.notes_text.grid(row=row, column=1, padx=10, pady=5, sticky=tk.W)
        row += 1

        # Buttons
        btn_frame = ttk.Frame(f)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="Speichern", command=self._save).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Abbrechen", command=self.dialog.destroy).pack(side=tk.LEFT, padx=10)

        self._toggle_type_fields()

    def _add_kickback_row(self, article_number="", kickback_amount=""):
        row_frame = ttk.Frame(self._kb_articles_frame)
        row_frame.pack(fill=tk.X, pady=2)

        art_var = tk.StringVar(value=article_number)
        amt_var = tk.StringVar(value=str(kickback_amount) if kickback_amount else "")

        ttk.Label(row_frame, text="Art.-Nr.:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(row_frame, textvariable=art_var, width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(row_frame, text="Betrag:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(row_frame, textvariable=amt_var, width=10).pack(side=tk.LEFT, padx=(0, 5))

        def remove():
            row_frame.destroy()
            self._kickback_rows = [(f, a, b) for f, a, b in self._kickback_rows if f.winfo_exists()]

        ttk.Button(row_frame, text="X", width=3, command=remove).pack(side=tk.LEFT)

        self._kickback_rows.append((row_frame, art_var, amt_var))

    def _add_umsatzbonus_row(self, revenue_threshold="", bonus_percentage=""):
        row_frame = ttk.Frame(self._ub_staffeln_frame)
        row_frame.pack(fill=tk.X, pady=2)

        thr_var = tk.StringVar(value=str(revenue_threshold) if revenue_threshold else "")
        pct_var = tk.StringVar(value=str(bonus_percentage) if bonus_percentage else "")

        ttk.Label(row_frame, text="Schwelle:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(row_frame, textvariable=thr_var, width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(row_frame, text="Bonus %:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(row_frame, textvariable=pct_var, width=8).pack(side=tk.LEFT, padx=(0, 5))

        def remove():
            row_frame.destroy()
            self._ub_rows = [(f, a, b) for f, a, b in self._ub_rows if f.winfo_exists()]

        ttk.Button(row_frame, text="X", width=3, command=remove).pack(side=tk.LEFT)

        self._ub_rows.append((row_frame, thr_var, pct_var))

    def _toggle_wkz_percentage(self):
        is_pct = self._vars["wkz_is_percentage"].get()
        lbl, ent, r = self._wkz_pctval_widgets
        if is_pct:
            lbl.grid(row=r, column=0, sticky=tk.W, padx=10, pady=5)
            ent.grid(row=r, column=1, padx=10, pady=5, sticky=tk.W)
        else:
            lbl.grid_remove()
            ent.grid_remove()

    def _toggle_type_fields(self):
        entry_type = self._vars["entry_type"].get()

        # Hide all type-specific
        self._kb_frame_label.grid_remove()
        self._kb_container.grid_remove()
        self._ub_frame_label.grid_remove()
        self._ub_container.grid_remove()
        for lbl, widget, r in self._wkz_widgets:
            lbl.grid_remove()
            widget.grid_remove()

        # Show relevant
        if entry_type == EntryType.WKZ.value:
            self._amount_entry.config(state="normal")
            for lbl, widget, r in self._wkz_widgets:
                lbl.grid(row=r, column=0, sticky=tk.W, padx=10, pady=5)
                widget.grid(row=r, column=1, padx=10, pady=5, sticky=tk.W)
            self._toggle_wkz_percentage()
        elif entry_type == EntryType.KICKBACK.value:
            self._kb_frame_label.grid(row=self._kb_row, column=0, sticky=tk.NW, padx=10, pady=5)
            self._kb_container.grid(row=self._kb_row, column=1, padx=10, pady=5, sticky=tk.W)
            # Make amount field read-only for kickback (auto-calculated)
            self._amount_entry.config(state="readonly")
            if not self._kickback_rows:
                self._add_kickback_row()
        elif entry_type == EntryType.UMSATZBONUS.value:
            self._ub_frame_label.grid(row=self._ub_row, column=0, sticky=tk.NW, padx=10, pady=5)
            self._ub_container.grid(row=self._ub_row, column=1, padx=10, pady=5, sticky=tk.W)
            self._amount_entry.config(state="normal")
            if not self._ub_rows:
                self._add_umsatzbonus_row()
        else:
            self._amount_entry.config(state="normal")

    def _populate(self):
        e = self.entry
        self._vars["entry_type"].set(e.entry_type.value)
        self._vars["supplier_name"].set(e.supplier_name)
        self._vars["description"].set(e.description)
        self._vars["status"].set(e.status.value)
        self._vars["amount"].set(str(e.amount))
        self._vars["amount_billed"].set(str(e.amount_billed))
        self._vars["date_start"].set(format_date(e.date_start))
        self._vars["date_end"].set(format_date(e.date_end))
        self._vars["billing_deadline"].set(format_date(e.billing_deadline))
        self._vars["date_billed"].set(format_date(e.date_billed))
        self._vars["wkz_is_percentage"].set(e.wkz_is_percentage)
        self._vars["wkz_percentage"].set(str(e.wkz_percentage))
        self._vars["wkz_category"].set(e.wkz_category)
        self.notes_text.insert("1.0", e.notes)

        # Populate kickback articles
        if e.entry_type == EntryType.KICKBACK:
            articles = e.get_kickback_articles()
            for art in articles:
                self._add_kickback_row(
                    article_number=art.get("article_number", ""),
                    kickback_amount=art.get("kickback_amount", "")
                )

        # Populate umsatzbonus tiers
        if e.entry_type == EntryType.UMSATZBONUS:
            staffeln = e.get_umsatzbonus_staffeln()
            for s in staffeln:
                self._add_umsatzbonus_row(
                    revenue_threshold=s.get("revenue_threshold", ""),
                    bonus_percentage=s.get("bonus_percentage", "")
                )

        self._toggle_type_fields()

    def _save(self):
        supplier_name = self._vars["supplier_name"].get().strip()
        if not supplier_name:
            messagebox.showwarning("Fehler", "Bitte einen Lieferanten angeben.")
            return

        # Find or note supplier
        supplier = self.app.supplier_service.get_by_name(supplier_name)
        supplier_id = supplier.id if supplier else ""

        entry_type = EntryType(self._vars["entry_type"].get())

        # For kickback: calculate amount from articles
        kickback_articles = []
        umsatzbonus_staffeln = []

        if entry_type == EntryType.KICKBACK:
            total_kickback = 0.0
            for row_frame, art_var, amt_var in self._kickback_rows:
                if not row_frame.winfo_exists():
                    continue
                art_num = art_var.get().strip()
                try:
                    kb_amount = float(amt_var.get() or 0)
                except ValueError:
                    kb_amount = 0.0
                if art_num or kb_amount:
                    kickback_articles.append({"article_number": art_num, "kickback_amount": kb_amount})
                    total_kickback += kb_amount
            amount = total_kickback
        elif entry_type == EntryType.UMSATZBONUS:
            for row_frame, thr_var, pct_var in self._ub_rows:
                if not row_frame.winfo_exists():
                    continue
                try:
                    threshold = float(thr_var.get() or 0)
                except ValueError:
                    threshold = 0.0
                try:
                    percentage = float(pct_var.get() or 0)
                except ValueError:
                    percentage = 0.0
                if threshold or percentage:
                    umsatzbonus_staffeln.append({"revenue_threshold": threshold, "bonus_percentage": percentage})
            try:
                amount = float(self._vars["amount"].get() or 0)
            except ValueError:
                messagebox.showwarning("Fehler", "Ungültiger Betrag.")
                return
        else:
            try:
                amount = float(self._vars["amount"].get() or 0)
            except ValueError:
                messagebox.showwarning("Fehler", "Ungültiger Betrag.")
                return

        try:
            amount_billed = float(self._vars["amount_billed"].get() or 0)
        except ValueError:
            messagebox.showwarning("Fehler", "Ungültiger abgerechneter Betrag.")
            return

        if self.is_edit:
            entry = self.entry
        else:
            entry = Entry(
                entry_type=entry_type,
                supplier_id=supplier_id,
                supplier_name=supplier_name,
            )

        entry.entry_type = entry_type
        entry.supplier_id = supplier_id
        entry.supplier_name = supplier_name
        entry.description = self._vars["description"].get()
        entry.status = EntryStatus(self._vars["status"].get())
        entry.amount = amount
        entry.amount_billed = amount_billed
        entry.date_start = parse_date(self._vars["date_start"].get())
        entry.date_end = parse_date(self._vars["date_end"].get())
        entry.billing_deadline = parse_date(self._vars["billing_deadline"].get())
        entry.date_billed = parse_date(self._vars["date_billed"].get())
        entry.set_kickback_articles(kickback_articles)
        entry.set_umsatzbonus_staffeln(umsatzbonus_staffeln)
        entry.wkz_is_percentage = self._vars["wkz_is_percentage"].get()
        try:
            entry.wkz_percentage = float(self._vars["wkz_percentage"].get() or 0)
        except ValueError:
            entry.wkz_percentage = 0.0
        entry.wkz_category = self._vars["wkz_category"].get()
        entry.notes = self.notes_text.get("1.0", tk.END).strip()

        if self.is_edit:
            self.app.entry_service.update(entry)
        else:
            self.app.entry_service.add(entry)

        self.dialog.destroy()
        self.app.refresh_current_page()
