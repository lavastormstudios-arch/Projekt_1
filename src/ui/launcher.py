import os
import tkinter as tk

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

        self._center_window(620, 480)
        self._build_ui()

    def run(self):
        self.root.mainloop()

    def _center_window(self, w, h):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

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

            # Scale to 72 px tall, keep aspect ratio
            target_h = 72
            target_w = int(target_h * img.width / img.height)
            img = img.resize((target_w, target_h), Image.LANCZOS)

            # Composite transparent logo onto the header background colour
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
        card_area.pack(fill="both", expand=True, padx=30, pady=28)

        card_area.columnconfigure(0, weight=1)
        card_area.columnconfigure(1, weight=1)
        card_area.columnconfigure(2, weight=1)
        card_area.rowconfigure(0, weight=1)

        modules = [
            {
                "icon": "🔧",
                "title": "WKZ & Bonus",
                "desc": "Konditionserfassung\nund Auswertung",
                "enabled": True,
                "command": self._open_wkz_bonus,
            },
            {
                "icon": "📦",
                "title": "FOB-Kalkulation",
                "desc": "Preiskalkulation\nfür FOB-Importe",
                "enabled": False,
                "command": None,
            },
            {
                "icon": "🤝",
                "title": "Lieferanten-\nmanagement",
                "desc": "Lieferantenpflege\nund Bewertung",
                "enabled": True,
                "command": self._open_lieferanten,
            },
        ]

        for col, mod in enumerate(modules):
            self._make_card(card_area, col, mod)

    def _make_card(self, parent, col, mod):
        enabled = mod["enabled"]
        bg = self.CARD_ACTIVE if enabled else self.CARD_DISABLED
        cursor = "hand2" if enabled else ""

        card = tk.Frame(parent, bg=bg, relief="flat", bd=0)
        card.grid(row=0, column=col, padx=8, sticky="nsew")

        # Inner padding frame
        inner = tk.Frame(card, bg=bg)
        inner.pack(expand=True, fill="both", padx=16, pady=20)

        icon_lbl = tk.Label(inner, text=mod["icon"], bg=bg, fg="white",
                            font=("Segoe UI Emoji", 28))
        icon_lbl.pack(pady=(0, 8))

        title_lbl = tk.Label(inner, text=mod["title"], bg=bg, fg="white",
                             font=("Segoe UI", 13, "bold"), justify="center")
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

        tk.Label(footer, text="v1.0  ·  Werkzeuge Suite",
                 bg=self.BG, fg="#9AA5B4", font=("Segoe UI", 8)).pack(side=tk.LEFT)

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
        from src.ui.main_window import MainWindow  # deferred import
        app = MainWindow()
        app.run()

    def _open_lieferanten(self):
        self.root.destroy()
        from src.ui.supplier_window import SupplierWindow
        app = SupplierWindow()
        app.run()

    def _open_admin(self):
        from src.ui.admin_dialog import AdminDialog
        AdminDialog(self.root)
