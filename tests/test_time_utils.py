"""Tests for UTC timestamp handling and time utilities."""
import pytest
from datetime import datetime, timezone, timedelta
from src.common.time_utils import (
    ensure_utc,
    parse_utc_timestamp,
    format_utc_timestamp,
    time_ranges_overlap,
    is_timestamp_within_range
)


def test_parse_utc_timestamp_z_suffix():
    ts_str = "2021-10-02T01:58:36Z"
    dt = parse_utc_timestamp(ts_str)
    assert dt.tzinfo == timezone.utc
    assert dt.year == 2021 and dt.month == 10 and dt.day == 2
    assert dt.hour == 1 and dt.minute == 58 and dt.second == 36


def test_parse_utc_timestamp_offset():
    ts_str = "2021-10-02T01:58:36+00:00"
    dt = parse_utc_timestamp(ts_str)
    assert dt.tzinfo == timezone.utc


def test_naive_datetime_rejected():
    naive = datetime(2021, 10, 2, 1, 58, 36)
    with pytest.raises(ValueError, match="Naive datetime"):
        ensure_utc(naive)

    with pytest.raises(ValueError, match="lacks an explicit timezone"):
        parse_utc_timestamp("2021-10-02T01:58:36")


def test_format_utc_timestamp():
    dt = datetime(2021, 10, 2, 1, 58, 36, tzinfo=timezone.utc)
    formatted = format_utc_timestamp(dt)
    assert formatted == "2021-10-02T01:58:36Z"


def test_time_ranges_overlap():
    t0 = datetime(2021, 10, 1, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2021, 10, 1, 12, 0, tzinfo=timezone.utc)
    t2 = datetime(2021, 10, 1, 6, 0, tzinfo=timezone.utc)
    t3 = datetime(2021, 10, 1, 18, 0, tzinfo=timezone.utc)
    t4 = datetime(2021, 10, 2, 0, 0, tzinfo=timezone.utc)

    assert time_ranges_overlap((t0, t1), (t2, t3)) is True
    assert time_ranges_overlap((t0, t1), (t3, t4)) is False
