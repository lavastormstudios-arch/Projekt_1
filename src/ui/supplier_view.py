import os
import re
import shutil
import configparser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date

from src.models.supplier import Supplier

DOC_CATEGORIES = [
    "Lieferantengespräche",
    "Lieferantenvertrag",
    "Konditionen",
    "Preislisten",
    "Informationen",
    "WKZ & Bonusrechnungen",
]

# Project root is three levels up from this file (src/ui/supplier_view.py)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_PROJECT_ROOT, "config.ini")


def _safe_folder_name(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()


class SupplierPage:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.frame = ttk.Frame(parent)
        self._all_suppliers = []
        self._selected_supplier = None
        self._search_var: tk.StringVar = tk.StringVar()
        # Maps category name → ttk.Treeview for that tab
        self._cat_trees: dict[str, ttk.Treeview] = {}
        self._all_files_tree: ttk.Treeview | None = None
        self._notebook: ttk.Notebook | None = None
        self._name_label: ttk.Label | None = None
        self._path_var: tk.StringVar = tk.StringVar()
        self._placeholder: ttk.Label | None = None
        self._doc_panel: ttk.Frame | None = None
        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _can(self, perm: str) -> bool:
        if self.app.permissions is None:
            return True
        return bool(getattr(self.app.permissions, perm, True))

    def _build(self):
        paned = ttk.PanedWindow(self.frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # ── Left pane ──────────────────────────────────────────────────
        left = ttk.Frame(paned, width=280)
        left.pack_propagate(False)
        paned.add(left, weight=0)

        ttk.Label(left, text="Lieferantenmanagement",
                  font=("Segoe UI", 13, "bold")).pack(anchor=tk.W, padx=10, pady=(10, 4))

        # Search bar
        search_frame = ttk.Frame(left)
        search_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        ttk.Label(search_frame, text="Suche:").pack(side=tk.LEFT)
        ttk.Entry(search_frame, textvariable=self._search_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
        self._search_var.trace_add("write", lambda *_: self._apply_search())

        tree_frame = ttk.Frame(left)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("name", "country", "contact")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                 selectmode="browse")
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        headers = {
            "name": ("Name", 120),
            "country": ("Land", 50),
            "contact": ("Kontakt", 100),
        }
        for col, (text, width) in headers.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, minwidth=40, anchor=tk.W)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self._on_supplier_select)

        # Supplier CRUD buttons (shown only with edit/delete rights)
        supplier_btn_frame = ttk.Frame(left)
        supplier_btn_frame.pack(fill=tk.X, padx=10, pady=(0, 6))
        if self._can("can_edit"):
            ttk.Button(supplier_btn_frame, text="Neu",
                       command=self._new_supplier).pack(side=tk.LEFT, padx=2)
            ttk.Button(supplier_btn_frame, text="Bearbeiten",
                       command=self._edit_supplier).pack(side=tk.LEFT, padx=2)
        if self._can("can_delete"):
            ttk.Button(supplier_btn_frame, text="Löschen",
                       command=self._delete_supplier).pack(side=tk.LEFT, padx=2)

        # ── Right pane ─────────────────────────────────────────────────
        right = ttk.Frame(paned)
        paned.add(right, weight=1)
        self._build_doc_panel(right)

    def _build_doc_panel(self, parent: ttk.Frame):
        self._doc_panel = parent

        # ── Header row ─────────────────────────────────────────────────
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, padx=12, pady=(10, 4))

        self._name_label = ttk.Label(header_frame, text="",
                                     font=("Segoe UI", 14, "bold"))
        self._name_label.pack(anchor=tk.W)

        # ── Base-folder row ────────────────────────────────────────────
        path_frame = ttk.Frame(parent)
        path_frame.pack(fill=tk.X, padx=12, pady=(0, 6))

        ttk.Label(path_frame, text="Dokumente-Ordner:").pack(side=tk.LEFT)
        ttk.Entry(path_frame, textvariable=self._path_var,
                  state="readonly", width=52).pack(side=tk.LEFT, padx=(6, 0))

        self._path_var.set(self._get_base_folder())

        # ── Notebook ───────────────────────────────────────────────────
        notebook_frame = ttk.Frame(parent)
        notebook_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 4))

        self._notebook = ttk.Notebook(notebook_frame)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        self._build_all_files_tab(self._notebook)
        for cat in DOC_CATEGORIES:
            self._build_category_tab(self._notebook, cat)

        # ── Action buttons ─────────────────────────────────────────────
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, padx=12, pady=(0, 10))

        if self._can("can_edit"):
            ttk.Button(action_frame, text="Dokument hinzufügen",
                       command=self._add_document).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Datei öffnen",
                   command=self._open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Ordner öffnen in Explorer",
                   command=self._open_folder).pack(side=tk.LEFT, padx=2)

        # ── Placeholder (shown when no supplier selected) ───────────────
        self._placeholder = ttk.Label(parent,
                                      text="Bitte einen Lieferanten auswählen.",
                                      font=("Segoe UI", 11),
                                      foreground="gray")
        self._placeholder.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Initial state: hide everything except placeholder
        self._set_panel_visible(False)

    def _build_category_tab(self, notebook: ttk.Notebook, category: str):
        tab_frame = ttk.Frame(notebook)
        notebook.add(tab_frame, text=category)

        columns = ("name", "size", "modified")
        tree_frame = ttk.Frame(tab_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                            selectmode="browse")
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)

        tree.heading("name", text="Dateiname")
        tree.heading("size", text="Größe")
        tree.heading("modified", text="Geändert")
        tree.column("name", width=300, minwidth=100, anchor=tk.W)
        tree.column("size", width=80, minwidth=60, anchor=tk.E)
        tree.column("modified", width=110, minwidth=80, anchor=tk.W)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.bind("<Double-1>", lambda e, c=category: self._open_file(c))

        self._cat_trees[category] = tree

    def _build_all_files_tab(self, notebook: ttk.Notebook):
        tab_frame = ttk.Frame(notebook)
        notebook.add(tab_frame, text="Alle Dateien")

        columns = ("size", "modified")
        tree_frame = ttk.Frame(tab_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self._all_files_tree = ttk.Treeview(tree_frame, columns=columns,
                                             show="tree headings", selectmode="browse")
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                            command=self._all_files_tree.yview)
        self._all_files_tree.configure(yscrollcommand=vsb.set)

        self._all_files_tree.heading("#0",       text="Kategorie / Dateiname")
        self._all_files_tree.heading("size",     text="Größe")
        self._all_files_tree.heading("modified", text="Geändert")

        self._all_files_tree.column("#0",       width=320, minwidth=150, anchor=tk.W)
        self._all_files_tree.column("size",     width=90,  minwidth=60,  anchor=tk.E)
        self._all_files_tree.column("modified", width=110, minwidth=80,  anchor=tk.W)

        self._all_files_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._all_files_tree.bind("<Double-1>", self._open_file_from_all_tab)

    def _refresh_all_files_tab(self):
        if self._all_files_tree is None:
            return
        self._all_files_tree.delete(*self._all_files_tree.get_children())

        for cat in DOC_CATEGORIES:
            folder = self._category_folder(cat)
            files = []
            if os.path.isdir(folder):
                try:
                    for entry in sorted(os.scandir(folder),
                                        key=lambda e: e.name.lower()):
                        if not entry.is_file():
                            continue
                        try:
                            stat = entry.stat()
                            size_kb = stat.st_size / 1024
                            size_str = (f"{size_kb:.1f} KB" if size_kb < 1024
                                        else f"{size_kb/1024:.1f} MB")
                            mtime = datetime.fromtimestamp(
                                stat.st_mtime).strftime("%d.%m.%y")
                        except OSError:
                            size_str = "–"
                            mtime = "–"
                        files.append((entry.path, entry.name, size_str, mtime))
                except OSError:
                    pass

            cat_iid = f"__cat__{cat}"
            cat_label = f"{cat}  ({len(files)})"
            self._all_files_tree.insert("", tk.END, iid=cat_iid,
                                        text=cat_label, values=("", ""),
                                        open=False)
            for path, name, size_str, mtime in files:
                self._all_files_tree.insert(cat_iid, tk.END, iid=path,
                                            text=name, values=(size_str, mtime))

    def _open_file_from_all_tab(self, event=None):
        if self._all_files_tree is None:
            return
        sel = self._all_files_tree.selection()
        if not sel:
            return
        path = sel[0]
        if path.startswith("__cat__"):
            return  # category node clicked
        if not os.path.isfile(path):
            messagebox.showerror("Fehler", "Datei nicht gefunden.")
            return
        try:
            os.startfile(path)
        except OSError as exc:
            messagebox.showerror("Fehler",
                                 f"Datei konnte nicht geöffnet werden:\n{exc}")

    # ------------------------------------------------------------------
    # Visibility helpers
    # ------------------------------------------------------------------

    def _set_panel_visible(self, visible: bool):
        """Show/hide the document panel widgets; show placeholder when hidden."""
        children = self._doc_panel.winfo_children()
        for child in children:
            if child is self._placeholder:
                continue
            if visible:
                child.pack_configure()  # already packed; just ensure not hidden
            # We use .place for placeholder and pack for real widgets,
            # so toggling is done via raise/lower
        if visible:
            self._placeholder.place_forget()
        else:
            self._placeholder.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            self._placeholder.lift()

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    def _get_base_folder(self) -> str:
        cfg = configparser.ConfigParser()
        cfg.read(_CONFIG_PATH, encoding="utf-8")
        path = cfg.get("Documents", "base_folder", fallback="data/documents").strip()
        if not os.path.isabs(path):
            path = os.path.abspath(os.path.join(_PROJECT_ROOT, path))
        return path

    def _save_base_folder(self, path: str):
        cfg = configparser.ConfigParser()
        cfg.read(_CONFIG_PATH, encoding="utf-8")
        if not cfg.has_section("Documents"):
            cfg.add_section("Documents")
        cfg.set("Documents", "base_folder", path)
        with open(_CONFIG_PATH, "w", encoding="utf-8") as fh:
            cfg.write(fh)

    # ------------------------------------------------------------------
    # Folder helpers
    # ------------------------------------------------------------------

    def _supplier_folder(self) -> str:
        if self._selected_supplier is None:
            return ""
        safe = _safe_folder_name(self._selected_supplier.name)
        return os.path.join(self._get_base_folder(), safe)

    def _category_folder(self, category: str) -> str:
        return os.path.join(self._supplier_folder(), category)

    # ------------------------------------------------------------------
    # Active category
    # ------------------------------------------------------------------

    def _active_category(self) -> str | None:
        if self._notebook is None:
            return None
        try:
            tab_id = self._notebook.select()
            if not tab_id:
                return None
            return self._notebook.tab(tab_id, "text")
        except tk.TclError:
            return None

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh_category(self, category: str, tree: ttk.Treeview):
        tree.delete(*tree.get_children())
        folder = self._category_folder(category)
        if not os.path.isdir(folder):
            return
        try:
            entries = os.scandir(folder)
        except OSError:
            return
        for entry in sorted(entries, key=lambda e: e.name.lower()):
            if not entry.is_file():
                continue
            try:
                stat = entry.stat()
                size_kb = stat.st_size / 1024
                size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%y")
            except OSError:
                size_str = "–"
                mtime = "–"
            tree.insert("", tk.END, iid=entry.path,
                        values=(entry.name, size_str, mtime))

    def _refresh_all_categories(self):
        for cat, tree in self._cat_trees.items():
            self._refresh_category(cat, tree)
        self._refresh_all_files_tab()

    # ------------------------------------------------------------------
    # Supplier selection
    # ------------------------------------------------------------------

    def _on_supplier_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            self._selected_supplier = None
            self._name_label.config(text="")
            self._set_panel_visible(False)
            return

        supplier_id = sel[0]
        self._selected_supplier = self.app.supplier_service.get_by_id(supplier_id)
        if self._selected_supplier is None:
            self._set_panel_visible(False)
            return

        self._name_label.config(text=self._selected_supplier.name)
        self._set_panel_visible(True)
        self._refresh_all_categories()

    # ------------------------------------------------------------------
    # Supplier CRUD
    # ------------------------------------------------------------------

    def _new_supplier(self):
        SupplierFormDialog(self.frame.winfo_toplevel(), self.app, supplier=None)

    def _edit_supplier(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Hinweis", "Bitte einen Lieferanten auswählen.")
            return
        supplier = self.app.supplier_service.get_by_id(sel[0])
        if supplier:
            SupplierFormDialog(self.frame.winfo_toplevel(), self.app, supplier=supplier)

    def _delete_supplier(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Hinweis", "Bitte einen Lieferanten auswählen.")
            return
        supplier = self.app.supplier_service.get_by_id(sel[0])
        name = supplier.name if supplier else sel[0]
        if messagebox.askyesno("Löschen", f"Lieferant '{name}' wirklich löschen?"):
            self.app.supplier_service.delete(sel[0])
            self._selected_supplier = None
            self._set_panel_visible(False)
            self.refresh()

    # ------------------------------------------------------------------
    # Document actions
    # ------------------------------------------------------------------

    def _ask_category(self) -> str | None:
        """Show a dialog to pick a document category. Returns the chosen category or None."""
        current = self._active_category() or DOC_CATEGORIES[0]
        result = [None]

        top = self._doc_panel.winfo_toplevel()
        dlg = tk.Toplevel(top)
        dlg.title("Dokumenttyp wählen")
        dlg.resizable(False, False)
        dlg.transient(top)
        dlg.grab_set()

        ttk.Label(dlg, text="In welchen Ordner soll das Dokument abgelegt werden?",
                  font=("Segoe UI", 10)).pack(padx=20, pady=(14, 8))

        var = tk.StringVar(value=current)
        for cat in DOC_CATEGORIES:
            ttk.Radiobutton(dlg, text=cat, variable=var, value=cat).pack(
                anchor=tk.W, padx=28, pady=2)

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=12)

        def ok():
            result[0] = var.get()
            dlg.destroy()

        ttk.Button(btn_frame, text="OK", command=ok, width=10).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Abbrechen", command=dlg.destroy, width=10).pack(side=tk.LEFT, padx=6)

        # Size the dialog after widgets are placed
        dlg.update_idletasks()
        w, h = dlg.winfo_reqwidth() + 20, dlg.winfo_reqheight() + 10
        x = top.winfo_rootx() + (top.winfo_width() - w) // 2
        y = top.winfo_rooty() + (top.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{x}+{y}")

        dlg.wait_window()
        return result[0]

    def _switch_to_category(self, category: str):
        if self._notebook is None:
            return
        for idx in range(self._notebook.index("end")):
            if self._notebook.tab(idx, "text") == category:
                self._notebook.select(idx)
                break

    def _add_document(self):
        if self._selected_supplier is None:
            messagebox.showinfo("Hinweis", "Bitte zuerst einen Lieferanten auswählen.")
            return

        category = self._ask_category()
        if category is None:
            return

        paths = filedialog.askopenfilenames(
            title="Dokument(e) hinzufügen",
            parent=self._doc_panel.winfo_toplevel(),
        )
        if not paths:
            return
        dest_folder = self._category_folder(category)
        try:
            os.makedirs(dest_folder, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Fehler", f"Ordner konnte nicht erstellt werden:\n{exc}")
            return
        errors = []
        for src in paths:
            filename = os.path.basename(src)
            dest = os.path.join(dest_folder, filename)
            try:
                shutil.copy2(src, dest)
            except OSError as exc:
                errors.append(f"{filename}: {exc}")
        if errors:
            messagebox.showwarning("Fehler beim Kopieren",
                                   "Einige Dateien konnten nicht kopiert werden:\n" +
                                   "\n".join(errors))
        # Switch to the target tab so the user immediately sees the added file
        self._switch_to_category(category)
        self._refresh_category(category, self._cat_trees[category])

    def _open_file(self, category: str | None = None):
        if category is None:
            category = self._active_category()
        if category == "Alle Dateien":
            self._open_file_from_all_tab()
            return
        if category is None:
            return
        tree = self._cat_trees.get(category)
        if tree is None:
            return
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Hinweis", "Bitte eine Datei auswählen.")
            return
        full_path = sel[0]  # iid is the full path
        if not os.path.isfile(full_path):
            messagebox.showerror("Fehler", "Datei nicht gefunden.")
            return
        try:
            os.startfile(full_path)
        except OSError as exc:
            messagebox.showerror("Fehler", f"Datei konnte nicht geöffnet werden:\n{exc}")

    def _open_folder(self):
        if self._selected_supplier is None:
            messagebox.showinfo("Hinweis", "Bitte zuerst einen Lieferanten auswählen.")
            return
        folder = self._supplier_folder()
        try:
            os.makedirs(folder, exist_ok=True)
            os.startfile(folder)
        except OSError as exc:
            messagebox.showerror("Fehler", f"Ordner konnte nicht geöffnet werden:\n{exc}")

    def _change_base_folder(self):
        new_path = filedialog.askdirectory(
            title="Dokumenten-Basisordner wählen",
            initialdir=self._get_base_folder(),
            parent=self._doc_panel.winfo_toplevel(),
        )
        if not new_path:
            return
        self._save_base_folder(new_path)
        self._path_var.set(new_path)
        if self._selected_supplier is not None:
            self._refresh_all_categories()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _apply_search(self):
        q = self._search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        for s in self._all_suppliers:
            if q in s.name.lower() or q in s.country.lower() or q in s.contact_person.lower():
                self.tree.insert("", tk.END, iid=s.id,
                                 values=(s.name, s.country, s.contact_person))

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def refresh(self):
        self._all_suppliers = self.app.supplier_service.get_all()
        self._apply_search()
        # Re-select previously selected supplier if still present
        if self._selected_supplier is not None:
            if self.tree.exists(self._selected_supplier.id):
                self.tree.selection_set(self._selected_supplier.id)
                self._refresh_all_categories()
            else:
                self._selected_supplier = None
                self._name_label.config(text="")
                self._set_panel_visible(False)

    def show(self):
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.refresh()

    def hide(self):
        self.frame.pack_forget()


# ---------------------------------------------------------------------------
# Supplier form dialog (unchanged logic, just moved below)
# ---------------------------------------------------------------------------

class SupplierFormDialog:
    def __init__(self, parent, app, supplier=None):
        self.app = app
        self.supplier = supplier
        self.is_edit = supplier is not None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Lieferant bearbeiten" if self.is_edit else "Neuer Lieferant")
        self.dialog.geometry("420x390")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._vars = {}
        self._build()
        if self.is_edit:
            self._populate()

    def _build(self):
        f = ttk.Frame(self.dialog, padding=15)
        f.pack(fill=tk.BOTH, expand=True)

        fields = [
            ("name", "Name:"),
            ("contact_person", "Ansprechpartner:"),
            ("email", "E-Mail:"),
            ("phone", "Telefon:"),
            ("country", "Land:"),
        ]
        for row, (field, label) in enumerate(fields):
            ttk.Label(f, text=label).grid(row=row, column=0, sticky=tk.W, pady=5)
            self._vars[field] = tk.StringVar()
            ttk.Entry(f, textvariable=self._vars[field], width=30).grid(
                row=row, column=1, padx=10, pady=5, sticky=tk.W)

        row = len(fields)
        ttk.Label(f, text="Notizen:").grid(row=row, column=0, sticky=tk.NW, pady=5)
        self.notes_text = tk.Text(f, width=30, height=4)
        self.notes_text.grid(row=row, column=1, padx=10, pady=5, sticky=tk.W)
        row += 1

        btn_frame = ttk.Frame(f)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="Speichern", command=self._save).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Abbrechen", command=self.dialog.destroy).pack(side=tk.LEFT, padx=10)

    def _populate(self):
        s = self.supplier
        self._vars["name"].set(s.name)
        self._vars["contact_person"].set(s.contact_person)
        self._vars["email"].set(s.email)
        self._vars["phone"].set(s.phone)
        self._vars["country"].set(s.country)
        self.notes_text.insert("1.0", s.notes)

    def _save(self):
        name = self._vars["name"].get().strip()
        if not name:
            messagebox.showwarning("Fehler", "Bitte einen Namen angeben.")
            return

        if self.is_edit:
            s = self.supplier
        else:
            s = Supplier(name=name)

        s.name = name
        s.contact_person = self._vars["contact_person"].get()
        s.email = self._vars["email"].get()
        s.phone = self._vars["phone"].get()
        s.country = self._vars["country"].get().strip()
        s.notes = self.notes_text.get("1.0", tk.END).strip()

        if self.is_edit:
            self.app.supplier_service.update(s)
        else:
            self.app.supplier_service.add(s)

        self.dialog.destroy()
        self.app.refresh_current_page()


# ---------------------------------------------------------------------------
# SupplierOverviewPage — used inside WKZ & Bonus (MainWindow)
# Read-only supplier list + entry summary per supplier + date filter
# ---------------------------------------------------------------------------

class SupplierOverviewPage:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.frame = ttk.Frame(parent)
        self._all_suppliers = []
        self._selected_supplier = None
        self._search_var = tk.StringVar()
        self._date_from_var = tk.StringVar()
        self._date_to_var = tk.StringVar()
        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self):
        paned = ttk.PanedWindow(self.frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # ── Left pane ──────────────────────────────────────────────────
        left = ttk.Frame(paned, width=280)
        left.pack_propagate(False)
        paned.add(left, weight=0)

        ttk.Label(left, text="Lieferanten",
                  font=("Segoe UI", 13, "bold")).pack(anchor=tk.W, padx=10, pady=(10, 4))

        # Search bar
        search_frame = ttk.Frame(left)
        search_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        ttk.Label(search_frame, text="Suche:").pack(side=tk.LEFT)
        ttk.Entry(search_frame, textvariable=self._search_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
        self._search_var.trace_add("write", lambda *_: self._apply_search())

        # Supplier treeview
        tree_frame = ttk.Frame(left)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("name", "country", "contact")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                 selectmode="browse")
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        for col, text, width in [("name", "Name", 120), ("country", "Land", 50),
                                  ("contact", "Kontakt", 100)]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, minwidth=40, anchor=tk.W)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self._on_supplier_select)

        # ── Right pane ─────────────────────────────────────────────────
        right = ttk.Frame(paned)
        paned.add(right, weight=1)
        self._build_overview_panel(right)

    def _build_overview_panel(self, parent):
        self._panel = parent

        # Content (visible only when a supplier is selected)
        self._content = ttk.Frame(parent)

        # Supplier name heading
        self._name_label = ttk.Label(self._content, text="",
                                     font=("Segoe UI", 14, "bold"))
        self._name_label.pack(anchor=tk.W, padx=12, pady=(10, 4))

        # Date filter row
        filter_frame = ttk.Frame(self._content)
        filter_frame.pack(fill=tk.X, padx=12, pady=(0, 8))

        ttk.Label(filter_frame, text="Zeitraum:").pack(side=tk.LEFT)
        ttk.Label(filter_frame, text="Von:").pack(side=tk.LEFT, padx=(10, 2))
        ttk.Entry(filter_frame, textvariable=self._date_from_var,
                  width=11).pack(side=tk.LEFT)
        ttk.Label(filter_frame, text="Bis:").pack(side=tk.LEFT, padx=(10, 2))
        ttk.Entry(filter_frame, textvariable=self._date_to_var,
                  width=11).pack(side=tk.LEFT)
        ttk.Button(filter_frame, text="Filtern",
                   command=self._refresh_overview).pack(side=tk.LEFT, padx=(10, 2))
        ttk.Button(filter_frame, text="Zurücksetzen",
                   command=self._reset_filter).pack(side=tk.LEFT, padx=2)

        # Entry treeview
        tree_frame = ttk.Frame(self._content)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 4))

        cols = ("date", "type", "description", "status", "amount")
        self._entry_tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                        selectmode="browse")
        vsb2 = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                              command=self._entry_tree.yview)
        self._entry_tree.configure(yscrollcommand=vsb2.set)

        col_defs = [
            ("date",        "Datum",        90,  tk.W),
            ("type",        "Typ",          90,  tk.W),
            ("description", "Beschreibung", 260, tk.W),
            ("status",      "Status",       95,  tk.W),
            ("amount",      "Betrag",       95,  tk.E),
        ]
        for col, text, width, anchor in col_defs:
            self._entry_tree.heading(col, text=text)
            self._entry_tree.column(col, width=width, minwidth=40, anchor=anchor)

        self._entry_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb2.pack(side=tk.RIGHT, fill=tk.Y)

        # Total row
        total_frame = ttk.Frame(self._content)
        total_frame.pack(fill=tk.X, padx=12, pady=(2, 10))
        ttk.Label(total_frame, text="Gesamt:").pack(side=tk.LEFT)
        self._total_label = ttk.Label(total_frame, text="",
                                      font=("Segoe UI", 10, "bold"))
        self._total_label.pack(side=tk.LEFT, padx=(8, 0))

        # Placeholder shown when no supplier is selected
        self._placeholder = ttk.Label(parent,
                                      text="Bitte einen Lieferanten auswählen.",
                                      font=("Segoe UI", 11), foreground="gray")
        self._set_content_visible(False)

    # ------------------------------------------------------------------
    # Visibility
    # ------------------------------------------------------------------

    def _set_content_visible(self, visible: bool):
        if visible:
            self._placeholder.pack_forget()
            self._content.pack(fill=tk.BOTH, expand=True)
        else:
            self._content.pack_forget()
            self._placeholder.pack(expand=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fmt_eur(self, value: float) -> str:
        return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

    def _parse_date(self, s: str) -> date | None:
        for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
            try:
                return datetime.strptime(s.strip(), fmt).date()
            except ValueError:
                continue
        return None

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_supplier_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            self._selected_supplier = None
            self._set_content_visible(False)
            return
        self._selected_supplier = self.app.supplier_service.get_by_id(sel[0])
        if self._selected_supplier is None:
            self._set_content_visible(False)
            return
        self._name_label.config(text=self._selected_supplier.name)
        self._set_content_visible(True)
        self._refresh_overview()

    def _refresh_overview(self):
        if self._selected_supplier is None:
            return

        date_from = self._parse_date(self._date_from_var.get())
        date_to = self._parse_date(self._date_to_var.get())

        entries = [
            e for e in self.app.entry_service.get_all()
            if e.supplier_name.strip().lower() == self._selected_supplier.name.strip().lower()
        ]

        if date_from:
            entries = [e for e in entries if e.date_start and e.date_start >= date_from]
        if date_to:
            entries = [e for e in entries if e.date_start and e.date_start <= date_to]

        entries.sort(key=lambda e: e.date_start or date.min, reverse=True)

        self._entry_tree.delete(*self._entry_tree.get_children())
        total = 0.0
        for e in entries:
            date_str = e.date_start.strftime("%d.%m.%y") if e.date_start else "–"
            self._entry_tree.insert("", tk.END, iid=e.id, values=(
                date_str,
                e.entry_type.value,
                e.description,
                e.status.value,
                self._fmt_eur(e.amount),
            ))
            total += e.amount

        self._total_label.config(text=self._fmt_eur(total))

    def _reset_filter(self):
        self._date_from_var.set("")
        self._date_to_var.set("")
        self._refresh_overview()

    def _apply_search(self):
        q = self._search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        for s in self._all_suppliers:
            if q in s.name.lower() or q in s.country.lower() or q in s.contact_person.lower():
                self.tree.insert("", tk.END, iid=s.id,
                                 values=(s.name, s.country, s.contact_person))

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def refresh(self):
        self._all_suppliers = self.app.supplier_service.get_all()
        self._apply_search()
        if self._selected_supplier is not None:
            if self.tree.exists(self._selected_supplier.id):
                self.tree.selection_set(self._selected_supplier.id)
                self._refresh_overview()
            else:
                self._selected_supplier = None
                self._set_content_visible(False)

    def show(self):
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.refresh()

    def hide(self):
        self.frame.pack_forget()
