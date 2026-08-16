from __future__ import annotations

from datetime import date, datetime, time, timezone


def parse_as_of(value: str) -> date:
    return date.fromisoformat(value)


def author_utc_date(iso_str: str) -> date:
    parsed = datetime.fromisoformat(iso_str)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).date()


def as_of_datetime(as_of: date) -> datetime:
    return datetime.combine(as_of, time.min, tzinfo=timezone.utc)


def days_before(last: date, as_of: date) -> int:
    return (as_of - last).days
