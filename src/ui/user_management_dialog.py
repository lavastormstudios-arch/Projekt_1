import tkinter as tk
from tkinter import ttk, messagebox

from src.models.user import User
from src.utils.constants import DEPARTMENTS, ROLES, MODULES, ACTION_PERMISSIONS


_PERM_LABELS = {
    "can_edit":    "Bearbeiten",
    "can_delete":  "Löschen",
    "can_invoice": "Rechnungen",
    "can_export":  "Exportieren",
    "can_import":  "Importieren",
    "is_admin":    "Admin",
}


class UserManagementDialog:
    def __init__(self, parent: tk.Misc, auth_service):
        self._auth = auth_service

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Benutzerverwaltung")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        w, h = 700, 480
        self.dialog.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.dialog.geometry(f"{w}x{h}+{x}+{y}")

        nb = ttk.Notebook(self.dialog)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._tab_users(nb)
        self._tab_permissions(nb)

        ttk.Button(self.dialog, text="Schließen",
                   command=self.dialog.destroy).pack(pady=(0, 8))

    # ------------------------------------------------------------------
    # Tab 1: Benutzer
    # ------------------------------------------------------------------

    def _tab_users(self, nb: ttk.Notebook):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="Benutzer")

        # Treeview
        cols = ("username", "display_name", "department", "role", "active")
        tree_frame = ttk.Frame(f)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self._user_tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                       selectmode="browse")
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                            command=self._user_tree.yview)
        self._user_tree.configure(yscrollcommand=vsb.set)

        headers = {
            "username":     ("Benutzername",  140),
            "display_name": ("Name",          160),
            "department":   ("Abteilung",     90),
            "role":         ("Rolle",         110),
            "active":       ("Aktiv",         50),
        }
        for col, (text, width) in headers.items():
            self._user_tree.heading(col, text=text)
            self._user_tree.column(col, width=width, minwidth=40, anchor=tk.W)

        self._user_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        btn_row = ttk.Frame(f)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_row, text="Hinzufügen", command=self._add_user).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Bearbeiten", command=self._edit_user).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Löschen",   command=self._delete_user).pack(side=tk.LEFT, padx=4)

        self._refresh_users()

    def _refresh_users(self):
        self._user_tree.delete(*self._user_tree.get_children())
        for u in self._auth.get_all_users():
            active_str = "Ja" if u.active else "Nein"
            self._user_tree.insert("", tk.END, iid=u.username,
                                   values=(u.username, u.display_name,
                                           u.department, u.role, active_str))

    def _selected_username(self) -> str | None:
        sel = self._user_tree.selection()
        return sel[0] if sel else None

    def _add_user(self):
        UserFormDialog(self.dialog, self._auth, user=None,
                       on_save=self._refresh_users)

    def _edit_user(self):
        username = self._selected_username()
        if not username:
            messagebox.showinfo("Hinweis", "Bitte einen Benutzer auswählen.",
                                parent=self.dialog)
            return
        users = {u.username: u for u in self._auth.get_all_users()}
        user = users.get(username)
        if user:
            UserFormDialog(self.dialog, self._auth, user=user,
                           on_save=self._refresh_users)

    def _delete_user(self):
        username = self._selected_username()
        if not username:
            messagebox.showinfo("Hinweis", "Bitte einen Benutzer auswählen.",
                                parent=self.dialog)
            return
        if messagebox.askyesno("Löschen",
                               f"Benutzer '{username}' wirklich löschen?",
                               parent=self.dialog):
            self._auth.delete_user(username)
            self._refresh_users()

    # ------------------------------------------------------------------
    # Tab 2: Berechtigungen
    # ------------------------------------------------------------------

    def _tab_permissions(self, nb: ttk.Notebook):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="Berechtigungen")

        perm_nb = ttk.Notebook(f)
        perm_nb.pack(fill=tk.BOTH, expand=True)

        self._tab_module_access(perm_nb)
        self._tab_action_rights(perm_nb)

    # ── Modulzugriff ───────────────────────────────────────────────────

    def _tab_module_access(self, nb: ttk.Notebook):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="Modulzugriff")

        matrix = self._auth.get_module_access()
        self._mod_vars: dict[str, dict[str, tk.BooleanVar]] = {}

        # Header row
        for j, mod in enumerate(MODULES):
            ttk.Label(f, text=mod, font=("Segoe UI", 9, "bold")).grid(
                row=0, column=j + 1, padx=8, pady=(0, 6), sticky=tk.W)

        for i, dept in enumerate(DEPARTMENTS, start=1):
            ttk.Label(f, text=dept).grid(row=i, column=0, sticky=tk.W,
                                         padx=(0, 16), pady=3)
            self._mod_vars[dept] = {}
            for j, mod in enumerate(MODULES, start=1):
                val = matrix.get(dept, {}).get(mod, False)
                var = tk.BooleanVar(value=val)
                self._mod_vars[dept][mod] = var
                ttk.Checkbutton(f, variable=var).grid(row=i, column=j, padx=8)

        ttk.Button(f, text="Speichern", command=self._save_module_access).grid(
            row=len(DEPARTMENTS) + 1, column=0, columnspan=len(MODULES) + 1,
            pady=(14, 0))

    def _save_module_access(self):
        matrix = {
            dept: {mod: self._mod_vars[dept][mod].get() for mod in MODULES}
            for dept in DEPARTMENTS
        }
        self._auth._store.save_module_access(matrix)
        messagebox.showinfo("Gespeichert", "Modulzugriff gespeichert.",
                            parent=self.dialog)

    # ── Aktionsrechte ──────────────────────────────────────────────────

    def _tab_action_rights(self, nb: ttk.Notebook):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="Aktionsrechte")

        matrix = self._auth.get_action_rights()
        self._act_vars: dict[str, dict[str, tk.BooleanVar]] = {}

        # Header row
        for j, perm in enumerate(ACTION_PERMISSIONS):
            ttk.Label(f, text=_PERM_LABELS.get(perm, perm),
                      font=("Segoe UI", 9, "bold")).grid(
                row=0, column=j + 1, padx=6, pady=(0, 6), sticky=tk.W)

        for i, role in enumerate(ROLES, start=1):
            ttk.Label(f, text=role).grid(row=i, column=0, sticky=tk.W,
                                         padx=(0, 16), pady=3)
            self._act_vars[role] = {}
            for j, perm in enumerate(ACTION_PERMISSIONS, start=1):
                val = matrix.get(role, {}).get(perm, False)
                var = tk.BooleanVar(value=val)
                self._act_vars[role][perm] = var
                ttk.Checkbutton(f, variable=var).grid(row=i, column=j, padx=6)

        ttk.Button(f, text="Speichern", command=self._save_action_rights).grid(
            row=len(ROLES) + 1, column=0,
            columnspan=len(ACTION_PERMISSIONS) + 1, pady=(14, 0))

    def _save_action_rights(self):
        matrix = {
            role: {perm: self._act_vars[role][perm].get()
                   for perm in ACTION_PERMISSIONS}
            for role in ROLES
        }
        self._auth._store.save_action_rights(matrix)
        messagebox.showinfo("Gespeichert", "Aktionsrechte gespeichert.",
                            parent=self.dialog)


# ---------------------------------------------------------------------------
# User form dialog
# ---------------------------------------------------------------------------

class UserFormDialog:
    def __init__(self, parent, auth_service, user: User | None, on_save):
        self._auth = auth_service
        self._user = user
        self._is_edit = user is not None
        self._on_save = on_save

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Benutzer bearbeiten" if self._is_edit else "Neuer Benutzer")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        w, h = 380, 280
        self.dialog.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.dialog.geometry(f"{w}x{h}+{x}+{y}")

        self._vars: dict[str, tk.Variable] = {}
        self._build()
        if self._is_edit:
            self._populate()

    def _build(self):
        f = ttk.Frame(self.dialog, padding=16)
        f.pack(fill=tk.BOTH, expand=True)

        rows = [
            ("username",     "Benutzername (Windows-Login):"),
            ("display_name", "Anzeigename:"),
        ]
        for i, (key, label) in enumerate(rows):
            ttk.Label(f, text=label).grid(row=i, column=0, sticky=tk.W, pady=4)
            self._vars[key] = tk.StringVar()
            entry = ttk.Entry(f, textvariable=self._vars[key], width=28)
            entry.grid(row=i, column=1, padx=8, pady=4, sticky=tk.W)
            if self._is_edit and key == "username":
                entry.configure(state="disabled")

        row = len(rows)
        ttk.Label(f, text="Abteilung:").grid(row=row, column=0, sticky=tk.W, pady=4)
        self._vars["department"] = tk.StringVar()
        ttk.Combobox(f, textvariable=self._vars["department"],
                     values=DEPARTMENTS, state="readonly",
                     width=26).grid(row=row, column=1, padx=8, pady=4, sticky=tk.W)

        row += 1
        ttk.Label(f, text="Rolle:").grid(row=row, column=0, sticky=tk.W, pady=4)
        self._vars["role"] = tk.StringVar()
        ttk.Combobox(f, textvariable=self._vars["role"],
                     values=ROLES, state="readonly",
                     width=26).grid(row=row, column=1, padx=8, pady=4, sticky=tk.W)

        row += 1
        self._vars["active"] = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text="Aktiv", variable=self._vars["active"]).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=4)

        row += 1
        btn_row = ttk.Frame(f)
        btn_row.grid(row=row, column=0, columnspan=2, pady=(14, 0))
        ttk.Button(btn_row, text="Speichern", command=self._save, width=12).pack(
            side=tk.LEFT, padx=6)
        ttk.Button(btn_row, text="Abbrechen", command=self.dialog.destroy,
                   width=12).pack(side=tk.LEFT, padx=6)

    def _populate(self):
        u = self._user
        self._vars["username"].set(u.username)
        self._vars["display_name"].set(u.display_name)
        self._vars["department"].set(u.department)
        self._vars["role"].set(u.role)
        self._vars["active"].set(u.active)

    def _save(self):
        username = self._vars["username"].get().strip()
        if not username:
            messagebox.showwarning("Fehler", "Benutzername darf nicht leer sein.",
                                   parent=self.dialog)
            return
        department = self._vars["department"].get()
        if not department:
            messagebox.showwarning("Fehler", "Bitte eine Abteilung wählen.",
                                   parent=self.dialog)
            return
        role = self._vars["role"].get()
        if not role:
            messagebox.showwarning("Fehler", "Bitte eine Rolle wählen.",
                                   parent=self.dialog)
            return

        user = User(
            username=username.lower(),
            display_name=self._vars["display_name"].get().strip(),
            department=department,
            role=role,
            active=self._vars["active"].get(),
        )
        if self._is_edit:
            self._auth.update_user(user)
        else:
            self._auth.add_user(user)

        self.dialog.destroy()
        self._on_save()
