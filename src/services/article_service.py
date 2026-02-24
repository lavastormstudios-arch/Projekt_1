import configparser
import csv
import os
from typing import Optional

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config.ini",
)

# CSV-Spaltenname (lowercase) → FobEntry-Feldname
# Wird laufend erweitert wenn vollständige Spaltenliste bekannt ist
_FIELD_MAP = {
    # Artikelnummer
    "artnr":              "artnr",
    "art.-nr":            "artnr",
    "art.nr":             "artnr",
    "artikelnr":          "artnr",
    "artikelnummer":      "artnr",
    "artikel-nr":         "artnr",
    # Bezeichnung
    "bez":                "bezeichnung",
    "bezeichnung":        "bezeichnung",
    "bezeichng":          "bezeichnung",
    "artbezeichnung":     "bezeichnung",
    "beschreibung":       "bezeichnung",
    # EK
    "ek":                 "aktueller_ek",
    "ek std":             "aktueller_ek",
    "ek-std":             "aktueller_ek",
    "ek_std":             "aktueller_ek",
    "einkaufspreis":      "aktueller_ek",
    "std":                "aktueller_ek",
    "standardpreis":      "aktueller_ek",
    # Lieferant
    "lieferant":          "lieferant",
    "lief.":              "lieferant",
    "lief":               "lieferant",
    # Warengruppe
    "warengruppe":        "warengruppe",
    "wgr":                "warengruppe",
    "wg":                 "warengruppe",
    # UVP / VK
    "uvp":                "geplanter_uvp",
    "vk":                 "geplanter_uvp",
    "verkaufspreis":      "geplanter_uvp",
    # ZTN
    "ztn":                "aktuelle_ztn",
    "aktuelle ztn":       "aktuelle_ztn",
    # CM
    "cm":                 "cm",
}


class ArticleService:
    """
    Lädt eine CSV-Artikelliste und stellt einen schnellen Lookup per Artnr bereit.
    Nutzt einen Klassen-Level-Cache, sodass die Daten programmweit verfügbar sind.
    """

    _cache: dict[str, dict] = {}
    _loaded_count: int = 0
    _loaded_path: str = ""

    # ------------------------------------------------------------------
    # Laden
    # ------------------------------------------------------------------

    @classmethod
    def load_from_config(cls) -> int:
        """Liest den Pfad aus config.ini und lädt die CSV. Gibt Anzahl geladener Artikel zurück."""
        cfg = configparser.ConfigParser()
        cfg.read(_CONFIG_PATH, encoding="utf-8")
        path = cfg.get("Import", "articles_csv_path", fallback="").strip()
        if not path or not os.path.exists(path):
            return 0
        return cls.load_from_csv(path)

    @classmethod
    def load_from_csv(cls, path: str) -> int:
        """
        Liest eine CSV-Datei mit flexiblem Delimiter und Encoding.
        Gibt die Anzahl erfolgreich geladener Artikel zurück.
        Wirft ValueError wenn die Datei kein gültiges Format hat.
        """
        last_error = None

        for encoding in ("utf-8-sig", "cp1252", "utf-8"):
            for delimiter in (";", ",", "\t"):
                try:
                    with open(path, encoding=encoding, newline="") as fh:
                        reader = csv.DictReader(fh, delimiter=delimiter)
                        rows = list(reader)

                    if not rows:
                        continue

                    # Prüfen ob Artnr-Spalte vorhanden
                    raw_keys = [str(k).strip().lower() for k in rows[0].keys() if k is not None]
                    has_artnr = any(k in _FIELD_MAP and _FIELD_MAP[k] == "artnr" for k in raw_keys)
                    if not has_artnr:
                        continue

                    new_cache: dict[str, dict] = {}
                    for row in rows:
                        mapped: dict[str, str] = {}
                        for raw_key, val in row.items():
                            if raw_key is None:
                                continue
                            hl = str(raw_key).strip().lower()
                            field = _FIELD_MAP.get(hl)
                            v = str(val).strip() if val is not None else ""
                            if field:
                                if field not in mapped:  # first match wins
                                    mapped[field] = v
                            else:
                                mapped[f"_raw_{raw_key.strip()}"] = v

                        artnr = mapped.get("artnr", "").strip().upper()
                        if artnr:
                            new_cache[artnr] = mapped

                    cls._cache = new_cache
                    cls._loaded_count = len(new_cache)
                    cls._loaded_path = path
                    return cls._loaded_count

                except Exception as exc:
                    last_error = exc
                    continue

        raise ValueError(
            f"Artikelliste konnte nicht geladen werden: {last_error or 'Unbekanntes Format'}"
        )

    # ------------------------------------------------------------------
    # Abfrage
    # ------------------------------------------------------------------

    @classmethod
    def lookup(cls, artnr: str) -> Optional[dict]:
        """Gibt das gemappte Daten-Dict zurück, oder None wenn nicht gefunden."""
        return cls._cache.get(artnr.strip().upper())

    @classmethod
    def get_count(cls) -> int:
        return cls._loaded_count

    @classmethod
    def get_loaded_path(cls) -> str:
        return cls._loaded_path

    @classmethod
    def is_loaded(cls) -> bool:
        return cls._loaded_count > 0
