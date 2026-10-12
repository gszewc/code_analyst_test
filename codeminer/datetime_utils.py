"""Utilities for UTC-aware datetime handling."""

from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def ensure_utc_datetime(value: Optional[datetime | str]) -> Optional[datetime]:
    """Normalize datetime or ISO datetime strings to UTC-aware datetimes."""
    if value is None:
        return None

    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        value = datetime.fromisoformat(normalized)

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)
