from datetime import date, datetime
from typing import Optional

DATE_FORMAT = "%Y-%m-%d"


def parse_date(value) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), DATE_FORMAT).date()
    except (ValueError, TypeError):
        return None


def format_date(d: Optional[date]) -> str:
    if d is None:
        return ""
    return d.strftime(DATE_FORMAT)


def safe_float(value, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
