# Release-Anleitung

## 1. PostgreSQL auf dem Windows Server einrichten

### PostgreSQL installieren
1. Installer herunterladen: https://www.postgresql.org/download/windows/
2. Installation durchführen (Standard-Port **5432** beibehalten)
3. Während der Installation ein Passwort für den `postgres`-Superuser vergeben und merken

### Datenbank und Benutzer anlegen
Nach der Installation **pgAdmin** öffnen oder die **SQL Shell (psql)** verwenden:

```sql
-- Neuen Benutzer anlegen
CREATE USER wkz_user WITH PASSWORD 'sicheres_passwort';

-- Datenbank anlegen
CREATE DATABASE wkz_bonus OWNER wkz_user;

-- Rechte vergeben
GRANT ALL PRIVILEGES ON DATABASE wkz_bonus TO wkz_user;
```

### Firewall-Regel einrichten (Windows Server)
Port **5432** für eingehende TCP-Verbindungen freigeben:
- Windows Defender Firewall → Eingehende Regel → Neu
- Typ: Port → TCP → 5432
- Aktion: Verbindung zulassen
- Profil: Domäne + Privat (nicht Öffentlich)

### PostgreSQL für Netzwerkzugriff konfigurieren
In der PostgreSQL-Konfigurationsdatei `pg_hba.conf` (liegt in `C:\Program Files\PostgreSQL\17\data\`):

```
# Zugriff aus dem LAN erlauben (Beispiel: Subnetz 192.168.1.0/24)
host    wkz_bonus    wkz_user    192.168.1.0/24    scrypt
```

Danach PostgreSQL-Dienst neu starten (Dienste → postgresql-x64-17 → Neu starten).

---

## 2. App auf PostgreSQL umstellen

### config.ini anpassen
Auf **jedem Client-PC** (und dem Server selbst) die `config.ini` im Programmordner öffnen und den `[Database]`-Abschnitt anpassen:

```ini
[Database]
url = postgresql://wkz_user:sicheres_passwort@192.168.1.10:5432/wkz_bonus
```

`192.168.1.10` durch die tatsächliche IP-Adresse des Windows Servers ersetzen.

Die SQLite-Zeile wird dadurch automatisch ignoriert — es gibt nur einen aktiven `url`-Eintrag.

### Einmalige Datenmigration ausführen
Auf **einem** PC (mit den aktuellen Excel-Daten und der neuen config.ini):

```
python scripts/migrate_excel_to_db.py
```

Dieser Schritt kopiert alle bestehenden Daten aus den Excel-Dateien in die PostgreSQL-Datenbank.
**Nur einmal ausführen** — danach ist die Migration abgeschlossen.

### Verbindung testen
App starten → wenn der Launcher erscheint und alle Daten sichtbar sind, ist die Verbindung erfolgreich.

---

## 3. VPN-Zugriff (Homeoffice)

Solange der VPN-Tunnel aktiv ist und der Server unter seiner LAN-IP erreichbar ist, funktioniert die App identisch wie im Büro. Keine zusätzliche Konfiguration nötig.

---

## 4. Auto-Update-Mechanismus

### Wie es funktioniert
```
Entwickler:  git tag v1.2.0 → git push origin v1.2.0
                ↓
GitHub Actions baut automatisch WKZ_Bonus.exe (via PyInstaller)
                ↓
.exe wird als Release-Asset auf GitHub hochgeladen
                ↓
Beim nächsten App-Start (max. 1× täglich):
  App fragt GitHub API: "Gibt es eine neuere Version?"
  Neue Version gefunden → Dialog "Update verfügbar"
  Benutzer klickt "Ja" → .exe wird heruntergeladen
  App schließt sich → neue .exe ersetzt alte → App startet neu
```

### GitHub PAT einrichten (einmalig)
Damit die App die GitHub API abfragen darf, wird ein Token benötigt:

1. GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens**
2. Token erstellen:
   - Repository: nur dieses Repo auswählen
   - Berechtigungen: **Contents: Read-only**
3. Token kopieren (wird nur einmal angezeigt)
4. In `config.ini` eintragen:

```ini
[Update]
github_token = github_pat_xxxxxxxxxxxxxxxxxxxx
```

> **Sicherheitshinweis:** Dieser Token kann ausschließlich den Source-Code lesen — der ohnehin auf GitHub liegt. Schreibzugriff ist nicht möglich. `config.ini` ist in `.gitignore` eingetragen und wird nie ins Repository committet.

### Ersten Release erstellen
```bash
# VERSION-Datei auf gewünschte Version setzen
echo 1.0.0 > VERSION
git add VERSION
git commit -m "release: v1.0.0"

# Tag pushen → löst GitHub Actions Build aus
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions baut daraufhin automatisch die `WKZ_Bonus.exe` und lädt sie als Release hoch (~3-5 Minuten).

### Nächstes Update veröffentlichen
```bash
echo 1.1.0 > VERSION
git add VERSION
git commit -m "release: v1.1.0"
git tag v1.1.0
git push origin v1.1.0
```

Alle Clients erhalten beim nächsten App-Start automatisch den Update-Hinweis.

### Update-Verhalten
- Prüfung findet **höchstens einmal täglich** statt (verhindert API-Rate-Limits)
- Bei fehlendem Internet wird die Prüfung **still übersprungen** — die App startet normal
- Das automatische Update funktioniert nur für die **gepackte .exe** — beim Entwickeln aus dem Source-Code erscheint ein Hinweis statt des Updates
- Das letzte Prüfdatum wird in `config.ini → [Update] last_check` gespeichert

---

## Aktivierungs-Checkliste

- [ ] PostgreSQL auf Windows Server installiert
- [ ] Datenbank `wkz_bonus` + Benutzer `wkz_user` angelegt
- [ ] Firewall-Regel für Port 5432 gesetzt
- [ ] `pg_hba.conf` für LAN-Zugriff konfiguriert
- [ ] `config.ini` auf allen Clients mit PostgreSQL-URL befüllt
- [ ] Migrations-Skript einmalig ausgeführt
- [ ] GitHub PAT erstellt und in `config.ini` eingetragen
- [ ] Ersten Release-Tag gepusht (`v1.0.0`)
- [ ] Update-Test: ältere Version starten → Update-Dialog erscheint
