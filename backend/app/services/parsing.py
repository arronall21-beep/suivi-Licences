"""Normalisation des valeurs de cellules Excel (dates, nombres, textes)."""

import re
from datetime import date, datetime, timedelta

import pandas as pd

NULL_TOKENS = {
    "",
    "-",
    "--",
    "/",
    "?",
    "n/a",
    "na",
    "nd",
    "n.d",
    "n.d.",
    "neant",
    "néant",
    "aucun",
    "aucune",
    "none",
    "null",
    "nan",
    "nat",
    "x",
}

DATE_FORMATS = ["%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"]

CRITICALITY_MAP = {
    "critique": "Critique",
    "tres haute": "Critique",
    "très haute": "Critique",
    "p1": "Critique",
    "4": "Critique",
    "haute": "Haute",
    "elevee": "Haute",
    "élevée": "Haute",
    "eleve": "Haute",
    "élevé": "Haute",
    "high": "Haute",
    "forte": "Haute",
    "p2": "Haute",
    "3": "Haute",
    "moyenne": "Moyenne",
    "moyen": "Moyenne",
    "medium": "Moyenne",
    "normale": "Moyenne",
    "p3": "Moyenne",
    "2": "Moyenne",
    "basse": "Basse",
    "faible": "Basse",
    "low": "Basse",
    "bas": "Basse",
    "p4": "Basse",
    "1": "Basse",
}


class ParseError(ValueError):
    pass


def is_null(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    if isinstance(value, str) and value.strip().lower() in NULL_TOKENS:
        return True
    return False


def parse_str(value) -> str | None:
    if is_null(value):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return re.sub(r"\s+", " ", str(value)).strip() or None


def parse_date(value) -> date | None:
    if is_null(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        if 1000 < value < 100000:  # numéro de série Excel
            return date(1899, 12, 30) + timedelta(days=int(value))
        raise ParseError(f"date invalide « {value} »")
    text = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        ts = pd.to_datetime(text, dayfirst=True, errors="raise")
        if pd.isna(ts):
            return None
        return ts.date()
    except (ValueError, TypeError, OverflowError):
        raise ParseError(f"date invalide « {text} »") from None


def parse_number(value) -> float | None:
    if is_null(value):
        return None
    if isinstance(value, bool):
        raise ParseError(f"nombre invalide « {value} »")
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(" ", "").replace(" ", "").replace(" ", "")
    text = re.sub(r"(€|eur|euros?|ht|ttc|\$|%)", "", text, flags=re.I)
    if text.count(",") == 1 and text.count(".") == 0:
        text = text.replace(",", ".")
    elif text.count(",") >= 1 and text.count(".") == 1 and text.rfind(".") > text.rfind(","):
        text = text.replace(",", "")
    elif text.count(".") >= 1 and text.count(",") == 1:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        raise ParseError(f"nombre invalide « {value} »") from None


def parse_int(value) -> int | None:
    n = parse_number(value)
    if n is None:
        return None
    if n < 0:
        raise ParseError(f"valeur négative « {value} »")
    return int(round(n))


def parse_money(value) -> float | None:
    n = parse_number(value)
    if n is None:
        return None
    if n < 0:
        raise ParseError(f"montant négatif « {value} »")
    return round(n, 2)


def parse_criticality(value) -> str | None:
    s = parse_str(value)
    if s is None:
        return None
    return CRITICALITY_MAP.get(s.lower(), s.capitalize())


PARSERS = {
    "str": parse_str,
    "vendor": parse_str,
    "contract": parse_str,
    "date": parse_date,
    "int": parse_int,
    "money": parse_money,
    "criticality": parse_criticality,
}
