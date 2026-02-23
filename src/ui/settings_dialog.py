import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import configparser
import os


class SettingsDialog:
    def __init__(self, parent, app):
        self.app = app
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.ini")

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Einstellungen")
        self.dialog.geometry("450x500")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._build()

    def _build(self):
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # SMTP Tab
        smtp_frame = ttk.Frame(notebook, padding=15)
        notebook.add(smtp_frame, text="E-Mail (SMTP)")

        es = self.app.email_service

        self.enabled_var = tk.BooleanVar(value=es.enabled)
        ttk.Checkbutton(smtp_frame, text="E-Mail-Versand aktiviert", variable=self.enabled_var).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=5)

        fields = [
            ("server", "SMTP-Server:", es.server),
            ("port", "Port:", str(es.port)),
            ("username", "Benutzername:", es.username),
            ("password", "Passwort:", es.password),
            ("from_addr", "Absender:", es.from_address),
            ("to_addr", "Empfänger:", es.to_address),
        ]
        self._smtp_vars = {}
        for i, (key, label, value) in enumerate(fields, 1):
            ttk.Label(smtp_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=3)
            self._smtp_vars[key] = tk.StringVar(value=value)
            show = "*" if key == "password" else None
            ttk.Entry(smtp_frame, textvariable=self._smtp_vars[key], width=30, show=show).grid(
                row=i, column=1, padx=10, pady=3)

        self.tls_var = tk.BooleanVar(value=es.use_tls)
        ttk.Checkbutton(smtp_frame, text="TLS verwenden", variable=self.tls_var).grid(
            row=len(fields) + 1, column=0, columnspan=2, sticky=tk.W, pady=5)

        btn_row = len(fields) + 2
        ttk.Button(smtp_frame, text="Test-E-Mail senden", command=self._send_test).grid(
            row=btn_row, column=0, columnspan=2, pady=10)

        # Reminders Tab
        rem_frame = ttk.Frame(notebook, padding=15)
        notebook.add(rem_frame, text="Erinnerungen")

        ttk.Label(rem_frame, text="Warnzeit (Tage vor Frist):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.warn_days_var = tk.StringVar(value=str(self.app.reminder_service.warn_days))
        ttk.Entry(rem_frame, textvariable=self.warn_days_var, width=10).grid(
            row=0, column=1, padx=10, pady=5, sticky=tk.W)

        # Import Tab
        import_frame = ttk.Frame(notebook, padding=15)
        notebook.add(import_frame, text="Import")

        ttk.Label(import_frame, text="CSV-Importpfad:", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        ttk.Label(import_frame, text="Pfad zur CSV-Datei mit Lieferanten und Einkaufsumsatz.\n"
                  "Die CSV wird beim Start automatisch importiert.").grid(
            row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        self.csv_path_var = tk.StringVar(value=self._load_csv_path())
        path_frame = ttk.Frame(import_frame)
        path_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=5)
        ttk.Entry(path_frame, textvariable=self.csv_path_var, width=35).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(path_frame, text="Durchsuchen...", command=self._browse_csv).pack(side=tk.LEFT)

        # Save / Cancel
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Speichern", command=self._save).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Abbrechen", command=self.dialog.destroy).pack(side=tk.LEFT, padx=10)

    def _load_csv_path(self) -> str:
        config = configparser.ConfigParser()
        config.read(self.config_path, encoding="utf-8")
        return config.get("Import", "csv_path", fallback="")

    def _browse_csv(self):
        path = filedialog.askopenfilename(
            title="CSV-Datei auswählen",
            filetypes=[("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*")]
        )
        if path:
            self.csv_path_var.set(path)

    def _save_csv_path(self, path: str):
        config = configparser.ConfigParser()
        config.read(self.config_path, encoding="utf-8")
        if not config.has_section("Import"):
            config.add_section("Import")
        config.set("Import", "csv_path", path)
        with open(self.config_path, "w", encoding="utf-8") as f:
            config.write(f)

    def _send_test(self):
        self._apply_smtp()
        result = self.app.email_service.send_test()
        messagebox.showinfo("Test", result)

    def _apply_smtp(self):
        self.app.email_service.save_config(
            server=self._smtp_vars["server"].get(),
            port=int(self._smtp_vars["port"].get() or 587),
            use_tls=self.tls_var.get(),
            username=self._smtp_vars["username"].get(),
            password=self._smtp_vars["password"].get(),
            from_addr=self._smtp_vars["from_addr"].get(),
            to_addr=self._smtp_vars["to_addr"].get(),
            enabled=self.enabled_var.get(),
        )

    def _save(self):
        self._apply_smtp()

        try:
            warn_days = int(self.warn_days_var.get())
            self.app.reminder_service.warn_days = warn_days
        except ValueError:
            messagebox.showwarning("Fehler", "Ungültiger Wert für Warnzeit.")
            return

        # Save CSV import path
        self._save_csv_path(self.csv_path_var.get().strip())

        messagebox.showinfo("Gespeichert", "Einstellungen wurden gespeichert.")
        self.dialog.destroy()
