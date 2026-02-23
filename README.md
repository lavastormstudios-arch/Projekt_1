# Werkzeuge Suite

Interne Desktop-Applikation zur Verwaltung von Werbekostenzuschüssen (WKZ), Kickbacks, Umsatzboni und Lieferantendokumenten.

---

## Module

### WKZ & Bonus
- Erfassung und Verwaltung von WKZ-, Kickback- und Umsatzbonus-Einträgen
- Dashboard mit Übersicht und Fristenwarnung
- Kalenderansicht nach Fälligkeiten
- Gefilterte Tabellenansichten (alle Einträge, WKZ, Kickback, Umsatzbonus)
- Einzel- und Sammelrechnungserstellung als PDF (Word-Vorlage via `docxtpl`)
- Export nach Excel

### Lieferantenmanagement
- Lieferantenliste mit Suchfunktion
- Dokumentenablage pro Lieferant, kategorisiert in:
  - Lieferantengespräche
  - Lieferantenvertrag
  - Konditionen
  - Informationen
  - WKZ & Bonusrechnungen
- Dateien öffnen & Ordner direkt in Windows Explorer aufrufen

### Admin-Bereich (PIN-geschützt)
- CSV-Importpfad (SAP-Export)
- SMTP-Konfiguration für E-Mail-Erinnerungen
- Dokumenten-Basisordner
- Frühwarnzeit für Fristenwarnung
- Admin-PIN ändern

---

## Voraussetzungen

- **Python** 3.11 oder neuer
- **Microsoft Word** (für PDF-Generierung via `docx2pdf`)
- Windows 10 / 11

---

## Installation

```bash
# 1. Repository klonen
git clone https://github.com/lavastormstudios-arch/Projekt_1.git
cd Projekt_1

# 2. Abhängigkeiten installieren
pip install -r requirements.txt

# 3. Konfigurationsdatei anlegen
copy config.ini.example config.ini
```

Anschließend `config.ini` mit den gewünschten Einstellungen befüllen (SMTP, Importpfad usw.).
Der Standard-Admin-PIN ist **1234** — bitte nach dem ersten Start ändern.

---

## Starten

```bash
python main.py
```

---

## Projektstruktur

```
Projekt_1/
├── main.py                      # Einstiegspunkt
├── requirements.txt
├── config.ini.example           # Konfigurationsvorlage
│
├── assets/
│   ├── 201_Berger_Logo_blau.png # Logo für Hauptmenü
│   └── Vorlage Bonus.docx       # Original-Rechnungsvorlage
│
├── data/
│   └── templates/               # Verarbeitete Word-Vorlagen (docxtpl)
│       └── invoice_bonus.docx
│
└── src/
    ├── data/
    │   ├── excel_store.py       # Excel-Datenzugriff (openpyxl)
    │   └── export.py            # Excel-Export
    ├── models/
    │   ├── base_entry.py        # Datenmodell: Einträge
    │   ├── supplier.py          # Datenmodell: Lieferant
    │   └── enums.py             # EntryType, EntryStatus
    ├── services/
    │   ├── entry_service.py     # CRUD für Einträge
    │   ├── supplier_service.py  # CRUD + CSV-Import
    │   ├── invoice_service.py   # Rechnungserstellung (PDF)
    │   ├── reminder_service.py  # Fristenprüfung
    │   └── email_service.py     # SMTP-Versand
    └── ui/
        ├── launcher.py          # Hauptmenü
        ├── main_window.py       # WKZ & Bonus Fenster
        ├── supplier_window.py   # Lieferantenmanagement Fenster
        ├── admin_dialog.py      # Admin-PIN & Einstellungen
        ├── dashboard.py
        ├── entry_table_view.py
        ├── entry_form.py
        ├── invoice_dialog.py    # Einzel- & Sammelrechnung
        ├── supplier_view.py
        ├── calendar_view.py
        └── export_dialog.py
```

---

## CSV-Import (SAP-Format)

Der Import erkennt automatisch Encoding (UTF-8, CP1252) und Trennzeichen (`;`, Tab, `,`).
Erwartete Spalten:

| SAP-Spalte | Bedeutung |
|---|---|
| `NAME1` | Lieferantenname (Pflichtfeld) |
| `NAME2` / `NAME3` | Namenszusätze |
| `DLIFNR` | Lieferantennummer |
| `STRAS` | Straße |
| `PLOR` | PLZ |
| `ORTNA` | Ort |
| `LANDKZ` | Länderkennzeichen (z. B. `DE`) |

Re-Import ist idempotent — bestehende Lieferanten werden aktualisiert, keine Duplikate.

---

## Rechnungserstellung

Vorlage: `data/templates/invoice_bonus.docx` (docxtpl / Jinja2-Syntax)

Verfügbare Platzhalter:

| Platzhalter | Quelle |
|---|---|
| `{{NAME1}}` … `{{ORTNA}}` | Lieferantenstammdaten |
| `{{LANDKZ}}` | Länderkennzeichen |
| `{{DLIFNR}}` | Lieferantennummer |
| `{{RENR}}` | Rechnungsnummer (auto) |
| `{{AKTDAT}}` | Rechnungsdatum |
| `{{ARTBON}}` | Bonusart (WKZ / Kickback / Umsatzbonus) |
| `{{JAHR}}` | Geschäftsjahr |
| `{{NETSUM}}` / `{{MWST}}` / `{{GESBET}}` | Beträge |

MwSt. wird automatisch auf **19 %** gesetzt wenn `LANDKZ` = `DE` (oder `D`), sonst **0 %**.

---

## Abhängigkeiten

| Paket | Zweck |
|---|---|
| `openpyxl` | Excel-Datenspeicherung |
| `tkcalendar` | Datumsauswahl in der GUI |
| `docxtpl` | Word-Vorlagen befüllen |
| `docx2pdf` | Word → PDF Konvertierung |
| `Pillow` | Logo-Anzeige im Hauptmenü |

> `Pillow` wird nicht in `requirements.txt` geführt, da es optional ist — ohne Pillow wird statt des Logos ein Textfallback angezeigt.
