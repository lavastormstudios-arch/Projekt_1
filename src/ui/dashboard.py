import tkinter as tk
from tkinter import ttk

from src.models.enums import EntryType, EntryStatus


class DashboardPage:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.frame = ttk.Frame(parent)
        self._build()

    def _build(self):
        # Title
        ttk.Label(self.frame, text="Dashboard", font=("Segoe UI", 16, "bold")).pack(
            anchor=tk.W, padx=10, pady=(10, 5))

        # Warning banner frame
        self.warning_frame = ttk.Frame(self.frame)
        self.warning_frame.pack(fill=tk.X, padx=10, pady=5)

        # Summary cards frame
        self.cards_frame = ttk.Frame(self.frame)
        self.cards_frame.pack(fill=tk.X, padx=10, pady=5)

        # Overdue list
        ttk.Label(self.frame, text="Überfällige Einträge", font=("Segoe UI", 12, "bold")).pack(
            anchor=tk.W, padx=10, pady=(15, 5))
        self.overdue_tree = ttk.Treeview(self.frame, columns=("type", "supplier", "desc", "deadline", "amount"),
                                         show="headings", height=6)
        self.overdue_tree.heading("type", text="Typ")
        self.overdue_tree.heading("supplier", text="Lieferant")
        self.overdue_tree.heading("desc", text="Beschreibung")
        self.overdue_tree.heading("deadline", text="Frist")
        self.overdue_tree.heading("amount", text="Betrag")
        self.overdue_tree.column("type", width=100)
        self.overdue_tree.column("supplier", width=150)
        self.overdue_tree.column("desc", width=250)
        self.overdue_tree.column("deadline", width=100)
        self.overdue_tree.column("amount", width=100)
        self.overdue_tree.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.overdue_tree.bind("<Double-1>", self._on_overdue_double_click)

        # Due soon list
        ttk.Label(self.frame, text="Bald fällig", font=("Segoe UI", 12, "bold")).pack(
            anchor=tk.W, padx=10, pady=(10, 5))
        self.due_soon_tree = ttk.Treeview(self.frame, columns=("type", "supplier", "desc", "deadline", "days"),
                                          show="headings", height=6)
        self.due_soon_tree.heading("type", text="Typ")
        self.due_soon_tree.heading("supplier", text="Lieferant")
        self.due_soon_tree.heading("desc", text="Beschreibung")
        self.due_soon_tree.heading("deadline", text="Frist")
        self.due_soon_tree.heading("days", text="Verbleibend")
        self.due_soon_tree.column("type", width=100)
        self.due_soon_tree.column("supplier", width=150)
        self.due_soon_tree.column("desc", width=250)
        self.due_soon_tree.column("deadline", width=100)
        self.due_soon_tree.column("days", width=100)
        self.due_soon_tree.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.due_soon_tree.bind("<Double-1>", self._on_due_soon_double_click)

        self._overdue_entries = []
        self._due_soon_entries = []

    def _create_card(self, parent, title, value, color="#4472C4"):
        card = tk.Frame(parent, bg=color, padx=15, pady=10)
        tk.Label(card, text=title, bg=color, fg="white", font=("Segoe UI", 9)).pack()
        tk.Label(card, text=str(value), bg=color, fg="white", font=("Segoe UI", 18, "bold")).pack()
        return card

    def refresh(self):
        entries = self.app.entry_service.get_all()
        overdue, due_soon = self.app.reminder_service.check()
        self._overdue_entries = overdue
        self._due_soon_entries = due_soon

        # Clear warnings
        for w in self.warning_frame.winfo_children():
            w.destroy()

        if overdue:
            banner = tk.Frame(self.warning_frame, bg="#D32F2F", padx=10, pady=8)
            banner.pack(fill=tk.X, pady=2)
            tk.Label(banner, text=f"⚠ {len(overdue)} überfällige Einträge!",
                     bg="#D32F2F", fg="white", font=("Segoe UI", 11, "bold")).pack(anchor=tk.W)

        if due_soon:
            banner = tk.Frame(self.warning_frame, bg="#F57C00", padx=10, pady=8)
            banner.pack(fill=tk.X, pady=2)
            tk.Label(banner, text=f"{len(due_soon)} Einträge fällig in den nächsten 7 Tagen",
                     bg="#F57C00", fg="white", font=("Segoe UI", 11)).pack(anchor=tk.W)

        # Summary cards
        for w in self.cards_frame.winfo_children():
            w.destroy()

        total = len(entries)
        offen = len([e for e in entries if e.status == EntryStatus.OFFEN])
        abgerechnet = len([e for e in entries if e.status == EntryStatus.ABGERECHNET])
        total_amount = sum(e.amount for e in entries if e.status not in (EntryStatus.ABGERECHNET, EntryStatus.STORNIERT))
        billed_amount = sum(e.amount_billed for e in entries if e.status == EntryStatus.ABGERECHNET)

        cards = [
            ("Gesamt", total, "#4472C4"),
            ("Offen", offen, "#F57C00"),
            ("Abgerechnet", abgerechnet, "#388E3C"),
            ("Überfällig", len(overdue), "#D32F2F"),
            (f"Erw. Summe", f"{total_amount:,.2f}€", "#5C6BC0"),
            (f"Abger. Summe", f"{billed_amount:,.2f}€", "#388E3C"),
        ]
        for i, (title, value, color) in enumerate(cards):
            card = self._create_card(self.cards_frame, title, value, color)
            card.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
        for i in range(len(cards)):
            self.cards_frame.columnconfigure(i, weight=1)

        # Overdue table
        self.overdue_tree.delete(*self.overdue_tree.get_children())
        for e in overdue:
            deadline = e.billing_deadline.strftime("%d.%m.%y") if e.billing_deadline else ""
            self.overdue_tree.insert("", tk.END, values=(
                e.entry_type.value, e.supplier_name, e.description,
                deadline, f"{e.amount:,.2f}€"
            ))

        # Due soon table
        self.due_soon_tree.delete(*self.due_soon_tree.get_children())
        for e in due_soon:
            deadline = e.billing_deadline.strftime("%d.%m.%y") if e.billing_deadline else ""
            days = e.days_until_deadline()
            self.due_soon_tree.insert("", tk.END, values=(
                e.entry_type.value, e.supplier_name, e.description,
                deadline, f"{days} Tage"
            ))

    def _on_overdue_double_click(self, event):
        sel = self.overdue_tree.selection()
        if sel:
            idx = self.overdue_tree.index(sel[0])
            if idx < len(self._overdue_entries):
                from src.ui.entry_form import EntryFormDialog
                EntryFormDialog(self.app.root, self.app, entry=self._overdue_entries[idx])

    def _on_due_soon_double_click(self, event):
        sel = self.due_soon_tree.selection()
        if sel:
            idx = self.due_soon_tree.index(sel[0])
            if idx < len(self._due_soon_entries):
                from src.ui.entry_form import EntryFormDialog
                EntryFormDialog(self.app.root, self.app, entry=self._due_soon_entries[idx])

    def show(self):
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.refresh()

    def hide(self):
        self.frame.pack_forget()
