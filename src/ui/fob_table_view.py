import tkinter as tk
from tkinter import ttk


_COLUMNS = [
    ("artnr",         "Artnr",        80),
    ("bezeichnung",   "Bezeichnung", 180),
    ("lieferant",     "Lieferant",   120),
    ("fob_dollar",    "FOB $",        70),
    ("fob_rmb",       "FOB ¥",        70),
    ("fob_euro",      "FOB €",        70),
    ("ek_eur",        "EK €",         70),
    ("fracht",        "Fracht €",     75),
    ("zoll",          "Zoll €",       65),
    ("neuer_ek",      "NEUER EK €",   90),
]

_COLOR_RED    = "#FFD0D0"
_COLOR_ORANGE = "#FFE8C0"
_COLOR_GREEN  = "#D0FFD4"
_COLOR_WHITE  = "#FFFFFF"
_COLOR_ARCHIV = "#EFEFEF"


class FobTableView(ttk.Frame):
    def __init__(self, parent, fob_service, permissions=None, on_save=None):
        super().__init__(parent)
        self._svc = fob_service
        self._permissions = permissions
        self._on_save = on_save
        self._show_archiv = False
        self._all_rows: list = []      # full dataset (loaded + calculated)
        self._rows: list = []          # filtered view
        self._active_filter: dict = {} # {text, cm, lieferant, warengruppe}
        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self):
        col_ids = [c[0] for c in _COLUMNS]

        self.tree = ttk.Treeview(self, columns=col_ids, show="headings",
                                 selectmode="browse")

        for col_id, col_label, col_width in _COLUMNS:
            self.tree.heading(col_id, text=col_label,
                              command=lambda c=col_id: self._sort_by(c))
            self.tree.column(col_id, width=col_width, minwidth=40, anchor=tk.E
                             if col_id not in ("artnr", "bezeichnung", "lieferant")
                             else tk.W)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Tag colors
        self.tree.tag_configure("red",    background=_COLOR_RED)
        self.tree.tag_configure("orange", background=_COLOR_ORANGE)
        self.tree.tag_configure("green",  background=_COLOR_GREEN)
        self.tree.tag_configure("archiv", background=_COLOR_ARCHIV, foreground="#888888")

        self._sort_col = None
        self._sort_asc = True

        # Right-click context menu
        self._ctx_menu = tk.Menu(self, tearoff=0)
        self._ctx_menu.add_command(label="Neuer Preis erfassen",
                                   command=self._open_price_dialog)
        self.tree.bind("<Button-3>", self._show_context_menu)

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self):
        self._all_rows = []
        entries = self._svc.load_all(include_archiv=self._show_archiv)
        for entry in entries:
            calc = self._svc.calculate(entry)
            self._all_rows.append((entry, calc))
        self._apply_filter()

    def apply_filter(self, text="", cm="", lieferant="", warengruppe=""):
        self._active_filter = {
            "text": text,
            "cm": cm,
            "lieferant": lieferant,
            "warengruppe": warengruppe,
        }
        self._apply_filter()

    def _apply_filter(self):
        f = self._active_filter
        text = f.get("text", "").lower()
        cm   = f.get("cm", "")
        lief = f.get("lieferant", "")
        wgr  = f.get("warengruppe", "")

        self._rows = [
            (e, c) for e, c in self._all_rows
            if (not text or text in (e.artnr or "").lower() or text in (e.bezeichnung or "").lower())
            and (not cm   or e.cm == cm)
            and (not lief or e.lieferant == lief)
            and (not wgr  or e.warengruppe == wgr)
        ]
        self.tree.delete(*self.tree.get_children())
        for entry, calc in self._rows:
            self._insert_row(entry, calc)

    def get_distinct_values(self, field: str) -> list:
        """Return sorted unique non-empty values for *field* from the full dataset."""
        seen = set()
        result = []
        for entry, _ in self._all_rows:
            v = getattr(entry, field, "") or ""
            if v and v not in seen:
                seen.add(v)
                result.append(v)
        return sorted(result)

    def _insert_row(self, entry, calc):
        def fmt(v, decimals=2):
            try:
                return f"{float(v):.{decimals}f}"
            except (TypeError, ValueError):
                return ""

        def fmt_pct(v):
            try:
                return f"{float(v)*100:.1f}%"
            except (TypeError, ValueError):
                return ""

        values = (
            entry.artnr,
            entry.bezeichnung,
            entry.lieferant,
            fmt(entry.ek_fob_dollar, 2) if entry.ek_fob_dollar else "",
            fmt(entry.ek_fob_rmb, 2) if entry.ek_fob_rmb else "",
            fmt(entry.ek_fob_euro, 2) if entry.ek_fob_euro else "",
            fmt(calc["ek_in_eur"]),
            fmt(calc["frachtkosten"]),
            fmt(calc["zollkosten"]),
            fmt(calc["neuer_ek"]),
        )

        if entry.archiv:
            tag = "archiv"
        else:
            tag = ""

        self.tree.insert("", tk.END, iid=entry.id, values=values,
                         tags=(tag,) if tag else ())

    # ------------------------------------------------------------------
    # Selection helper
    # ------------------------------------------------------------------

    def selected_entry(self):
        sel = self.tree.selection()
        if not sel:
            return None
        entry_id = sel[0]
        for entry, _ in self._rows:
            if entry.id == entry_id:
                return entry
        return None

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    def _sort_by(self, col_id):
        if self._sort_col == col_id:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col_id
            self._sort_asc = True

        def sort_key(item):
            entry, calc = item
            _map = {
                "artnr":        entry.artnr,
                "bezeichnung":  entry.bezeichnung,
                "lieferant":    entry.lieferant,
                "fob_dollar":   entry.ek_fob_dollar,
                "fob_rmb":      entry.ek_fob_rmb,
                "fob_euro":     entry.ek_fob_euro,
                "ek_eur":       calc["ek_in_eur"],
                "fracht":       calc["frachtkosten"],
                "zoll":         calc["zollkosten"],
                "neuer_ek":     calc["neuer_ek"],
            }
            v = _map.get(col_id, "")
            if isinstance(v, str):
                return v.lower()
            return v if v is not None else 0

        self._all_rows.sort(key=sort_key, reverse=not self._sort_asc)
        self._apply_filter()

    # ------------------------------------------------------------------
    # Archiv toggle
    # ------------------------------------------------------------------

    def set_show_archiv(self, show: bool):
        self._show_archiv = show
        self.refresh()

    # ------------------------------------------------------------------
    # Context menu / price dialog
    # ------------------------------------------------------------------

    def _show_context_menu(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self._ctx_menu.tk_popup(event.x_root, event.y_root)

    def _open_price_dialog(self):
        entry = self.selected_entry()
        if entry is None:
            return
        from src.ui.fob_price_dialog import FobPriceDialog
        FobPriceDialog(
            self.winfo_toplevel(),
            entry,
            self._svc,
            on_save=self._after_price_update,
        )

    def _after_price_update(self):
        self.refresh()
        if self._on_save:
            self._on_save()
        # Propagate to parent window's status bar if available
        try:
            toplevel = self.winfo_toplevel()
            if hasattr(toplevel, "_refresh_status"):
                toplevel._refresh_status()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Status summary
    # ------------------------------------------------------------------

    def get_status_text(self) -> str:
        active = [(e, c) for e, c in self._rows if not e.archiv]
        count = len(active)
        if count == 0:
            return "Keine Artikel"
        avg_ek = sum(c["neuer_ek"] for _, c in active) / count
        return f"{count} Artikel  |  Ø NEUER EK: {avg_ek:.2f} €"
