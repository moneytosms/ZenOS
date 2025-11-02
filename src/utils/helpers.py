"""Utility helper functions"""

from datetime import datetime, date, timedelta
from typing import Optional
from zoneinfo import ZoneInfo
import os


def format_duration(minutes: int) -> str:
    """Format duration in minutes to human-readable string"""
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    mins = minutes % 60
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h {mins}m"


def get_week_range(target_date: Optional[date] = None) -> tuple[date, date]:
    """Get start (Monday) and end (Sunday) of week for given date"""
    if target_date is None:
        target_date = date.today()
    
    # Monday is 0, Sunday is 6
    days_since_monday = target_date.weekday()
    start_of_week = target_date - timedelta(days=days_since_monday)
    end_of_week = start_of_week + timedelta(days=6)
    
    return start_of_week, end_of_week


def calculate_percentage(part: float, total: float) -> float:
    """Calculate percentage, handling zero division"""
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def parse_date_string(date_str: str) -> Optional[date]:
    """Parse date string in various formats"""
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.date() if isinstance(dt, datetime) else dt
        except ValueError:
            continue
    return None


# Timezone helpers
DEFAULT_TZ = os.getenv("ZENOS_TIMEZONE", "Asia/Kolkata")


def get_zoneinfo(tz_name: Optional[str] = None) -> ZoneInfo:
    """Return a ZoneInfo for the given tz_name or default."""
    if tz_name is None:
        tz_name = DEFAULT_TZ
    try:
        return ZoneInfo(tz_name)
    except Exception:
        # Fallback to UTC
        return ZoneInfo("UTC")


def to_local(dt: datetime, tz_name: Optional[str] = None) -> datetime:
    """Convert an aware or naive datetime to the local timezone.

    If dt is naive, it is assumed to be in UTC.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # assume UTC for naive datetimes
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    zone = get_zoneinfo(tz_name)
    return dt.astimezone(zone)


def format_datetime_local(dt: Optional[datetime], fmt: str = "%Y-%m-%d %H:%M", tz_name: Optional[str] = None) -> str:
    """Format a datetime in the local timezone. Returns 'N/A' for None."""
    if dt is None:
        return "N/A"
    local = to_local(dt, tz_name)
    return local.strftime(fmt)


def format_date_local(d: Optional[date], fmt: str = "%Y-%m-%d") -> str:
    if d is None:
        return "N/A"
    return d.strftime(fmt)

