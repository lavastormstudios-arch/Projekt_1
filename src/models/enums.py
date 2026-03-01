from enum import Enum


class EntryType(str, Enum):
    WKZ = "WKZ"
    KICKBACK = "Kickback"
    UMSATZBONUS = "Umsatzbonus"
    LAGERWERTAUSGLEICH = "Lagerwertausgleich"


class EntryStatus(str, Enum):
    OFFEN = "Offen"
    ABGERECHNET = "Abgerechnet"
    UEBERFAELLIG = "Überfällig"
    STORNIERT = "Storniert"
