import json
from dataclasses import dataclass, field


@dataclass
class FobEntry:
    id: str
    artnr: str
    bezeichnung: str
    lieferant: str
    warengruppe: str = ""
    cm: str = ""
    aktuelle_ztn: str = ""
    aktueller_ek: float = 0.0
    ek_fob_dollar: float = 0.0
    ek_fob_rmb: float = 0.0
    ek_fob_euro: float = 0.0
    produktionszeit: int = 0
    kubikmeter: float = 0.0
    lcl: bool = False
    container_20: int = 0
    container_40hc: int = 0
    zollsatz: float = 0.0
    sonder_toolingkosten: float = 0.0
    archiv: bool = False
    price_history: str = ""

    def get_price_history(self) -> list:
        return json.loads(self.price_history) if self.price_history else []

    def set_price_history(self, history: list):
        self.price_history = json.dumps(history, ensure_ascii=False)
