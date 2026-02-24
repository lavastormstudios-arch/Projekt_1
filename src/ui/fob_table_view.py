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
    ("marge_uvp",     "Marge UVP",    80),
    ("marge_aktion",  "Marge Aktion", 90),
]

_COLOR_RED    = "#FFD0D0"
_COLOR_ORANGE = "#FFE8C0"
_COLOR_GREEN  = "#D0FFD4"
_COLOR_WHITE  = "#FFFFFF"
_COLOR_ARCHIV = "#EFEFEF"


class FobTableView(ttk.Frame):
    def __init__(self, parent, fob_service, permissions=None):
        super().__init__(parent)
        self._svc = fob_service
        self._permissions = permissions
        self._show_archiv = False
        self._rows: list = []      # list of (entry, calc_dict)
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

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        self._rows = []

        entries = self._svc.load_all(include_archiv=self._show_archiv)
        for entry in entries:
            calc = self._svc.calculate(entry)
            self._rows.append((entry, calc))
            self._insert_row(entry, calc)

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
            fmt_pct(calc["marge_uvp"]) if entry.geplanter_uvp else "",
            fmt_pct(calc["marge_aktion"]) if entry.aktionspreis else "",
        )

        # Color tag based on marge_uvp
        if entry.archiv:
            tag = "archiv"
        else:
            m = calc.get("marge_uvp", 0)
            if entry.geplanter_uvp:
                if m < 0.10:
                    tag = "red"
                elif m < 0.20:
                    tag = "orange"
                else:
                    tag = "green"
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
                "marge_uvp":    calc["marge_uvp"],
                "marge_aktion": calc["marge_aktion"],
            }
            v = _map.get(col_id, "")
            if isinstance(v, str):
                return v.lower()
            return v if v is not None else 0

        self._rows.sort(key=sort_key, reverse=not self._sort_asc)
        self.tree.delete(*self.tree.get_children())
        for entry, calc in self._rows:
            self._insert_row(entry, calc)

    # ------------------------------------------------------------------
    # Archiv toggle
    # ------------------------------------------------------------------

    def set_show_archiv(self, show: bool):
        self._show_archiv = show
        self.refresh()

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
