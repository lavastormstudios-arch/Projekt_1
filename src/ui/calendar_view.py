import tkinter as tk
from tkinter import ttk
from datetime import date, timedelta
import calendar

from src.models.enums import EntryStatus
from src.utils.date_helpers import format_date


class CalendarPage:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.frame = ttk.Frame(parent)
        self.current_year = date.today().year
        self.current_month = date.today().month
        self._entries = []
        self._deadline_map = {}
        self._build()

    def _build(self):
        ttk.Label(self.frame, text="Kalender", font=("Segoe UI", 16, "bold")).pack(
            anchor=tk.W, padx=10, pady=(10, 5))

        # Navigation
        nav = ttk.Frame(self.frame)
        nav.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(nav, text="◄", width=3, command=self._prev_month).pack(side=tk.LEFT)
        self.month_label = ttk.Label(nav, text="", font=("Segoe UI", 13, "bold"))
        self.month_label.pack(side=tk.LEFT, padx=15)
        ttk.Button(nav, text="►", width=3, command=self._next_month).pack(side=tk.LEFT)
        ttk.Button(nav, text="Heute", command=self._go_today).pack(side=tk.LEFT, padx=15)

        # Legend
        legend = ttk.Frame(self.frame)
        legend.pack(fill=tk.X, padx=10, pady=(0, 5))
        for color, text in [("#D32F2F", "Überfällig"), ("#F57C00", "Bald fällig"),
                            ("#388E3C", "Abgerechnet"), ("#4472C4", "Offen")]:
            tk.Label(legend, text="■", fg=color, font=("Segoe UI", 12)).pack(side=tk.LEFT)
            ttk.Label(legend, text=text).pack(side=tk.LEFT, padx=(0, 12))

        # Calendar grid
        self.cal_frame = ttk.Frame(self.frame)
        self.cal_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Detail list below calendar
        ttk.Label(self.frame, text="Einträge am gewählten Tag:", font=("Segoe UI", 11, "bold")).pack(
            anchor=tk.W, padx=10, pady=(5, 2))
        self.detail_tree = ttk.Treeview(self.frame, columns=("type", "supplier", "desc", "status", "amount"),
                                        show="headings", height=5)
        self.detail_tree.heading("type", text="Typ")
        self.detail_tree.heading("supplier", text="Lieferant")
        self.detail_tree.heading("desc", text="Beschreibung")
        self.detail_tree.heading("status", text="Status")
        self.detail_tree.heading("amount", text="Betrag")
        self.detail_tree.column("type", width=100)
        self.detail_tree.column("supplier", width=150)
        self.detail_tree.column("desc", width=200)
        self.detail_tree.column("status", width=100)
        self.detail_tree.column("amount", width=100)
        self.detail_tree.pack(fill=tk.X, padx=10, pady=(0, 10))

    def _build_calendar_grid(self):
        for widget in self.cal_frame.winfo_children():
            widget.destroy()

        month_name = calendar.month_name[self.current_month] if hasattr(calendar, 'month_name') else str(self.current_month)
        # Use German month names
        german_months = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
                         "Juli", "August", "September", "Oktober", "November", "Dezember"]
        self.month_label.config(text=f"{german_months[self.current_month]} {self.current_year}")

        # Day headers
        days = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        for col, day in enumerate(days):
            lbl = ttk.Label(self.cal_frame, text=day, font=("Segoe UI", 10, "bold"),
                            anchor=tk.CENTER, width=10)
            lbl.grid(row=0, column=col, padx=1, pady=2)

        cal = calendar.monthcalendar(self.current_year, self.current_month)
        today = date.today()

        for row_idx, week in enumerate(cal, 1):
            for col_idx, day_num in enumerate(week):
                if day_num == 0:
                    ttk.Label(self.cal_frame, text="", width=10).grid(
                        row=row_idx, column=col_idx, padx=1, pady=1)
                    continue

                d = date(self.current_year, self.current_month, day_num)
                bg = "#FFFFFF"
                fg = "#333333"

                if d in self._deadline_map:
                    entries_on_day = self._deadline_map[d]
                    statuses = [e.status for e in entries_on_day]
                    if any(e.is_overdue() or e.status == EntryStatus.UEBERFAELLIG for e in entries_on_day):
                        bg = "#FFCDD2"
                        fg = "#B71C1C"
                    elif any(e.status == EntryStatus.OFFEN for e in entries_on_day):
                        days_left = (d - today).days
                        if 0 <= days_left <= 7:
                            bg = "#FFE0B2"
                            fg = "#E65100"
                        else:
                            bg = "#BBDEFB"
                            fg = "#0D47A1"
                    elif all(e.status == EntryStatus.ABGERECHNET for e in entries_on_day):
                        bg = "#C8E6C9"
                        fg = "#1B5E20"

                if d == today:
                    fg = "#FFFFFF"
                    bg = "#1976D2" if bg == "#FFFFFF" else bg

                cell = tk.Label(self.cal_frame, text=str(day_num), width=10, height=2,
                                bg=bg, fg=fg, font=("Segoe UI", 10),
                                relief=tk.RIDGE, cursor="hand2")
                cell.grid(row=row_idx, column=col_idx, padx=1, pady=1, sticky="nsew")
                cell.bind("<Button-1>", lambda e, dt=d: self._on_day_click(dt))

        for col in range(7):
            self.cal_frame.columnconfigure(col, weight=1)
        for row_idx in range(len(cal) + 1):
            self.cal_frame.rowconfigure(row_idx, weight=1, minsize=48)

    def _build_deadline_map(self):
        self._deadline_map = {}
        for e in self._entries:
            if e.billing_deadline:
                self._deadline_map.setdefault(e.billing_deadline, []).append(e)

    def _on_day_click(self, d: date):
        self.detail_tree.delete(*self.detail_tree.get_children())
        entries = self._deadline_map.get(d, [])
        for e in entries:
            self.detail_tree.insert("", tk.END, values=(
                e.entry_type.value, e.supplier_name, e.description,
                e.status.value, f"{e.amount:,.2f}€"
            ))
        if not entries:
            self.detail_tree.insert("", tk.END, values=(
                "", "", f"Keine Einträge am {d.strftime('%d.%m.%y')}", "", ""
            ))

    def _prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self._build_calendar_grid()

    def _next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self._build_calendar_grid()

    def _go_today(self):
        self.current_year = date.today().year
        self.current_month = date.today().month
        self._build_calendar_grid()

    def refresh(self):
        self._entries = self.app.entry_service.get_all()
        self._build_deadline_map()
        self._build_calendar_grid()

    def show(self):
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.refresh()

    def hide(self):
        self.frame.pack_forget()
