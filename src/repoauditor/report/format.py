"""Display helpers for the HTML report."""

from __future__ import annotations


def compact_number(value: object) -> str:
    """962 stays 962. 6266493 becomes 6.27M. Three significant digits past 1000."""
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return str(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number != number:  # NaN
        return "—"
    sign = "-" if number < 0 else ""
    number = abs(number)
    if number < 1000:
        if number == int(number):
            return f"{sign}{int(number)}"
        return f"{sign}{number:g}"
    for suffix, magnitude in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if number >= magnitude:
            scaled = number / magnitude
            text = f"{scaled:.3g}"
            if text.endswith(".0"):
                text = text[:-2]
            return f"{sign}{text}{suffix}"
    return f"{sign}{number:.3g}"


def display_date(value: object) -> str:
    if value is None or value == "":
        return "—"
    text = str(value)
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return text


def name_from_key(key: object) -> str:
    text = str(key or "")
    return text.split("\t", 1)[0] if text else "unknown"