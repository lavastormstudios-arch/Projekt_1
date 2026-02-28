import re
from datetime import date, datetime
from typing import Optional

DATE_FORMAT = "%Y-%m-%d"
DISPLAY_FORMAT = "%d.%m.%y"

# Formats tried when parsing user input or stored strings
_PARSE_FORMATS = ("%Y-%m-%d", "%d.%m.%y", "%d.%m.%Y")


def parse_date(value) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    for fmt in _PARSE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def format_date(d: Optional[date]) -> str:
    """ISO format for internal storage (YYYY-MM-DD)."""
    if d is None:
        return ""
    return d.strftime(DATE_FORMAT)


def display_date(d: Optional[date]) -> str:
    """Human-readable format for UI display (DD.MM.YY)."""
    if d is None:
        return ""
    return d.strftime(DISPLAY_FORMAT)


def auto_format_date(value: str) -> str:
    """Convert user input to DD.MM.YY.

    Accepts: 280226 → 28.02.26
             28022026 → 28.02.26
             28.02.26 or 28.02.2026 → unchanged
    """
    v = value.strip()
    if not v:
        return v
    # Already looks like a date with dots — leave as-is
    if re.match(r'^\d{1,2}\.\d{1,2}\.\d{2,4}$', v):
        return v
    # Pure digits: extract and reformat
    digits = re.sub(r'\D', '', v)
    if len(digits) == 6:   # DDMMYY
        return f"{digits[0:2]}.{digits[2:4]}.{digits[4:6]}"
    if len(digits) == 8:   # DDMMYYYY → DD.MM.YY (last 2 digits of year)
        return f"{digits[0:2]}.{digits[2:4]}.{digits[6:8]}"
    return value


def safe_float(value, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        # Handle German decimal comma (e.g. "954,25" → 954.25)
        try:
            return float(str(value).replace(",", "."))
        except (ValueError, TypeError):
            return default


def safe_int(value, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
