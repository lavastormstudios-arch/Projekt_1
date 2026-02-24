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
        self._build()
        if entry:
            self._populate(entry)
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
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=3)
        if var_type == "bool":
            v = tk.BooleanVar()
            self._vars[key] = v
            cb = ttk.Checkbutton(parent, variable=v, command=self._update_preview)
            cb.grid(row=row, column=1, sticky=tk.W, padx=8)
        else:
            v = tk.StringVar()
            self._vars[key] = v
            e = ttk.Entry(parent, textvariable=v, width=width)
            e.grid(row=row, column=1, sticky=tk.W, padx=8, pady=3)
            v.trace_add("write", lambda *_: self._update_preview())
            if show_pct:
                ttk.Label(parent, text="%").grid(row=row, column=2, sticky=tk.W)

    def _tab_artikel(self, nb):
        f = ttk.Frame(nb, padding=14)
        nb.add(f, text="Artikel-Info")

        # Artnr: special handling with lookup trigger
        ttk.Label(f, text="Artnr *").grid(row=0, column=0, sticky=tk.W, pady=3)
        artnr_var = tk.StringVar()
        self._vars["artnr"] = artnr_var
        artnr_entry = ttk.Entry(f, textvariable=artnr_var, width=32)
        artnr_entry.grid(row=0, column=1, sticky=tk.W, padx=8, pady=3)
        artnr_var.trace_add("write", lambda *_: self._update_preview())
        artnr_entry.bind("<FocusOut>", lambda _e: self._lookup_article())
        artnr_entry.bind("<Return>", lambda _e: self._lookup_article())

        self._lookup_status = tk.StringVar(value="")
        ttk.Label(f, textvariable=self._lookup_status,
                  font=("Segoe UI", 8), foreground="#2B7A0B").grid(
            row=0, column=2, sticky=tk.W, padx=4)

        # Remaining fields
        fields = [
            ("Bezeichnung *",   "bezeichnung"),
            ("Lieferant *",     "lieferant"),
            ("Warengruppe",     "warengruppe"),
            ("CM",              "cm"),
            ("Aktuelle ZTN",    "aktuelle_ztn"),
        ]
        for i, (lbl, key) in enumerate(fields, start=1):
            self._add_field(f, i, lbl, key, width=32)
        self._add_field(f, len(fields) + 1, "Archiv", "archiv", var_type="bool")

    def _tab_preise(self, nb):
        f = ttk.Frame(nb, padding=14)
        nb.add(f, text="Preise")
        fields = [
            ("Aktueller EK (€)",      "aktueller_ek"),
            ("Geplanter UVP inkl. MwSt. (€)", "geplanter_uvp"),
            ("Aktionspreis inkl. MwSt. (€)",  "aktionspreis"),
            ("EK FOB Dollar ($)",     "ek_fob_dollar"),
            ("EK FOB RMB (¥)",        "ek_fob_rmb"),
        ]
        for row, (lbl, key) in enumerate(fields):
            self._add_field(f, row, lbl, key)
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
        sv("geplanter_uvp", e.geplanter_uvp if e.geplanter_uvp else "")
        sv("aktionspreis", e.aktionspreis if e.aktionspreis else "")
        sv("ek_fob_dollar", e.ek_fob_dollar if e.ek_fob_dollar else "")
        sv("ek_fob_rmb", e.ek_fob_rmb if e.ek_fob_rmb else "")
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
        return FobEntry(
            id=entry_id,
            artnr=gs("artnr"),
            bezeichnung=gs("bezeichnung"),
            lieferant=gs("lieferant"),
            warengruppe=gs("warengruppe"),
            cm=gs("cm"),
            aktuelle_ztn=gs("aktuelle_ztn"),
            aktueller_ek=gf("aktueller_ek"),
            geplanter_uvp=gf("geplanter_uvp"),
            aktionspreis=gf("aktionspreis"),
            ek_fob_dollar=gf("ek_fob_dollar"),
            ek_fob_rmb=gf("ek_fob_rmb"),
            produktionszeit=gi("produktionszeit"),
            kubikmeter=gf("kubikmeter"),
            lcl=gb("lcl"),
            container_20=gi("container_20"),
            container_40hc=gi("container_40hc"),
            zollsatz=zollsatz,
            sonder_toolingkosten=gf("sonder_toolingkosten"),
            archiv=gb("archiv"),
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
                f"NEUER EK: {calc['neuer_ek']:.4f} €   "
                f"Marge UVP: {calc['marge_uvp']*100:.1f}%   "
                f"Marge Aktion: {calc['marge_aktion']*100:.1f}%",
            ]
            self._preview_text.set("\n".join(lines))
        except Exception:
            self._preview_text.set("")

    # ------------------------------------------------------------------
    # Article lookup / auto-fill
    # ------------------------------------------------------------------

    def _lookup_article(self):
        from src.services.article_service import ArticleService
        artnr = self._vars.get("artnr", tk.StringVar()).get().strip()
        if not artnr:
            self._lookup_status.set("")
            return

        article = ArticleService.lookup(artnr)
        if article is None:
            if ArticleService.is_loaded():
                self._lookup_status.set("Nicht in Artikelliste")
            else:
                self._lookup_status.set("")
            return

        # Auto-fill: only fill fields that are currently empty
        _str_fields = [
            ("bezeichnung",    "bezeichnung"),
            ("lieferant",      "lieferant"),
            ("warengruppe",    "warengruppe"),
            ("cm",             "cm"),
            ("aktuelle_ztn",   "aktuelle_ztn"),
        ]
        _float_fields = [
            ("aktueller_ek",   "aktueller_ek"),
            ("geplanter_uvp",  "geplanter_uvp"),
        ]

        filled = []
        for form_key, article_key in _str_fields:
            val = article.get(article_key, "")
            if val:
                v = self._vars.get(form_key)
                if v and not v.get().strip():
                    v.set(val)
                    filled.append(form_key)

        for form_key, article_key in _float_fields:
            val = article.get(article_key, "")
            if val:
                v = self._vars.get(form_key)
                if v and not v.get().strip():
                    v.set(val)
                    filled.append(form_key)

        bez = article.get("bezeichnung", artnr)
        self._lookup_status.set(f"✓ {bez}")
        self._update_preview()

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _save(self):
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

        entry = self._build_entry_from_form()

        if self._entry is None:
            self._svc.add(entry)
        else:
            self._svc.update(entry)

        self.dialog.destroy()
        if self._on_save:
            self._on_save()
