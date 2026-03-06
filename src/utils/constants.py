import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.xlsx")

DEPARTMENTS = ["CM", "Marketing", "Vertrieb", "SCM"]
ROLES = ["Admin", "Abteilungsleiter", "Teamleiter", "Mitarbeiter"]
MODULES = ["WKZ & Bonus", "Lieferantenmanagement", "FOB-Kalkulation"]
FOB_KALKULATION_FILE = os.path.join(DATA_DIR, "fob_kalkulation.xlsx")
FOB_COLUMNS = [
    "id", "artnr", "bezeichnung", "lieferant", "warengruppe", "cm",
    "aktuelle_ztn", "aktueller_ek",
    "ek_fob_dollar", "ek_fob_rmb", "ek_fob_euro", "produktionszeit", "kubikmeter",
    "lcl", "container_20", "container_40hc", "zollsatz",
    "sonder_toolingkosten", "archiv", "price_history",
]
ACTION_PERMISSIONS = ["can_edit", "can_delete", "can_invoice", "can_export", "can_import", "is_admin"]
DUMMY_ARTNR = "MUSTER"
ENTRIES_FILE = os.path.join(DATA_DIR, "entries.xlsx")
SUPPLIERS_FILE = os.path.join(DATA_DIR, "suppliers.xlsx")

ENTRY_COLUMNS = [
    "id", "entry_type", "supplier_id", "supplier_name", "description",
    "status", "amount", "amount_billed", "date_start", "date_end",
    "billing_deadline", "date_billed", "kickback_articles",
    "umsatzbonus_staffeln", "jaehrlich_wiederholen", "wkz_is_percentage", "wkz_percentage",
    "wkz_category", "notes", "created_at", "invoice_number"
]

SUPPLIER_COLUMNS = ["id", "name", "contact_person", "email", "phone", "notes", "purchase_volume", "country"]

ENTRY_COLUMN_LABELS = {
    "id": "ID",
    "entry_type": "Typ",
    "supplier_id": "Lief.-ID",
    "supplier_name": "Lieferant",
    "description": "Beschreibung",
    "status": "Status",
    "amount": "Betrag (erw.)",
    "amount_billed": "Betrag (abger.)",
    "date_start": "Beginn",
    "date_end": "Ende",
    "billing_deadline": "Abrechnungsfrist",
    "date_billed": "Abgerechnet am",
    "kickback_articles": "Kickback-Artikel",
    "umsatzbonus_staffeln": "Umsatzbonus-Staffeln",
    "jaehrlich_wiederholen": "Jährlich wiederholen",
    "wkz_is_percentage": "WKZ Prozentual",
    "wkz_percentage": "WKZ Prozent",
    "wkz_category": "WKZ Kategorie",
    "notes": "Notizen",
    "created_at": "Erstellt",
}

TABLE_COLUMNS = [
    "id", "entry_type", "supplier_name", "description", "status",
    "amount", "billing_deadline", "date_billed"
]

DATE_FORMAT = "%Y-%m-%d"
