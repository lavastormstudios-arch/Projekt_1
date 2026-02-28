"""
Auto-Update-System: prüft einmal täglich auf neue GitHub Releases
und bietet dem Benutzer an, das Update herunterzuladen und zu installieren.

Wird beim Start der App via:
    root.after(500, lambda: check_for_update(root))
aufgerufen.
"""
import configparser
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from datetime import date

GITHUB_REPO = "lavastormstudios-arch/Projekt_1"


def _get_config_path() -> str:
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "config.ini")
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "config.ini",
    )


def get_current_version() -> str:
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
    version_file = os.path.join(base, "VERSION")
    try:
        return open(version_file).read().strip()
    except FileNotFoundError:
        return "0.0.0"


def _version_tuple(v: str):
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0, 0, 0)


def check_for_update(parent_window=None) -> None:
    """Prüft einmal täglich auf Updates und zeigt einen Dialog wenn verfügbar."""
    config_path = _get_config_path()
    cfg = configparser.ConfigParser()
    cfg.read(config_path)

    # Höchstens einmal täglich prüfen
    last_check = cfg.get("Update", "last_check", fallback="")
    if last_check == str(date.today()):
        return

    token = cfg.get("Update", "github_token", fallback="")
    try:
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
    except Exception:
        return  # Kein Internet oder Server nicht erreichbar → still ignorieren

    # Letztes Prüfdatum speichern
    if not cfg.has_section("Update"):
        cfg.add_section("Update")
    cfg.set("Update", "last_check", str(date.today()))
    try:
        with open(config_path, "w") as f:
            cfg.write(f)
    except OSError:
        pass

    latest_tag = data.get("tag_name", "").lstrip("v")
    current = get_current_version()
    if _version_tuple(latest_tag) <= _version_tuple(current):
        return  # Kein Update nötig

    # .exe-Asset suchen
    assets = data.get("assets", [])
    exe_asset = next((a for a in assets if a["name"].endswith(".exe")), None)
    if not exe_asset:
        return

    from tkinter import messagebox

    answer = messagebox.askyesno(
        "Update verfügbar",
        f"Eine neue Version ist verfügbar: v{latest_tag}\n"
        f"Aktuell installiert: v{current}\n\n"
        "Jetzt herunterladen und installieren?",
        parent=parent_window,
    )
    if answer:
        _download_and_apply(exe_asset["browser_download_url"], token, parent_window)


def _download_and_apply(url: str, token: str, parent_window=None):
    from tkinter import messagebox

    exe_path = sys.executable if getattr(sys, "frozen", False) else None
    if not exe_path:
        messagebox.showinfo(
            "Update",
            "Automatisches Update ist nur für die gepackte .exe verfügbar.",
            parent=parent_window,
        )
        return

    try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, headers=headers)
        tmp = tempfile.mktemp(suffix=".exe")
        with urllib.request.urlopen(req) as r, open(tmp, "wb") as f:
            f.write(r.read())
    except Exception as e:
        messagebox.showerror(
            "Update fehlgeschlagen",
            f"Download konnte nicht abgeschlossen werden:\n{e}",
            parent=parent_window,
        )
        return

    # Bat-Skript: kurz warten, alte .exe ersetzen, neu starten
    bat = tempfile.mktemp(suffix=".bat")
    with open(bat, "w") as f:
        f.write(
            f"@echo off\n"
            f"timeout /t 2 /nobreak >nul\n"
            f'move /Y "{tmp}" "{exe_path}"\n'
            f'start "" "{exe_path}"\n'
            f'del "%~f0"\n'
        )
    subprocess.Popen(bat, shell=True)
    sys.exit(0)
