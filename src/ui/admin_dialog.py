import hashlib
import os
import shutil
import configparser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_PROJECT_ROOT, "config.ini")
_DEFAULT_PIN = "1234"


def _hash(pin: str) -> str:
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Public entry-point — shows PIN prompt, then opens settings on success
# ---------------------------------------------------------------------------

class AdminDialog:
    def __init__(self, parent: tk.Misc, auth_service=None):
        self.parent = parent
        self._auth_service = auth_service
        self._show_pin_prompt()

    def _show_pin_prompt(self):
        dlg = tk.Toplevel(self.parent)
        dlg.title("Admin-Bereich")
        dlg.resizable(False, False)
        dlg.transient(self.parent)
        dlg.grab_set()
        dlg.update_idletasks()
        w, h = 300, 170
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - w) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{x}+{y}")

        f = ttk.Frame(dlg, padding=20)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text="Admin-Bereich", font=("Segoe UI", 11, "bold")).pack(pady=(0, 12))
        ttk.Label(f, text="PIN:").pack(anchor=tk.W)

        pin_var = tk.StringVar()
        pin_entry = ttk.Entry(f, textvariable=pin_var, show="●", width=20)
        pin_entry.pack(fill=tk.X, pady=(4, 12))
        pin_entry.focus_set()

        def attempt():
            if self._verify(pin_var.get()):
                dlg.destroy()
                AdminSettingsDialog(self.parent, self._auth_service)
            else:
                pin_var.set("")
                messagebox.showerror("Fehler", "Falscher PIN.", parent=dlg)

        pin_entry.bind("<Return>", lambda _: attempt())
        btn_row = ttk.Frame(f)
        btn_row.pack()
        ttk.Button(btn_row, text="OK", command=attempt, width=10).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Abbrechen", command=dlg.destroy, width=10).pack(side=tk.LEFT, padx=4)

    def _verify(self, entered: str) -> bool:
        cfg = configparser.ConfigParser()
        cfg.read(_CONFIG_PATH, encoding="utf-8")
        stored = cfg.get("Admin", "pin_hash", fallback=_hash(_DEFAULT_PIN))
        return _hash(entered) == stored


# ---------------------------------------------------------------------------
# Full settings dialog (opened after successful PIN)
# ---------------------------------------------------------------------------

class AdminSettingsDialog:
    def __init__(self, parent: tk.Misc, auth_service=None):
        self.parent = parent
        self._auth_service = auth_service

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Einstellungen — Admin")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        w, h = 520, 520
        self.dialog.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.dialog.geometry(f"{w}x{h}+{x}+{y}")

        self._v: dict[str, tk.Variable] = {}
        self._cfg = configparser.ConfigParser()
        self._cfg.read(_CONFIG_PATH, encoding="utf-8")

        self._build()

    # ── helpers ────────────────────────────────────────────────────────

    def _g(self, section: str, key: str, fallback: str = "") -> str:
        return self._cfg.get(section, key, fallback=fallback)

    def _browse_file(self, var: tk.StringVar, filetypes=None):
        path = filedialog.askopenfilename(
            parent=self.dialog,
            title="Datei auswählen",
            filetypes=filetypes or [("Alle Dateien", "*.*")],
        )
        if path:
            var.set(path)

    def _browse_dir(self, var: tk.StringVar):
        path = filedialog.askdirectory(parent=self.dialog, title="Ordner auswählen")
        if path:
            var.set(path)

    # ── layout ─────────────────────────────────────────────────────────

    def _build(self):
        nb = ttk.Notebook(self.dialog)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._tab_import(nb)
        self._tab_smtp(nb)
        self._tab_documents(nb)
        self._tab_reminders(nb)
        self._tab_fob_params(nb)
        self._tab_security(nb)
        self._tab_invoice_numbers(nb)
        self._tab_backup(nb)

        btn_row = ttk.Frame(self.dialog)
        btn_row.pack(pady=(0, 10))
        ttk.Button(btn_row, text="Speichern", command=self._save, width=12).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_row, text="Abbrechen", command=self.dialog.destroy, width=12).pack(side=tk.LEFT, padx=6)
        if self._auth_service is not None:
            ttk.Button(btn_row, text="Benutzerverwaltung",
                       command=self._open_user_management, width=18).pack(side=tk.LEFT, padx=6)

    def _get_articles_status(self) -> str:
        from src.services.article_service import ArticleService
        if ArticleService.is_loaded():
            return f"{ArticleService.get_count()} Artikel geladen"
        return "Noch nicht geladen"

    def _reload_articles(self):
        from src.services.article_service import ArticleService
        path = self._v["articles_csv_path"].get().strip()
        if not path:
            messagebox.showwarning("Hinweis", "Kein Pfad angegeben.", parent=self.dialog)
            return
        try:
            count = ArticleService.load_from_csv(path)
            self._articles_status.set(f"{count} Artikel geladen")
            messagebox.showinfo("Erfolg", f"{count} Artikel aus CSV geladen.", parent=self.dialog)
        except ValueError as exc:
            messagebox.showerror("Fehler", str(exc), parent=self.dialog)

    def _open_user_management(self):
        from src.ui.user_management_dialog import UserManagementDialog
        UserManagementDialog(self.dialog, self._auth_service)

    # ── Tab: Import ────────────────────────────────────────────────────

    def _tab_import(self, nb: ttk.Notebook):
        f = ttk.Frame(nb, padding=16)
        nb.add(f, text="Import")

        ttk.Label(f, text="CSV-Importpfad",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 4))
        ttk.Label(f, text="Pfad zur SAP-Exportdatei mit Lieferantendaten.\n"
                  "Die Datei wird beim Programmstart automatisch eingelesen.",
                  wraplength=470).pack(anchor=tk.W, pady=(0, 10))

        self._v["csv_path"] = tk.StringVar(value=self._g("Import", "csv_path"))
        row = ttk.Frame(f)
        row.pack(fill=tk.X)
        ttk.Entry(row, textvariable=self._v["csv_path"], width=42).pack(side=tk.LEFT)
        ttk.Button(row, text="...", width=3,
                   command=lambda: self._browse_file(
                       self._v["csv_path"],
                       filetypes=[("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*")]
                   )).pack(side=tk.LEFT, padx=(4, 0))

        ttk.Separator(f, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=14)

        ttk.Label(f, text="Artikelliste (SAP-Export)",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 4))
        ttk.Label(f, text="CSV-Datei mit Artikelstammdaten (Artnr, Bez, EK, ...).\n"
                  "Wird beim Programmstart geladen und im FOB-Formular zur Auto-Vervollständigung genutzt.",
                  wraplength=470).pack(anchor=tk.W, pady=(0, 6))

        self._v["articles_csv_path"] = tk.StringVar(
            value=self._g("Import", "articles_csv_path"))
        row2 = ttk.Frame(f)
        row2.pack(fill=tk.X)
        ttk.Entry(row2, textvariable=self._v["articles_csv_path"], width=42).pack(side=tk.LEFT)
        ttk.Button(row2, text="...", width=3,
                   command=lambda: self._browse_file(
                       self._v["articles_csv_path"],
                       filetypes=[("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*")]
                   )).pack(side=tk.LEFT, padx=(4, 0))

        self._articles_status = tk.StringVar(value=self._get_articles_status())
        ttk.Label(f, textvariable=self._articles_status,
                  font=("Segoe UI", 8), foreground="gray").pack(anchor=tk.W, pady=(4, 0))
        ttk.Button(f, text="Jetzt laden",
                   command=self._reload_articles).pack(anchor=tk.W, pady=(4, 0))

    # ── Tab: SMTP ──────────────────────────────────────────────────────

    def _tab_smtp(self, nb: ttk.Notebook):
        f = ttk.Frame(nb, padding=16)
        nb.add(f, text="E-Mail (SMTP)")

        self._v["smtp_enabled"] = tk.BooleanVar(
            value=self._g("SMTP", "enabled", "false").lower() == "true")
        ttk.Checkbutton(f, text="E-Mail-Versand aktivieren",
                        variable=self._v["smtp_enabled"]).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 8))

        fields = [
            ("smtp_server", "SMTP-Server:",  self._g("SMTP", "server")),
            ("smtp_port",   "Port:",         self._g("SMTP", "port",         "587")),
            ("smtp_user",   "Benutzername:", self._g("SMTP", "username")),
            ("smtp_pass",   "Passwort:",     self._g("SMTP", "password")),
            ("smtp_from",   "Absender:",     self._g("SMTP", "from_address")),
            ("smtp_to",     "Empfänger:",    self._g("SMTP", "to_address")),
        ]
        for i, (key, label, val) in enumerate(fields, 1):
            ttk.Label(f, text=label).grid(row=i, column=0, sticky=tk.W, pady=3)
            self._v[key] = tk.StringVar(value=val)
            show = "●" if key == "smtp_pass" else None
            ttk.Entry(f, textvariable=self._v[key], width=32, show=show).grid(
                row=i, column=1, padx=10, pady=3, sticky=tk.W)

        self._v["smtp_tls"] = tk.BooleanVar(
            value=self._g("SMTP", "use_tls", "true").lower() == "true")
        ttk.Checkbutton(f, text="TLS verwenden",
                        variable=self._v["smtp_tls"]).grid(
            row=len(fields) + 1, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))

    # ── Tab: Dokumente ─────────────────────────────────────────────────

    def _tab_documents(self, nb: ttk.Notebook):
        f = ttk.Frame(nb, padding=16)
        nb.add(f, text="Dokumente")

        ttk.Label(f, text="Dokumenten-Basisordner",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 4))
        ttk.Label(f, text="Basisordner für die Lieferanten-Dokumentenablage.\n"
                  "Struktur: {Basisordner} / {Lieferant} / {Kategorie} /",
                  wraplength=470).pack(anchor=tk.W, pady=(0, 10))

        self._v["doc_folder"] = tk.StringVar(
            value=self._g("Documents", "base_folder", "data/documents"))
        row = ttk.Frame(f)
        row.pack(fill=tk.X)
        ttk.Entry(row, textvariable=self._v["doc_folder"], width=42).pack(side=tk.LEFT)
        ttk.Button(row, text="...", width=3,
                   command=lambda: self._browse_dir(self._v["doc_folder"])).pack(
            side=tk.LEFT, padx=(4, 0))

    # ── Tab: Erinnerungen ──────────────────────────────────────────────

    def _tab_reminders(self, nb: ttk.Notebook):
        f = ttk.Frame(nb, padding=16)
        nb.add(f, text="Erinnerungen")

        ttk.Label(f, text="Fristenwarnung",
                  font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        ttk.Label(f, text="Frühwarnung (Tage vor Frist):").grid(
            row=1, column=0, sticky=tk.W, pady=5)
        self._v["warn_days"] = tk.StringVar(
            value=self._g("Reminders", "warn_days_before", "7"))
        ttk.Entry(f, textvariable=self._v["warn_days"], width=8).grid(
            row=1, column=1, sticky=tk.W, padx=10)

    # ── Tab: FOB-Parameter ─────────────────────────────────────────────

    def _tab_fob_params(self, nb: ttk.Notebook):
        f = ttk.Frame(nb, padding=16)
        nb.add(f, text="FOB-Parameter")

        ttk.Label(f, text="Kalkulations-Parameter",
                  font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        _fob_defaults = {
            "eur_usd":        "1.16",
            "eur_rmb":        "8.2443",
            "fracht_40hc":    "4300.0",
            "fracht_20":      "3200.0",
            "zinssatz_pa":    "0.0368",
            "frachtzeit_tage":"45",
            "rekla_quote":    "0.015",
        }

        fields = [
            ("fob_eur_usd",        "EUR / USD:",              self._g("FOB", "eur_usd",        _fob_defaults["eur_usd"])),
            ("fob_eur_rmb",        "EUR / RMB:",              self._g("FOB", "eur_rmb",        _fob_defaults["eur_rmb"])),
            ("fob_fracht_40hc",    'Fracht 40"HC (€):',       self._g("FOB", "fracht_40hc",    _fob_defaults["fracht_40hc"])),
            ("fob_fracht_20",      'Fracht 20" (€):',         self._g("FOB", "fracht_20",      _fob_defaults["fracht_20"])),
            ("fob_zinssatz_pa",    "Zinssatz p.a. (z.B. 0.0368 = 3,68%):", self._g("FOB", "zinssatz_pa",  _fob_defaults["zinssatz_pa"])),
            ("fob_frachtzeit",     "Frachtzeit (Tage):",      self._g("FOB", "frachtzeit_tage",_fob_defaults["frachtzeit_tage"])),
            ("fob_rekla_quote",    "Reklamationsquote (z.B. 0.015 = 1,5%):", self._g("FOB", "rekla_quote",  _fob_defaults["rekla_quote"])),
        ]
        for i, (key, label, val) in enumerate(fields, start=1):
            ttk.Label(f, text=label).grid(row=i, column=0, sticky=tk.W, pady=4)
            self._v[key] = tk.StringVar(value=val)
            ttk.Entry(f, textvariable=self._v[key], width=18).grid(
                row=i, column=1, padx=10, pady=4, sticky=tk.W)

    # ── Tab: Sicherheit ────────────────────────────────────────────────

    def _tab_security(self, nb: ttk.Notebook):
        f = ttk.Frame(nb, padding=16)
        nb.add(f, text="Sicherheit")

        ttk.Label(f, text="Admin-PIN ändern",
                  font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        pin_fields = [
            ("pin_cur",  "Aktueller PIN:"),
            ("pin_new",  "Neuer PIN:"),
            ("pin_conf", "PIN bestätigen:"),
        ]
        for i, (key, label) in enumerate(pin_fields, 1):
            ttk.Label(f, text=label).grid(row=i, column=0, sticky=tk.W, pady=5)
            self._v[key] = tk.StringVar()
            ttk.Entry(f, textvariable=self._v[key], show="●", width=20).grid(
                row=i, column=1, padx=10, sticky=tk.W)

        ttk.Button(f, text="PIN ändern", command=self._change_pin).grid(
            row=4, column=0, columnspan=2, pady=14)
        ttk.Label(f, text="Felder leer lassen, wenn kein PIN-Wechsel gewünscht.",
                  foreground="gray").grid(row=5, column=0, columnspan=2, sticky=tk.W)

    # ── Tab: Rechnungsnummern ──────────────────────────────────────────

    def _tab_invoice_numbers(self, nb: ttk.Notebook):
        from tkinter.scrolledtext import ScrolledText
        f = ttk.Frame(nb, padding=16)
        nb.add(f, text="Rechnungsnummern")

        ttk.Label(f, text="Rechnungsnummern-Pool",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 8))

        from src.services.invoice_service import InvoiceService
        self._invoice_service = InvoiceService()

        self._pool_count_var = tk.StringVar()
        self._pool_count_var.set(f"Verfügbar: {self._invoice_service.available_count()} Nummern")
        ttk.Label(f, textvariable=self._pool_count_var).pack(anchor=tk.W, pady=(0, 12))

        ttk.Label(
            f,
            text="Neue Nummern hinzufügen — Spalte aus Excel direkt einfügen (Strg+V):",
            wraplength=460,
        ).pack(anchor=tk.W, pady=(0, 4))
        self._pool_text = ScrolledText(f, height=8, width=50, font=("Segoe UI", 9))
        self._pool_text.pack(fill=tk.X, pady=(0, 8))

        btn_row = ttk.Frame(f)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="Rechnungsnummern anzeigen",
                   command=self._show_invoice_numbers).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Hinzufügen",
                   command=self._add_invoice_numbers).pack(side=tk.RIGHT)

    @staticmethod
    def _parse_excel_paste(raw: str) -> list:
        """Extrahiert Nummern aus Excel-Einfügen (Tab-getrennte Spalten, Zeilenumbrüche)."""
        numbers = []
        for line in raw.splitlines():
            # Erste Spalte nehmen (Excel trennt Spalten mit Tab)
            cell = line.split("\t")[0].strip()
            if cell:
                numbers.append(cell)
        return numbers

    def _add_invoice_numbers(self):
        raw = self._pool_text.get("1.0", tk.END)
        numbers = self._parse_excel_paste(raw)
        if not numbers:
            messagebox.showwarning("Hinweis", "Keine Nummern eingegeben.", parent=self.dialog)
            return
        added = self._invoice_service.add_invoice_numbers(numbers)
        skipped = len(numbers) - added
        msg = f"{added} Nummer(n) hinzugefügt"
        if skipped:
            msg += f" ({skipped} Duplikat(e) ignoriert)"
        self._pool_text.delete("1.0", tk.END)
        self._pool_count_var.set(f"Verfügbar: {self._invoice_service.available_count()} Nummern")
        messagebox.showinfo("Erfolg", msg, parent=self.dialog)

    def _show_invoice_numbers(self):
        pool = self._invoice_service._load_pool()
        dlg = tk.Toplevel(self.dialog)
        dlg.title("Rechnungsnummern-Pool")
        dlg.transient(self.dialog)
        dlg.grab_set()
        dlg.resizable(True, True)
        w, h = 520, 480
        dlg.update_idletasks()
        x = self.dialog.winfo_rootx() + (self.dialog.winfo_width() - w) // 2
        y = self.dialog.winfo_rooty() + (self.dialog.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{x}+{y}")

        nb2 = ttk.Notebook(dlg)
        nb2.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab: Verfügbar
        f_avail = ttk.Frame(nb2, padding=8)
        nb2.add(f_avail, text=f"Verfügbar ({len(pool['available'])})")
        ttk.Label(f_avail, text=f"{len(pool['available'])} Nummern verfügbar",
                  font=("Segoe UI", 9, "italic"), foreground="gray").pack(anchor=tk.W, pady=(0, 6))
        from tkinter.scrolledtext import ScrolledText as ST
        ta = ST(f_avail, font=("Consolas", 9), state="normal")
        ta.pack(fill=tk.BOTH, expand=True)
        ta.insert("1.0", "\n".join(pool["available"]) if pool["available"] else "(leer)")
        ta.configure(state="disabled")

        # Tab: Verwendet
        f_used = ttk.Frame(nb2, padding=8)
        nb2.add(f_used, text=f"Verwendet ({len(pool['used'])})")
        ttk.Label(f_used, text=f"{len(pool['used'])} Nummern bereits verwendet",
                  font=("Segoe UI", 9, "italic"), foreground="gray").pack(anchor=tk.W, pady=(0, 6))
        tu = ST(f_used, font=("Consolas", 9), state="normal")
        tu.pack(fill=tk.BOTH, expand=True)
        used_lines = [f"{u['number']}  –  {u['used_at']}" for u in pool["used"]]
        tu.insert("1.0", "\n".join(used_lines) if used_lines else "(leer)")
        tu.configure(state="disabled")

        ttk.Button(dlg, text="Schließen", command=dlg.destroy).pack(pady=(0, 8))

    # ── Tab: Backup ────────────────────────────────────────────────────

    def _tab_backup(self, nb: ttk.Notebook):
        f = ttk.Frame(nb, padding=16)
        nb.add(f, text="Backup")

        ttk.Label(f, text="Datensicherung",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 6))
        ttk.Label(
            f,
            text="Erstellt eine Sicherungskopie aller Datendateien im Ordner data/backups/.\n"
                 "Gesichert werden: entries.xlsx, suppliers.xlsx, fob_kalkulation.xlsx, "
                 "users.xlsx sowie local.db (falls vorhanden).",
            wraplength=460,
        ).pack(anchor=tk.W, pady=(0, 14))

        self._backup_status = tk.StringVar(value="")
        ttk.Label(f, textvariable=self._backup_status,
                  foreground="gray", font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(0, 8))

        ttk.Button(f, text="Backup jetzt erstellen",
                   command=self._run_backup).pack(anchor=tk.W)

    def _run_backup(self):
        from src.utils.constants import DATA_DIR
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(DATA_DIR, "backups")
        os.makedirs(backup_dir, exist_ok=True)

        backed_up = []
        for filename in ("entries.xlsx", "suppliers.xlsx", "fob_kalkulation.xlsx",
                         "users.xlsx", "local.db"):
            src = os.path.join(DATA_DIR, filename)
            if os.path.exists(src):
                ext = os.path.splitext(filename)[1]
                base = os.path.splitext(filename)[0]
                dst = os.path.join(backup_dir, f"{base}_{timestamp}{ext}")
                shutil.copy2(src, dst)
                backed_up.append(filename)

        if backed_up:
            self._backup_status.set(
                f"Zuletzt gesichert: {datetime.now().strftime('%d.%m.%Y %H:%M')} "
                f"({len(backed_up)} Dateien)"
            )
            messagebox.showinfo(
                "Backup erstellt",
                f"Backup erfolgreich erstellt in:\n{backup_dir}\n\n"
                f"Gesicherte Dateien:\n" + "\n".join(f"  • {f}" for f in backed_up),
                parent=self.dialog,
            )
        else:
            messagebox.showwarning("Backup", "Keine Datendateien gefunden.", parent=self.dialog)

    # ── PIN change ─────────────────────────────────────────────────────

    def _change_pin(self):
        cur  = self._v["pin_cur"].get()
        new  = self._v["pin_new"].get()
        conf = self._v["pin_conf"].get()

        if not new:
            return

        cfg = configparser.ConfigParser()
        cfg.read(_CONFIG_PATH, encoding="utf-8")
        stored = cfg.get("Admin", "pin_hash", fallback=_hash(_DEFAULT_PIN))

        if _hash(cur) != stored:
            messagebox.showerror("Fehler", "Aktueller PIN ist falsch.", parent=self.dialog)
            return
        if new != conf:
            messagebox.showerror("Fehler", "Neuer PIN und Bestätigung stimmen nicht überein.",
                                 parent=self.dialog)
            return
        if len(new) < 4:
            messagebox.showerror("Fehler", "PIN muss mindestens 4 Zeichen lang sein.",
                                 parent=self.dialog)
            return

        if not cfg.has_section("Admin"):
            cfg.add_section("Admin")
        cfg.set("Admin", "pin_hash", _hash(new))
        with open(_CONFIG_PATH, "w", encoding="utf-8") as fh:
            cfg.write(fh)

        for k in ("pin_cur", "pin_new", "pin_conf"):
            self._v[k].set("")
        messagebox.showinfo("Gespeichert", "PIN erfolgreich geändert.", parent=self.dialog)

    # ── Save all settings ──────────────────────────────────────────────

    def _save(self):
        try:
            warn_days = int(self._v["warn_days"].get())
        except ValueError:
            messagebox.showwarning("Fehler", "Frühwarnzeit muss eine ganze Zahl sein.",
                                   parent=self.dialog)
            return

        cfg = configparser.ConfigParser()
        cfg.read(_CONFIG_PATH, encoding="utf-8")

        def ensure(section):
            if not cfg.has_section(section):
                cfg.add_section(section)

        ensure("Import")
        cfg.set("Import", "csv_path", self._v["csv_path"].get().strip())
        cfg.set("Import", "articles_csv_path", self._v["articles_csv_path"].get().strip())

        ensure("SMTP")
        cfg.set("SMTP", "enabled",      str(self._v["smtp_enabled"].get()).lower())
        cfg.set("SMTP", "server",       self._v["smtp_server"].get().strip())
        cfg.set("SMTP", "port",         self._v["smtp_port"].get().strip() or "587")
        cfg.set("SMTP", "use_tls",      str(self._v["smtp_tls"].get()).lower())
        cfg.set("SMTP", "username",     self._v["smtp_user"].get())
        cfg.set("SMTP", "password",     self._v["smtp_pass"].get())
        cfg.set("SMTP", "from_address", self._v["smtp_from"].get().strip())
        cfg.set("SMTP", "to_address",   self._v["smtp_to"].get().strip())

        ensure("Documents")
        cfg.set("Documents", "base_folder", self._v["doc_folder"].get().strip())

        ensure("Reminders")
        cfg.set("Reminders", "warn_days_before", str(warn_days))

        ensure("FOB")
        cfg.set("FOB", "eur_usd",         self._v["fob_eur_usd"].get().strip())
        cfg.set("FOB", "eur_rmb",         self._v["fob_eur_rmb"].get().strip())
        cfg.set("FOB", "fracht_40hc",     self._v["fob_fracht_40hc"].get().strip())
        cfg.set("FOB", "fracht_20",       self._v["fob_fracht_20"].get().strip())
        cfg.set("FOB", "zinssatz_pa",     self._v["fob_zinssatz_pa"].get().strip())
        cfg.set("FOB", "frachtzeit_tage", self._v["fob_frachtzeit"].get().strip())
        cfg.set("FOB", "rekla_quote",     self._v["fob_rekla_quote"].get().strip())

        with open(_CONFIG_PATH, "w", encoding="utf-8") as fh:
            cfg.write(fh)

        messagebox.showinfo("Gespeichert", "Einstellungen wurden gespeichert.",
                            parent=self.dialog)
        self.dialog.destroy()
