import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "assets")
_LOGO_PATH = os.path.join(_ASSETS_DIR, "201_Berger_Logo_blau.png")


class LauncherWindow:
    # Color tokens
    BG = "#F0F2F5"
    HEADER_BG = "#2B3A52"
    CARD_ACTIVE = "#4472C4"
    CARD_HOVER = "#3461B0"
    CARD_DISABLED = "#9E9E9E"
    BADGE_BG = "#BDBDBD"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Werkzeuge")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG)

        # Auth
        import configparser as _cp
        _cfg = _cp.ConfigParser()
        _cfg.read(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "config.ini"))
        _db_url = _cfg.get("Database", "url", fallback="").strip() or None
        if _db_url:
            from src.data.database_store import DatabaseStore
            self.store = DatabaseStore(_db_url)
        else:
            from src.data.excel_store import ExcelStore
            self.store = ExcelStore()

        from src.services.auth_service import AuthService
        self.auth_service = AuthService(self.store)

        # Bootstrap check
        if self.auth_service.needs_bootstrap():
            self._run_bootstrap()

        # Authenticate
        self.current_user = self.auth_service.authenticate()
        if self.current_user is None:
            self.root.withdraw()
            messagebox.showerror(
                "Kein Zugang",
                "Ihr Windows-Benutzer ist nicht berechtigt, dieses Programm zu verwenden.\n\n"
                "Bitte wenden Sie sich an den Systemadministrator."
            )
            self.root.destroy()
            sys.exit()

        self.permissions = self.auth_service.get_permissions(self.current_user)

        self._center_window(920, 520)
        self._build_ui()

    def run(self):
        from src.utils.updater import check_for_update
        self.root.after(500, lambda: check_for_update(self.root))
        self.root.mainloop()

    def _center_window(self, w, h):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------------
    # Bootstrap dialog
    # ------------------------------------------------------------------

    def _run_bootstrap(self):
        """Show first-run dialog to create the first admin user."""
        win_user = self.auth_service.get_windows_username()

        dlg = tk.Toplevel(self.root)
        dlg.title("Ersteinrichtung")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        w, h = 420, 220
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        dlg.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        f = ttk.Frame(dlg, padding=20)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text="Ersteinrichtung",
                  font=("Segoe UI", 12, "bold")).pack(pady=(0, 6))
        ttk.Label(f, text="Bitte Admin-Benutzernamen und Anzeigenamen eingeben.",
                  wraplength=360).pack(pady=(0, 10))

        form = ttk.Frame(f)
        form.pack(fill=tk.X)

        ttk.Label(form, text="Benutzername:").grid(row=0, column=0, sticky=tk.W, pady=4)
        username_var = tk.StringVar(value=win_user)
        ttk.Entry(form, textvariable=username_var, width=28).grid(
            row=0, column=1, padx=8, pady=4)

        ttk.Label(form, text="Anzeigename:").grid(row=1, column=0, sticky=tk.W, pady=4)
        name_var = tk.StringVar(value=win_user)
        ttk.Entry(form, textvariable=name_var, width=28).grid(
            row=1, column=1, padx=8, pady=4)

        def do_bootstrap():
            username = username_var.get().strip()
            display_name = name_var.get().strip()
            if not username:
                messagebox.showwarning("Fehler", "Benutzername darf nicht leer sein.",
                                       parent=dlg)
                return
            self.auth_service.bootstrap_first_admin(username, display_name)
            dlg.destroy()

        ttk.Button(f, text="Admin anlegen", command=do_bootstrap).pack(pady=(14, 0))
        self.root.wait_window(dlg)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self._build_header()
        self._build_cards()
        self._build_footer()

    def _build_header(self):
        header = tk.Frame(self.root, bg=self.HEADER_BG, height=110)
        header.pack(fill="x")
        header.pack_propagate(False)

        logo_shown = False
        try:
            from PIL import Image, ImageTk
            img = Image.open(_LOGO_PATH).convert("RGBA")

            target_h = 72
            target_w = int(target_h * img.width / img.height)
            img = img.resize((target_w, target_h), Image.LANCZOS)

            hx = self.HEADER_BG.lstrip("#")
            bg_color = (int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16), 255)
            bg = Image.new("RGBA", img.size, bg_color)
            composed = Image.alpha_composite(bg, img)

            self._logo_photo = ImageTk.PhotoImage(composed.convert("RGB"))
            tk.Label(header, image=self._logo_photo,
                     bg=self.HEADER_BG).place(relx=0.5, rely=0.44, anchor="center")
            logo_shown = True
        except Exception:
            pass

        if not logo_shown:
            tk.Label(header, text="Category Management Tool",
                     bg=self.HEADER_BG, fg="white",
                     font=("Segoe UI", 22, "bold")).place(
                relx=0.5, rely=0.38, anchor="center")

        tk.Label(header, text="Wählen Sie ein Modul",
                 bg=self.HEADER_BG, fg="#A9B8CC",
                 font=("Segoe UI", 10)).place(relx=0.5, rely=0.84, anchor="center")

    def _build_cards(self):
        card_area = tk.Frame(self.root, bg=self.BG)
        card_area.pack(fill="both", expand=True, padx=24, pady=24)

        p = self.permissions

        modules = []
        if p.can_view_wkz_bonus:
            modules.append({
                "icon": "🔧",
                "title": "WKZ & Bonus",
                "desc": "Konditionserfassung\nund Auswertung",
                "enabled": True,
                "command": self._open_wkz_bonus,
            })
        if p.can_view_fob_kalkulation:
            modules.append({
                "icon": "📦",
                "title": "FOB-Kalkulation",
                "desc": "Preiskalkulation\nfür FOB-Importe",
                "enabled": True,
                "command": self._open_fob_kalkulation,
            })
        else:
            modules.append({
                "icon": "📦",
                "title": "FOB-Kalkulation",
                "desc": "Preiskalkulation\nfür FOB-Importe",
                "enabled": False,
                "command": None,
            })
        modules.append({
            "icon": "📣",
            "title": "Kampagnen",
            "desc": "Kampagnenplanung\nund Verwaltung",
            "enabled": False,
            "command": None,
        })
        modules.append({
            "icon": "📺",
            "title": "Retail Media",
            "desc": "Retail Media\nVerwaltung",
            "enabled": False,
            "command": None,
        })
        if p.can_view_lieferanten:
            modules.append({
                "icon": "🤝",
                "title": "Lieferantenmanagement",
                "desc": "Lieferantenpflege\nund Bewertung",
                "enabled": True,
                "command": self._open_lieferanten,
            })

        # If no visible modules, show a placeholder card
        if not modules:
            modules.append({
                "icon": "🔒",
                "title": "Kein Zugang",
                "desc": "Keine Module\nfreigeschaltet",
                "enabled": False,
                "command": None,
            })

        for col in range(len(modules)):
            card_area.columnconfigure(col, weight=1)
        card_area.rowconfigure(0, weight=1)

        for col, mod in enumerate(modules):
            self._make_card(card_area, col, mod)

    def _make_card(self, parent, col, mod):
        enabled = mod["enabled"]
        bg = self.CARD_ACTIVE if enabled else self.CARD_DISABLED
        cursor = "hand2" if enabled else ""

        card = tk.Frame(parent, bg=bg, relief="flat", bd=0)
        card.grid(row=0, column=col, padx=8, sticky="nsew")

        inner = tk.Frame(card, bg=bg)
        inner.pack(expand=True, fill="both", padx=16, pady=20)

        icon_lbl = tk.Label(inner, text=mod["icon"], bg=bg, fg="white",
                            font=("Segoe UI Emoji", 28))
        icon_lbl.pack(pady=(0, 8))

        title_lbl = tk.Label(inner, text=mod["title"], bg=bg, fg="white",
                             font=("Segoe UI", 13, "bold"), justify="center",
                             wraplength=160)
        title_lbl.pack()

        desc_lbl = tk.Label(inner, text=mod["desc"], bg=bg, fg="#DDEEFF",
                            font=("Segoe UI", 9), justify="center")
        desc_lbl.pack(pady=(4, 0))

        if not enabled:
            badge_frame = tk.Frame(inner, bg=self.BADGE_BG)
            badge_frame.pack(pady=(10, 0))
            tk.Label(badge_frame, text="Demnächst verfügbar",
                     bg=self.BADGE_BG, fg="#444444",
                     font=("Segoe UI", 8)).pack(padx=6, pady=3)

        if enabled:
            command = mod.get("command") or self._open_wkz_bonus
            all_widgets = [card, inner, icon_lbl, title_lbl, desc_lbl]
            for w in all_widgets:
                w.configure(cursor=cursor)
                w.bind("<Enter>", lambda e, c=card: self._on_enter(c))
                w.bind("<Leave>", lambda e, c=card: self._on_leave(c))
                w.bind("<Button-1>", lambda e, cmd=command: cmd())

    def _build_footer(self):
        sep = tk.Frame(self.root, bg="#CDD2DA", height=1)
        sep.pack(fill="x")

        footer = tk.Frame(self.root, bg=self.BG)
        footer.pack(fill="x", padx=14, pady=5)

        # Display logged-in user
        user_text = f"Angemeldet: {self.current_user.display_name or self.current_user.username}"
        tk.Label(footer, text=f"v1.1  ·  Berger Management Tool by Marc Lill  ·  {user_text}",
                 bg=self.BG, fg="#9AA5B4", font=("Segoe UI", 8)).pack(side=tk.LEFT)

        if self.permissions.is_admin:
            admin_lbl = tk.Label(footer, text="🔒  Admin",
                                 bg=self.BG, fg="#9AA5B4",
                                 font=("Segoe UI", 8), cursor="hand2")
            admin_lbl.pack(side=tk.RIGHT)
            admin_lbl.bind("<Enter>", lambda e: admin_lbl.config(fg="#4472C4"))
            admin_lbl.bind("<Leave>", lambda e: admin_lbl.config(fg="#9AA5B4"))
            admin_lbl.bind("<Button-1>", lambda e: self._open_admin())

    # ------------------------------------------------------------------
    # Hover handlers
    # ------------------------------------------------------------------

    def _on_enter(self, card):
        self._recolor(card, self.CARD_HOVER)

    def _on_leave(self, card):
        self._recolor(card, self.CARD_ACTIVE)

    def _recolor(self, widget, color):
        try:
            widget.configure(bg=color)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._recolor(child, color)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _open_wkz_bonus(self):
        self.root.destroy()
        from src.ui.main_window import MainWindow
        app = MainWindow(current_user=self.current_user,
                         permissions=self.permissions)
        app.run()

    def _open_fob_kalkulation(self):
        self.root.destroy()
        from src.ui.fob_window import FobWindow
        app = FobWindow(current_user=self.current_user,
                        permissions=self.permissions)
        app.run()

    def _open_lieferanten(self):
        self.root.destroy()
        from src.ui.supplier_window import SupplierWindow
        app = SupplierWindow(current_user=self.current_user,
                             permissions=self.permissions)
        app.run()

    def _open_admin(self):
        from src.ui.admin_dialog import AdminDialog
        AdminDialog(self.root, self.auth_service)
