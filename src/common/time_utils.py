"""
Standardized UTC datetime utilities for the SIH26143 pipeline.

Ensures:
1. Strict timezone awareness (all internal timestamps must be UTC).
2. Naive datetimes are explicitly rejected or converted under documented policies.
3. ISO 8601 parsing and serialization standards.
4. Spatio-temporal window validation and overlap testing.
"""

from datetime import datetime, timezone, timedelta
from typing import Union, Tuple


def ensure_utc(dt: datetime) -> datetime:
    """
    Ensure a datetime is timezone-aware and converted to UTC.
    Raises ValueError if datetime is naive.
    """
    if not isinstance(dt, datetime):
        raise TypeError(f"Expected datetime instance, got {type(dt)}")
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"Naive datetime encountered ({dt}). All timestamps must be explicitly UTC-aware.")
    return dt.astimezone(timezone.utc)


def parse_utc_timestamp(ts_input: Union[str, datetime]) -> datetime:
    """
    Parse an ISO 8601 string or datetime into a strict UTC timezone-aware datetime.
    Supports strings ending with 'Z' or standard UTC offsets (+00:00).
    """
    if isinstance(ts_input, datetime):
        return ensure_utc(ts_input)

    if not isinstance(ts_input, str):
        raise TypeError(f"Expected ISO 8601 string or datetime, got {type(ts_input)}")

    clean_str = ts_input.strip()
    if clean_str.endswith("Z"):
        clean_str = clean_str[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(clean_str)
    except Exception as exc:
        raise ValueError(f"Invalid ISO 8601 timestamp string: '{ts_input}'") from exc

    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"Timestamp string '{ts_input}' lacks an explicit timezone offset. Must be UTC.")

    return dt.astimezone(timezone.utc)


def format_utc_timestamp(dt: datetime) -> str:
    """Format a timezone-aware datetime into standard ISO 8601 UTC string ending in 'Z'."""
    utc_dt = ensure_utc(dt)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def time_ranges_overlap(
    range1: Tuple[datetime, datetime],
    range2: Tuple[datetime, datetime]
) -> bool:
    """
    Check if two closed time intervals [start1, end1] and [start2, end2] overlap.
    """
    s1, e1 = ensure_utc(range1[0]), ensure_utc(range1[1])
    s2, e2 = ensure_utc(range2[0]), ensure_utc(range2[1])

    if s1 > e1 or s2 > e2:
        raise ValueError("Range start must not be greater than range end.")

    return not (e1 < s2 or s1 > e2)


def is_timestamp_within_range(
    ts: datetime,
    start: datetime,
    end: datetime
) -> bool:
    """Check if a timestamp ts falls within [start, end]."""
    utc_ts = ensure_utc(ts)
    utc_start = ensure_utc(start)
    utc_end = ensure_utc(end)
    return utc_start <= utc_ts <= utc_end
