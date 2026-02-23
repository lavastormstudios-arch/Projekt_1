import os
import tkinter as tk
from tkinter import ttk, messagebox

from src.models.enums import EntryType
from src.services.invoice_service import InvoiceService


class InvoiceDialog:
    def __init__(self, parent, entry, supplier, supplier_service, invoice_service: InvoiceService):
        self.entry = entry
        self.supplier = supplier
        self.supplier_service = supplier_service
        self.invoice_service = invoice_service

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Rechnung erstellen — {entry.supplier_name}")
        self.dialog.geometry("480x420")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._qty_vars = {}   # article_number -> tk.StringVar (Kickback)
        self._revenue_var = tk.StringVar()  # Umsatzbonus
        self._tier_label_var = tk.StringVar(value="–")

        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        outer = ttk.Frame(self.dialog, padding=15)
        outer.pack(fill=tk.BOTH, expand=True)

        et = self.entry.entry_type

        if et == EntryType.KICKBACK:
            self._build_kickback(outer)
        elif et == EntryType.UMSATZBONUS:
            self._build_umsatzbonus(outer)
        elif et == EntryType.WKZ and self.entry.wkz_is_percentage:
            self._build_wkz_percentage(outer)
        else:
            self._build_summary(outer)

        ttk.Separator(outer, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        btn_frame = ttk.Frame(outer)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Erstellen", command=self._on_create).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Abbrechen", command=self.dialog.destroy).pack(side=tk.LEFT, padx=4)

    # ------------------------------------------------------------------
    def _info_row(self, parent, label: str, value: str, row: int):
        ttk.Label(parent, text=label, font=("Segoe UI", 9, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=2, padx=(0, 10))
        ttk.Label(parent, text=value).grid(row=row, column=1, sticky=tk.W, pady=2)

    def _build_summary(self, parent):
        ttk.Label(parent, text="Rechnungsvorschau", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, pady=(0, 8))
        g = ttk.Frame(parent)
        g.pack(fill=tk.X, pady=4)
        self._info_row(g, "Lieferant:", self.supplier.name, 0)
        self._info_row(g, "Typ:", self.entry.entry_type.value, 1)
        self._info_row(g, "Beschreibung:", self.entry.description, 2)
        self._info_row(g, "Betrag (netto):", f"{self.entry.amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."), 3)

    def _build_wkz_percentage(self, parent):
        ttk.Label(parent, text="WKZ Prozentual – Vorschau", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, pady=(0, 8))
        net = round(self.supplier.purchase_volume * self.entry.wkz_percentage / 100, 2)
        g = ttk.Frame(parent)
        g.pack(fill=tk.X, pady=4)
        self._info_row(g, "Lieferant:", self.supplier.name, 0)
        self._info_row(g, "Einkaufsumsatz (Basis):",
                       f"{self.supplier.purchase_volume:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."), 1)
        self._info_row(g, "Satz:", f"{self.entry.wkz_percentage:.2f} %", 2)
        self._info_row(g, "Nettobetrag:",
                       f"{net:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."), 3)

    def _build_kickback(self, parent):
        ttk.Label(parent, text="Kickback – Mengen eingeben", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, pady=(0, 8))

        articles = self.entry.get_kickback_articles()

        # Scrollable canvas for long article lists
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(canvas_frame, height=230)
        vsb = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")

        # Header row
        for col, text in enumerate(("Art.-Nr.", "Satz (€)", "Menge", "Betrag (€)")):
            ttk.Label(inner, text=text, font=("Segoe UI", 9, "bold")).grid(
                row=0, column=col, padx=6, pady=2, sticky=tk.W)

        self._total_var = tk.StringVar(value="0,00")

        for i, art in enumerate(articles, start=1):
            art_nr = art.get("article_number", "")
            rate = float(art.get("kickback_amount", 0))
            ttk.Label(inner, text=art_nr).grid(row=i, column=0, padx=6, pady=2, sticky=tk.W)
            ttk.Label(inner, text=f"{rate:.2f}").grid(row=i, column=1, padx=6, pady=2, sticky=tk.E)
            var = tk.StringVar(value="0")
            self._qty_vars[art_nr] = var
            spin = ttk.Spinbox(inner, textvariable=var, from_=0, to=999999, width=8,
                               command=self._update_kickback_total)
            spin.grid(row=i, column=2, padx=6, pady=2)
            var.trace_add("write", lambda *_: self._update_kickback_total())
            lbl = ttk.Label(inner, text="0,00")
            lbl.grid(row=i, column=3, padx=6, pady=2, sticky=tk.E)
            art["_lbl"] = lbl  # store reference for live update

        inner.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

        self._kickback_articles_ref = articles

        total_row = ttk.Frame(parent)
        total_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(total_row, text="Gesamt (netto):", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        ttk.Label(total_row, textvariable=self._total_var, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=6)
        ttk.Label(total_row, text="€").pack(side=tk.LEFT)

    def _update_kickback_total(self):
        total = 0.0
        for art in self._kickback_articles_ref:
            art_nr = art.get("article_number", "")
            rate = float(art.get("kickback_amount", 0))
            try:
                qty = float(self._qty_vars[art_nr].get())
            except (ValueError, KeyError):
                qty = 0.0
            line = round(qty * rate, 2)
            total += line
            lbl = art.get("_lbl")
            if lbl:
                lbl.config(text=f"{line:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        self._total_var.set(f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    def _build_umsatzbonus(self, parent):
        ttk.Label(parent, text="Umsatzbonus – Umsatz eingeben", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, pady=(0, 8))

        g = ttk.Frame(parent)
        g.pack(fill=tk.X, pady=4)

        ttk.Label(g, text="Erzielter Umsatz (€):", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=4, padx=(0, 10))
        rev_entry = ttk.Entry(g, textvariable=self._revenue_var, width=20)
        rev_entry.grid(row=0, column=1, sticky=tk.W, pady=4)
        rev_entry.bind("<KeyRelease>", lambda e: self._update_umsatzbonus_tier())

        ttk.Label(g, text="Passende Staffel:", font=("Segoe UI", 9, "bold")).grid(
            row=1, column=0, sticky=tk.W, pady=4, padx=(0, 10))
        ttk.Label(g, textvariable=self._tier_label_var).grid(row=1, column=1, sticky=tk.W, pady=4)

        ttk.Label(g, text="Lieferant:", font=("Segoe UI", 9, "bold")).grid(
            row=2, column=0, sticky=tk.W, pady=4, padx=(0, 10))
        ttk.Label(g, text=self.supplier.name).grid(row=2, column=1, sticky=tk.W, pady=4)

        ttk.Label(g, text="Beschreibung:", font=("Segoe UI", 9, "bold")).grid(
            row=3, column=0, sticky=tk.W, pady=4, padx=(0, 10))
        ttk.Label(g, text=self.entry.description, wraplength=280).grid(row=3, column=1, sticky=tk.W, pady=4)

    def _update_umsatzbonus_tier(self):
        try:
            rev = float(self._revenue_var.get().replace(",", "."))
        except ValueError:
            self._tier_label_var.set("–")
            return

        staffeln = self.entry.get_umsatzbonus_staffeln()
        matching = None
        for tier in sorted(staffeln, key=lambda t: float(t.get("revenue_threshold", 0)), reverse=True):
            if rev >= float(tier.get("revenue_threshold", 0)):
                matching = tier
                break

        if matching:
            von = float(matching.get("revenue_threshold", 0))
            pct = float(matching.get("bonus_percentage", 0))
            bonus = round(rev * pct / 100, 2)
            bonus_str = f"{bonus:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            von_str = f"{von:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            self._tier_label_var.set(f"ab {von_str} € → {pct:.2f}%  (= {bonus_str} €)")
        else:
            self._tier_label_var.set("Keine passende Staffel")

    # ------------------------------------------------------------------
    def _on_create(self):
        et = self.entry.entry_type

        qty_map = None
        achieved_revenue = None

        if et == EntryType.KICKBACK:
            qty_map = {}
            for art_nr, var in self._qty_vars.items():
                try:
                    qty_map[art_nr] = float(var.get())
                except ValueError:
                    qty_map[art_nr] = 0.0

        elif et == EntryType.UMSATZBONUS:
            try:
                achieved_revenue = float(self._revenue_var.get().replace(",", "."))
            except ValueError:
                messagebox.showwarning("Eingabefehler", "Bitte einen gültigen Umsatz eingeben.", parent=self.dialog)
                return

        try:
            context = self.invoice_service.build_context(
                self.entry, self.supplier, qty_map=qty_map, achieved_revenue=achieved_revenue
            )
            pdf_path = self.invoice_service.generate(self.entry, self.supplier, context)
        except FileNotFoundError as exc:
            messagebox.showerror("Vorlage fehlt", str(exc), parent=self.dialog)
            return
        except RuntimeError as exc:
            messagebox.showerror("Fehler", str(exc), parent=self.dialog)
            return
        except Exception as exc:
            messagebox.showerror(
                "Fehler bei der PDF-Erstellung",
                f"Die Rechnung konnte nicht erstellt werden:\n\n{exc}\n\n"
                "Stellen Sie sicher, dass Microsoft Word installiert ist und die Vorlage korrekt ist.",
                parent=self.dialog
            )
            return

        abs_path = os.path.abspath(pdf_path)
        messagebox.showinfo(
            "Rechnung erstellt",
            f"Gespeichert unter:\n{abs_path}",
            parent=self.dialog
        )
        try:
            os.startfile(abs_path)
        except Exception:
            pass
        self.dialog.destroy()


# ---------------------------------------------------------------------------
# Batch invoice dialog — multiple entries at once
# ---------------------------------------------------------------------------

class BulkInvoiceDialog:
    def __init__(self, parent, pairs: list, invoice_service: InvoiceService):
        """
        pairs: list of (entry, supplier) tuples
        """
        self.pairs = pairs
        self.invoice_service = invoice_service
        self._row_data = []   # one dict per entry

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Rechnungen erstellen — {len(pairs)} Einträge")
        self.dialog.geometry("640x520")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        outer = ttk.Frame(self.dialog, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer,
                  text=f"{len(self.pairs)} Rechnungen werden erstellt",
                  font=("Segoe UI", 11, "bold")).pack(anchor=tk.W, pady=(0, 6))
        ttk.Label(outer,
                  text="Ctrl+Klick / Shift+Klick zum Mehrfachauswählen in der Tabelle.",
                  font=("Segoe UI", 8), foreground="#888").pack(anchor=tk.W, pady=(0, 8))

        # ── Scrollable entry list ──────────────────────────────────────
        cf = ttk.Frame(outer)
        cf.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(cf, highlightthickness=0)
        vsb = ttk.Scrollbar(cf, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._inner = ttk.Frame(canvas)
        win_id = canvas.create_window((0, 0), window=self._inner, anchor="nw")

        for i, (entry, supplier) in enumerate(self.pairs):
            self._build_entry_card(self._inner, entry, supplier, i)
            if i < len(self.pairs) - 1:
                ttk.Separator(self._inner, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=2)

        self._inner.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        self._inner.bind("<Configure>",
                         lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1 * e.delta / 120), "units"))

        # ── Buttons ───────────────────────────────────────────────────
        ttk.Separator(outer, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        bf = ttk.Frame(outer)
        bf.pack(fill=tk.X)

        self._create_btn = ttk.Button(bf, text="Alle erstellen",
                                      command=self._on_create_all)
        self._create_btn.pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text="Abbrechen", command=self.dialog.destroy).pack(side=tk.LEFT, padx=4)

        self._folder_btn = ttk.Button(bf, text="Ordner öffnen",
                                      command=self._open_output_folder,
                                      state="disabled")
        self._folder_btn.pack(side=tk.RIGHT, padx=4)

    # ------------------------------------------------------------------
    def _build_entry_card(self, parent, entry, supplier, idx):
        row_data = {}
        self._row_data.append(row_data)

        card = ttk.Frame(parent)
        card.pack(fill=tk.X, padx=8, pady=6)

        # Header row
        hdr = ttk.Frame(card)
        hdr.pack(fill=tk.X)
        ttk.Label(hdr, text=supplier.name,
                  font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        ttk.Label(hdr, text=f"  [{entry.entry_type.value}]",
                  foreground="#666", font=("Segoe UI", 9)).pack(side=tk.LEFT)

        status_var = tk.StringVar(value="")
        row_data["status_var"] = status_var
        ttk.Label(hdr, textvariable=status_var,
                  font=("Segoe UI", 9)).pack(side=tk.RIGHT)

        # Entry-type-specific content
        et = entry.entry_type
        if et == EntryType.KICKBACK:
            self._card_kickback(card, entry, row_data)
        elif et == EntryType.UMSATZBONUS:
            self._card_umsatzbonus(card, entry, row_data)
        else:
            # WKZ (fixed or percentage) — no user input needed
            if et == EntryType.WKZ and getattr(entry, "wkz_is_percentage", False):
                vol = getattr(supplier, "purchase_volume", 0) or 0
                net = round(vol * (getattr(entry, "wkz_percentage", 0) or 0) / 100, 2)
                amt = self._fmt(net)
                ttk.Label(card,
                          text=f"Basis: {self._fmt(vol)} €  ×  "
                               f"{getattr(entry, 'wkz_percentage', 0):.2f} %  =  {amt} €",
                          font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(2, 0))
            else:
                ttk.Label(card,
                          text=f"Betrag (netto): {self._fmt(entry.amount)} €",
                          font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(2, 0))

    def _card_kickback(self, parent, entry, row_data):
        articles = entry.get_kickback_articles()
        qty_vars = {}
        row_data["qty_vars"] = qty_vars

        f = ttk.Frame(parent)
        f.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(f, text="Mengen:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)

        grid = ttk.Frame(f)
        grid.pack(fill=tk.X)
        MAX_COLS = 4
        for i, art in enumerate(articles):
            art_nr = art.get("article_number", "")
            rate = float(art.get("kickback_amount", 0))
            row, col = divmod(i, MAX_COLS)
            ttk.Label(grid, text=f"Nr.{art_nr} ({rate:.2f}€):",
                      font=("Segoe UI", 8)).grid(
                row=row * 2, column=col, padx=(4, 2), sticky=tk.W)
            var = tk.StringVar(value="0")
            qty_vars[art_nr] = var
            ttk.Entry(grid, textvariable=var, width=8).grid(
                row=row * 2 + 1, column=col, padx=(4, 8), pady=(0, 2), sticky=tk.W)

    def _card_umsatzbonus(self, parent, entry, row_data):
        f = ttk.Frame(parent)
        f.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(f, text="Erzielter Umsatz (€):",
                  font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        rev_var = tk.StringVar()
        row_data["revenue_var"] = rev_var
        ttk.Entry(f, textvariable=rev_var, width=18).pack(side=tk.LEFT)

    # ------------------------------------------------------------------
    @staticmethod
    def _fmt(v) -> str:
        try:
            return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (TypeError, ValueError):
            return "0,00"

    # ------------------------------------------------------------------
    def _on_create_all(self):
        self._create_btn.configure(state="disabled")
        created = 0
        errors = []

        for i, (entry, supplier) in enumerate(self.pairs):
            row_data = self._row_data[i]
            qty_map = None
            achieved_revenue = None

            try:
                if entry.entry_type == EntryType.KICKBACK:
                    qty_map = {}
                    for art_nr, var in row_data.get("qty_vars", {}).items():
                        try:
                            qty_map[art_nr] = float(var.get())
                        except ValueError:
                            qty_map[art_nr] = 0.0

                elif entry.entry_type == EntryType.UMSATZBONUS:
                    rev_str = row_data.get("revenue_var", tk.StringVar()).get().replace(",", ".")
                    if not rev_str:
                        raise ValueError("Kein Umsatz eingegeben.")
                    achieved_revenue = float(rev_str)

                context = self.invoice_service.build_context(
                    entry, supplier, qty_map=qty_map, achieved_revenue=achieved_revenue
                )
                self.invoice_service.generate(entry, supplier, context)

                inv_num = context.get("invoice_number", "")
                row_data["status_var"].set(f"  ✓ {inv_num}")
                created += 1

            except Exception as exc:
                row_data["status_var"].set("  ✗ Fehler")
                errors.append(f"{supplier.name}: {exc}")

        self._folder_btn.configure(state="normal")

        if errors:
            messagebox.showwarning(
                "Teilweise Fehler",
                f"{created} von {len(self.pairs)} Rechnungen erstellt.\n\nFehler:\n"
                + "\n".join(f"  • {e}" for e in errors),
                parent=self.dialog
            )
        else:
            messagebox.showinfo(
                "Fertig",
                f"Alle {created} Rechnungen wurden erfolgreich erstellt.",
                parent=self.dialog
            )

    def _open_output_folder(self):
        folder = os.path.abspath(self.invoice_service.OUTPUT_DIR)
        os.makedirs(folder, exist_ok=True)
        os.startfile(folder)
