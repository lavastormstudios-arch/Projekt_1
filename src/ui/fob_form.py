import tkinter as tk
from tkinter import ttk, messagebox


class FobFormDialog:
    """Add / Edit dialog for a single FOB entry."""

    def __init__(self, parent, fob_service, entry=None, on_save=None):
        self._svc = fob_service
        self._entry = entry          # None → new
        self._on_save = on_save

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Neuer Artikel" if entry is None else "Artikel bearbeiten")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        w, h = 620, 700
        self.dialog.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
        self.dialog.geometry(f"{w}x{h}+{x}+{y}")

        self._vars: dict[str, tk.Variable] = {}
        self._master_data_widgets: dict[str, ttk.Entry] = {}
        self._build()

        if entry is None:
            from src.utils.constants import DUMMY_ARTNR
            self._vars["artnr"].set(DUMMY_ARTNR)
            self._lookup_article()
        else:
            self._populate(entry)
            self.dialog.after(10, self._lookup_article)

        self._update_preview()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self):
        main = ttk.Frame(self.dialog, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        nb = ttk.Notebook(main)
        nb.pack(fill=tk.BOTH, expand=True)

        self._tab_artikel(nb)
        self._tab_preise(nb)
        self._tab_logistik(nb)

        # Preview
        preview_frame = ttk.LabelFrame(main, text="Berechnungsvorschau", padding=8)
        preview_frame.pack(fill=tk.X, pady=(8, 0))
        self._preview_text = tk.StringVar(value="")
        ttk.Label(preview_frame, textvariable=self._preview_text,
                  font=("Segoe UI", 9), foreground="#2B3A52",
                  justify=tk.LEFT).pack(anchor=tk.W)

        # Buttons
        btn_row = ttk.Frame(main)
        btn_row.pack(pady=(10, 0))
        ttk.Button(btn_row, text="Speichern", command=self._save, width=12).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Abbrechen", command=self.dialog.destroy, width=12).pack(side=tk.LEFT, padx=4)

    def _add_field(self, parent, row, label, key, var_type="str", width=22, show_pct=False):
        """Add a form field and return the created widget (Entry or Checkbutton)."""
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=3)
        if var_type == "bool":
            v = tk.BooleanVar()
            self._vars[key] = v
            cb = ttk.Checkbutton(parent, variable=v, command=self._update_preview)
            cb.grid(row=row, column=1, sticky=tk.W, padx=8)
            return cb
        else:
            v = tk.StringVar()
            self._vars[key] = v
            e = ttk.Entry(parent, textvariable=v, width=width)
            e.grid(row=row, column=1, sticky=tk.W, padx=8, pady=3)
            v.trace_add("write", lambda *_: self._update_preview())
            if show_pct:
                ttk.Label(parent, text="%").grid(row=row, column=2, sticky=tk.W)
            return e

    def _tab_artikel(self, nb):
        f = ttk.Frame(nb, padding=14)
        nb.add(f, text="Artikel-Info")

        # Artnr: Combobox with autocomplete
        ttk.Label(f, text="Artnr *").grid(row=0, column=0, sticky=tk.W, pady=3)
        artnr_var = tk.StringVar()
        self._vars["artnr"] = artnr_var
        self._artnr_combo = ttk.Combobox(f, textvariable=artnr_var, width=30, state="normal")
        self._artnr_combo.grid(row=0, column=1, sticky=tk.W, padx=8, pady=3)
        artnr_var.trace_add("write", lambda *_: self._update_preview())
        self._artnr_combo.bind("<KeyRelease>", self._artnr_keyrelease)
        self._artnr_combo.bind("<FocusOut>", lambda _e: self._lookup_article())
        self._artnr_combo.bind("<Return>", lambda _e: self._lookup_article())
        self._artnr_combo.bind("<<ComboboxSelected>>", lambda _e: self._lookup_article())

        self._lookup_status = tk.StringVar(value="")
        self._lookup_status_label = ttk.Label(f, textvariable=self._lookup_status,
                                              font=("Segoe UI", 8), foreground="#2B7A0B")
        self._lookup_status_label.grid(row=0, column=2, sticky=tk.W, padx=4)

        # Master data fields (will be locked when a real article is found)
        master_fields = [
            ("Bezeichnung *",   "bezeichnung"),
            ("Lieferant *",     "lieferant"),
            ("Warengruppe",     "warengruppe"),
            ("CM",              "cm"),
            ("Aktuelle ZTN",    "aktuelle_ztn"),
        ]
        for i, (lbl, key) in enumerate(master_fields, start=1):
            widget = self._add_field(f, i, lbl, key, width=32)
            self._master_data_widgets[key] = widget

        self._add_field(f, len(master_fields) + 1, "Archiv", "archiv", var_type="bool")

    def _tab_preise(self, nb):
        f = ttk.Frame(nb, padding=14)
        nb.add(f, text="Preise")
        fields = [
            ("Aktueller EK (€)",      "aktueller_ek"),
            ("EK FOB Dollar ($)",     "ek_fob_dollar"),
            ("EK FOB RMB (¥)",        "ek_fob_rmb"),
            ("EK FOB Euro (€)",       "ek_fob_euro"),
        ]
        for row, (lbl, key) in enumerate(fields):
            widget = self._add_field(f, row, lbl, key)
            if key == "aktueller_ek":
                self._master_data_widgets[key] = widget

        # Mutual exclusivity: only one FOB price field may be filled
        _fob_fields = ("ek_fob_dollar", "ek_fob_rmb", "ek_fob_euro")
        self._fob_clearing = False

        def make_fob_handler(changed_key):
            def handler(*_):
                if self._fob_clearing:
                    return
                v = self._vars.get(changed_key)
                if v and v.get().strip():
                    self._fob_clearing = True
                    for other in _fob_fields:
                        if other != changed_key:
                            ov = self._vars.get(other)
                            if ov:
                                ov.set("")
                    self._fob_clearing = False
            return handler

        for key in _fob_fields:
            v = self._vars.get(key)
            if v:
                v.trace_add("write", make_fob_handler(key))

        self._add_field(f, len(fields), "Zollsatz (%)",
                        "zollsatz_pct", show_pct=False)
        ttk.Label(f, text="(z.B. 4.7 für 4,7%)", foreground="gray",
                  font=("Segoe UI", 8)).grid(row=len(fields), column=2, sticky=tk.W)
        self._add_field(f, len(fields)+1, "Sonder-/Toolingkosten (€)",
                        "sonder_toolingkosten")

    def _tab_logistik(self, nb):
        f = ttk.Frame(nb, padding=14)
        nb.add(f, text="Logistik")
        self._add_field(f, 0, "Produktionszeit (Tage)", "produktionszeit")
        self._add_field(f, 1, "LCL (Sammelcontainer)", "lcl", var_type="bool")
        self._add_field(f, 2, "Kubikmeter (nur LCL)", "kubikmeter")
        self._add_field(f, 3, 'Stück im 20"-Container', "container_20")
        self._add_field(f, 4, 'Stück im 40"HC-Container', "container_40hc")

    # ------------------------------------------------------------------
    # Populate
    # ------------------------------------------------------------------

    def _populate(self, e):
        def sv(key, val):
            v = self._vars.get(key)
            if v is None:
                return
            if isinstance(v, tk.BooleanVar):
                v.set(bool(val))
            else:
                v.set("" if val is None else str(val))

        sv("artnr", e.artnr)
        sv("bezeichnung", e.bezeichnung)
        sv("lieferant", e.lieferant)
        sv("warengruppe", e.warengruppe)
        sv("cm", e.cm)
        sv("aktuelle_ztn", e.aktuelle_ztn)
        sv("archiv", e.archiv)
        sv("aktueller_ek", e.aktueller_ek if e.aktueller_ek else "")
        sv("ek_fob_dollar", e.ek_fob_dollar if e.ek_fob_dollar else "")
        sv("ek_fob_rmb", e.ek_fob_rmb if e.ek_fob_rmb else "")
        sv("ek_fob_euro", e.ek_fob_euro if e.ek_fob_euro else "")
        # zollsatz stored as fraction (e.g. 0.047), display as percent (4.7)
        sv("zollsatz_pct", f"{e.zollsatz * 100:.4g}" if e.zollsatz else "")
        sv("sonder_toolingkosten", e.sonder_toolingkosten if e.sonder_toolingkosten else "")
        sv("produktionszeit", e.produktionszeit if e.produktionszeit else "")
        sv("lcl", e.lcl)
        sv("kubikmeter", e.kubikmeter if e.kubikmeter else "")
        sv("container_20", e.container_20 if e.container_20 else "")
        sv("container_40hc", e.container_40hc if e.container_40hc else "")

    # ------------------------------------------------------------------
    # Live preview
    # ------------------------------------------------------------------

    def _build_entry_from_form(self):
        from src.models.fob_entry import FobEntry
        from src.utils.date_helpers import safe_float, safe_int

        def gs(key, default=""):
            v = self._vars.get(key)
            if v is None:
                return default
            return v.get()

        def gf(key):
            return safe_float(gs(key))

        def gi(key):
            return safe_int(gs(key))

        def gb(key):
            v = self._vars.get(key)
            return bool(v.get()) if v else False

        # zollsatz: form stores percent, model stores fraction
        zollsatz_pct = safe_float(gs("zollsatz_pct"))
        zollsatz = zollsatz_pct / 100.0

        entry_id = self._entry.id if self._entry else ""
        # Preserve price_history when editing an existing entry
        existing_history = self._entry.price_history if self._entry else ""
        return FobEntry(
            id=entry_id,
            artnr=gs("artnr"),
            bezeichnung=gs("bezeichnung"),
            lieferant=gs("lieferant"),
            warengruppe=gs("warengruppe"),
            cm=gs("cm"),
            aktuelle_ztn=gs("aktuelle_ztn"),
            aktueller_ek=gf("aktueller_ek"),
            ek_fob_dollar=gf("ek_fob_dollar"),
            ek_fob_rmb=gf("ek_fob_rmb"),
            ek_fob_euro=gf("ek_fob_euro"),
            produktionszeit=gi("produktionszeit"),
            kubikmeter=gf("kubikmeter"),
            lcl=gb("lcl"),
            container_20=gi("container_20"),
            container_40hc=gi("container_40hc"),
            zollsatz=zollsatz,
            sonder_toolingkosten=gf("sonder_toolingkosten"),
            archiv=gb("archiv"),
            price_history=existing_history,
        )

    def _update_preview(self):
        try:
            temp = self._build_entry_from_form()
            calc = self._svc.calculate(temp)
            lines = [
                f"EK in €: {calc['ek_in_eur']:.4f}   "
                f"Finanzierung: {calc['finanzierungskosten']:.4f}   "
                f"Fracht: {calc['frachtkosten']:.4f}",
                f"Rekla: {calc['reklakosten']:.4f}   "
                f"Kubik: {calc['kubikkosten']:.4f}   "
                f"Zoll: {calc['zollkosten']:.4f}",
                f"NEUER EK: {calc['neuer_ek']:.4f} €",
            ]
            self._preview_text.set("\n".join(lines))
        except Exception:
            self._preview_text.set("")

    # ------------------------------------------------------------------
    # Article lookup / auto-fill
    # ------------------------------------------------------------------

    def _lock_master_fields(self):
        for w in self._master_data_widgets.values():
            w.config(state="disabled")

    def _unlock_master_fields(self):
        for w in self._master_data_widgets.values():
            w.config(state="normal")

    def _artnr_keyrelease(self, event=None):
        from src.services.article_service import ArticleService
        typed = self._vars["artnr"].get().strip().upper()
        if not typed or not ArticleService.is_loaded():
            self._artnr_combo["values"] = []
            return
        all_artnrs = sorted(ArticleService._cache.keys())
        matches = [a for a in all_artnrs if a.upper().startswith(typed)][:50]
        self._artnr_combo["values"] = matches
        if matches:
            try:
                self._artnr_combo.event_generate("<Down>")
            except Exception:
                pass

    def _lookup_article(self):
        from src.services.article_service import ArticleService
        from src.utils.constants import DUMMY_ARTNR

        artnr = self._vars.get("artnr", tk.StringVar()).get().strip()

        # Empty field → reset everything
        if not artnr:
            self._lookup_status.set("")
            self._lookup_status_label.config(foreground="#888888")
            self._unlock_master_fields()
            return

        # Dummy artnr → all fields freely editable
        if artnr.upper() == DUMMY_ARTNR.upper():
            self._lookup_status.set("Dummy – alle Felder editierbar")
            self._lookup_status_label.config(foreground="#888888")
            self._unlock_master_fields()
            return

        # No ArticleService loaded → no validation
        if not ArticleService.is_loaded():
            self._lookup_status.set("")
            return

        article = ArticleService.lookup(artnr)
        if article is None:
            self._lookup_status.set("✗ Nicht gefunden")
            self._lookup_status_label.config(foreground="#CC0000")
            self._unlock_master_fields()
            return

        # Article found: fill fields (always overwrite) + lock
        self._unlock_master_fields()
        _str_fields = ["bezeichnung", "lieferant", "warengruppe", "cm", "aktuelle_ztn"]
        _float_fields = ["aktueller_ek"]
        for key in _str_fields:
            val = article.get(key, "")
            if val:
                self._vars[key].set(val)
        for key in _float_fields:
            val = article.get(key, "")
            if val:
                self._vars[key].set(val)
        self._lock_master_fields()
        bez = article.get("bezeichnung", artnr)
        self._lookup_status.set(f"✓ {bez}")
        self._lookup_status_label.config(foreground="#2B7A0B")
        self._update_preview()

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _save(self):
        from src.services.article_service import ArticleService
        from src.utils.constants import DUMMY_ARTNR

        artnr = self._vars.get("artnr", tk.StringVar()).get().strip()
        bezeichnung = self._vars.get("bezeichnung", tk.StringVar()).get().strip()
        lieferant = self._vars.get("lieferant", tk.StringVar()).get().strip()
        if not artnr:
            messagebox.showwarning("Pflichtfeld", "Artnr darf nicht leer sein.",
                                   parent=self.dialog)
            return
        if not bezeichnung:
            messagebox.showwarning("Pflichtfeld", "Bezeichnung darf nicht leer sein.",
                                   parent=self.dialog)
            return
        if not lieferant:
            messagebox.showwarning("Pflichtfeld", "Lieferant darf nicht leer sein.",
                                   parent=self.dialog)
            return

        # Validate: duplicate artnr (except DUMMY_ARTNR, which may appear multiple times)
        if artnr.upper() != DUMMY_ARTNR.upper():
            exclude_id = self._entry.id if self._entry else ""
            if self._svc.artnr_exists(artnr, exclude_id=exclude_id):
                messagebox.showwarning(
                    "Artikelnummer bereits vorhanden",
                    f"Die Artikelnummer '{artnr}' ist bereits in der FOB-Kalkulation eingetragen.\n"
                    "Jede Artikelnummer darf nur einmal verwendet werden.",
                    parent=self.dialog)
                return

        # Validate: unknown artnr (only when ArticleService is loaded and not dummy)
        if (artnr.upper() != DUMMY_ARTNR.upper()
                and ArticleService.is_loaded()
                and ArticleService.lookup(artnr) is None):
            messagebox.showwarning(
                "Ungültige Artikelnummer",
                f"'{artnr}' wurde nicht in der Artikelliste gefunden.\n"
                "Bitte eine gültige Artikelnummer eingeben oder "
                f"'{DUMMY_ARTNR}' für eine freie Kalkulation verwenden.",
                parent=self.dialog)
            return

        entry = self._build_entry_from_form()

        if self._entry is None:
            self._svc.add(entry)
        else:
            self._svc.update(entry)

        self.dialog.destroy()
        if self._on_save:
            self._on_save()
