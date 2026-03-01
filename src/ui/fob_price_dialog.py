import tkinter as tk
from tkinter import ttk, messagebox


class FobPriceDialog(tk.Toplevel):
    """Dialog for entering new FOB prices and viewing the full price history."""

    def __init__(self, parent, entry, fob_service, on_save=None):
        super().__init__(parent)
        self.entry = entry
        self._svc = fob_service
        self._on_save = on_save

        self.title(f"Neuer Preis – {entry.artnr} {entry.bezeichnung}")
        self.resizable(True, True)
        self.minsize(640, 440)
        self.grab_set()

        self._build()
        self._load_history()
        self._update_preview()

        # Centre over parent
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{px}+{py}")

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        # ── History Treeview ──────────────────────────────────────────
        hist_frame = ttk.LabelFrame(main, text="Preishistorie", padding=5)
        hist_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        hist_frame.columnconfigure(0, weight=1)
        hist_frame.rowconfigure(0, weight=1)

        cols = ("date", "fob_dollar", "fob_rmb", "fob_euro", "neuer_ek", "notiz")
        self._hist_tree = ttk.Treeview(hist_frame, columns=cols, show="headings",
                                       height=6, selectmode="none")
        headers = [
            ("date",       "Datum",      90),
            ("fob_dollar", "FOB $",      75),
            ("fob_rmb",    "FOB ¥",      75),
            ("fob_euro",   "FOB €",      75),
            ("neuer_ek",   "NEUER EK",   90),
            ("notiz",      "Notiz",     200),
        ]
        for col_id, label, width in headers:
            self._hist_tree.heading(col_id, text=label)
            self._hist_tree.column(col_id, width=width, minwidth=40,
                                   anchor=tk.W if col_id in ("date", "notiz") else tk.E)

        vsb = ttk.Scrollbar(hist_frame, orient="vertical",
                            command=self._hist_tree.yview)
        self._hist_tree.configure(yscrollcommand=vsb.set)
        self._hist_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # ── New-price entry form ──────────────────────────────────────
        form_frame = ttk.LabelFrame(main, text="Neue Preise erfassen", padding=8)
        form_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        # Helpers
        def lbl(text, r, c, **kw):
            ttk.Label(form_frame, text=text).grid(row=r, column=c,
                                                   sticky=tk.W, padx=(0, 6), pady=3, **kw)

        def entry_var(default=""):
            var = tk.StringVar(value=default)
            return var

        def fmt(v):
            return f"{float(v):.2f}" if v else ""

        # FOB Dollar
        lbl("FOB Dollar ($):", 0, 0)
        self._dollar_var = entry_var(fmt(self.entry.ek_fob_dollar))
        dollar_e = ttk.Entry(form_frame, textvariable=self._dollar_var, width=14)
        dollar_e.grid(row=0, column=1, sticky=tk.W, pady=3)
        dollar_e.bind("<KeyRelease>", lambda _: self._update_preview())

        # FOB RMB
        lbl("FOB RMB (¥):", 0, 2)
        self._rmb_var = entry_var(fmt(self.entry.ek_fob_rmb))
        rmb_e = ttk.Entry(form_frame, textvariable=self._rmb_var, width=14)
        rmb_e.grid(row=0, column=3, sticky=tk.W, pady=3)
        rmb_e.bind("<KeyRelease>", lambda _: self._update_preview())

        # FOB Euro
        lbl("FOB Euro (€):", 1, 0)
        self._euro_var = entry_var(fmt(self.entry.ek_fob_euro))
        euro_e = ttk.Entry(form_frame, textvariable=self._euro_var, width=14)
        euro_e.grid(row=1, column=1, sticky=tk.W, pady=3)
        euro_e.bind("<KeyRelease>", lambda _: self._update_preview())

        # Notiz
        lbl("Notiz:", 1, 2)
        self._notiz_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self._notiz_var, width=28).grid(
            row=1, column=3, sticky=tk.EW, pady=3)
        form_frame.columnconfigure(3, weight=1)

        # Live preview label
        self._preview_var = tk.StringVar()
        preview_lbl = ttk.Label(form_frame, textvariable=self._preview_var,
                                font=("", 10, "bold"), foreground="#1a6e1a")
        preview_lbl.grid(row=2, column=0, columnspan=4, sticky=tk.W, pady=(6, 0))

        # ── Buttons ───────────────────────────────────────────────────
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=2, column=0, sticky=tk.E)
        ttk.Button(btn_frame, text="Speichern", command=self._save).pack(
            side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Abbrechen", command=self.destroy).pack(
            side=tk.LEFT)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def _load_history(self):
        self._hist_tree.delete(*self._hist_tree.get_children())
        history = self.entry.get_price_history()
        for snap in history:
            raw_date = snap.get("date", "")
            # Format date as DD.MM.YYYY if ISO format
            try:
                from datetime import date as _date
                parts = raw_date.split("-")
                if len(parts) == 3:
                    raw_date = f"{parts[2]}.{parts[1]}.{parts[0]}"
            except Exception:
                pass

            def _fmt(v):
                try:
                    f = float(v)
                    return f"{f:.2f}" if f else "—"
                except (TypeError, ValueError):
                    return "—"

            self._hist_tree.insert("", tk.END, values=(
                raw_date,
                _fmt(snap.get("ek_fob_dollar")),
                _fmt(snap.get("ek_fob_rmb")),
                _fmt(snap.get("ek_fob_euro")),
                f"{float(snap.get('neuer_ek', 0)):.2f} €",
                snap.get("notiz", ""),
            ))

        if not history:
            self._hist_tree.insert("", tk.END, values=(
                "—", "—", "—", "—", "—", "Noch keine Historieneinträge",
            ))

    # ------------------------------------------------------------------
    # Live preview
    # ------------------------------------------------------------------

    def _parse_price_inputs(self):
        def _f(var):
            try:
                v = var.get().replace(",", ".")
                return float(v) if v.strip() else 0.0
            except ValueError:
                return 0.0

        return {
            "ek_fob_dollar": _f(self._dollar_var),
            "ek_fob_rmb":    _f(self._rmb_var),
            "ek_fob_euro":   _f(self._euro_var),
        }

    def _update_preview(self):
        from copy import copy
        prices = self._parse_price_inputs()
        # Build a temporary entry with new prices for calculation
        tmp = copy(self.entry)
        tmp.ek_fob_dollar = prices["ek_fob_dollar"]
        tmp.ek_fob_rmb    = prices["ek_fob_rmb"]
        tmp.ek_fob_euro   = prices["ek_fob_euro"]
        try:
            new_calc = self._svc.calculate(tmp)
            new_ek   = new_calc["neuer_ek"]
            old_calc = self._svc.calculate(self.entry)
            old_ek   = old_calc["neuer_ek"]
            diff     = new_ek - old_ek
            sign     = "+" if diff >= 0 else ""
            self._preview_var.set(
                f"NEUER EK → {new_ek:.2f} €   ({sign}{diff:.2f} € gegenüber aktuellem Wert)"
            )
        except Exception:
            self._preview_var.set("")

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _save(self):
        prices = self._parse_price_inputs()
        notiz  = self._notiz_var.get().strip()

        if not any(v > 0 for v in prices.values()):
            messagebox.showwarning(
                "Hinweis",
                "Bitte mindestens einen FOB-Preis eingeben.",
                parent=self,
            )
            return

        try:
            self._svc.update_prices(self.entry.id, prices, notiz=notiz)
        except Exception as exc:
            messagebox.showerror("Fehler", str(exc), parent=self)
            return

        if self._on_save:
            self._on_save()
        self.destroy()
