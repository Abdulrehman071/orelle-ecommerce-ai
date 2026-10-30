"""Dates. Django stores timestamps as naive UTC; the business thinks in local time (Asia/Karachi).
A 'day' of sales therefore runs local midnight -> local midnight, converted to UTC for the query."""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo


def business_tz(settings) -> ZoneInfo:
    return ZoneInfo(settings.business_timezone)


def local_bounds_to_utc(start: dt.date, end_inclusive: dt.date, tz: ZoneInfo) -> tuple[dt.datetime, dt.datetime]:
    """[start 00:00 local, end+1day 00:00 local) as naive-UTC datetimes."""
    a = dt.datetime.combine(start, dt.time.min, tzinfo=tz).astimezone(dt.timezone.utc).replace(tzinfo=None)
    b = dt.datetime.combine(end_inclusive + dt.timedelta(days=1), dt.time.min, tzinfo=tz) \
        .astimezone(dt.timezone.utc).replace(tzinfo=None)
    return a, b


def to_local_date(naive_utc: dt.datetime, tz: ZoneInfo) -> dt.date:
    return naive_utc.replace(tzinfo=dt.timezone.utc).astimezone(tz).date()


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)
