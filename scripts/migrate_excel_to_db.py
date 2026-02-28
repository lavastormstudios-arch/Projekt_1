"""
Einmaliges Migrationsskript: Excel-Daten → PostgreSQL (oder SQLite).

Ausführung vom Projektroot:
    python scripts/migrate_excel_to_db.py

Die Ziel-URL wird aus config.ini gelesen ([Database] url).
"""
import os
import sys
import configparser

# Projektroot zu sys.path hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

cfg = configparser.ConfigParser()
cfg.read(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.ini"))

db_url = cfg.get("Database", "url", fallback=None)
if not db_url:
    print("Fehler: Kein [Database] url in config.ini konfiguriert.")
    sys.exit(1)

from src.data.excel_store import ExcelStore
from src.data.database_store import DatabaseStore

print(f"Verbinde mit: {db_url}")
store_excel = ExcelStore()
store_db = DatabaseStore(db_url)

# Entries
entries = store_excel.load_entries()
print(f"Migriere {len(entries)} Einträge...")
for entry in entries:
    store_db.add_entry(entry)

# Suppliers
suppliers = store_excel.load_suppliers()
print(f"Migriere {len(suppliers)} Lieferanten...")
for supplier in suppliers:
    store_db.add_supplier(supplier)

# FOB-Einträge
fob_entries = store_excel.load_fob_entries()
print(f"Migriere {len(fob_entries)} FOB-Einträge...")
for fob_entry in fob_entries:
    store_db.add_fob_entry(fob_entry)

# Benutzer
users = store_excel.load_users()
print(f"Migriere {len(users)} Benutzer...")
store_db.save_users(users)

# Modulzugriff
module_access = store_excel.load_module_access()
print("Migriere Modulzugriffsrechte...")
store_db.save_module_access(module_access)

# Aktionsrechte
action_rights = store_excel.load_action_rights()
print("Migriere Aktionsrechte...")
store_db.save_action_rights(action_rights)

print("Migration abgeschlossen.")
