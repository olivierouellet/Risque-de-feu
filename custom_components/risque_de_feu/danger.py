"""Which of SOPFEU's three days is today, the danger of a place, and the measures in effect."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, time, timedelta

from .api import FIRE_BAN_TYPE, DangerReport, DangerZone, Restriction
from .const import QUEBEC_TZ

DAYS = 3


def quebec_date(moment: datetime) -> date:
    return moment.astimezone(QUEBEC_TZ).date()


def next_midnight(now: datetime) -> datetime:
    """The next midnight in Québec, when "today" moves to SOPFEU's next day."""
    return datetime.combine(quebec_date(now) + timedelta(days=1), time(), QUEBEC_TZ)


def day_offset(report: DangerReport, now: datetime) -> int:
    """Days since the calculation: day 1 is the calculation's day, so before the next one, today is day 2."""
    if report.calculated is None:
        return 0
    return max(0, (quebec_date(now) - report.calculated.date()).days)


def zone_levels(zone: DangerZone, offset: int) -> list[int | None]:
    """Today, tomorrow and the day after for one zone; None past the last calculated day."""
    return [zone.levels[i + offset] if i + offset < DAYS else None for i in range(DAYS)]


def place_levels(report: DangerReport, now: datetime) -> list[int | None]:
    """Today, tomorrow and the day after for the place: the highest of its zones (a municipality can span several)."""
    offset = day_offset(report, now)
    by_zone = [zone_levels(z, offset) for z in report.zones]
    return [max((levels[i] for levels in by_zone if levels[i] is not None), default=None) for i in range(DAYS)]


def in_effect(restrictions: Iterable[Restriction], now: datetime) -> list[Restriction]:
    """The measures that have started and not ended."""
    return [r for r in restrictions if (r.start is None or r.start <= now) and (r.end is None or now < r.end)]


def fire_ban(restrictions: Iterable[Restriction], now: datetime) -> bool:
    """An open-fire ban in or near the forest applies to the place."""
    return any(r.type == FIRE_BAN_TYPE for r in in_effect(restrictions, now))


def alert(level: int | None, banned: bool, threshold: int, include_fire_ban: bool) -> bool:
    """Today's danger reaches the threshold, or a fire ban applies when it counts."""
    return (level is not None and level >= threshold) or (include_fire_ban and banned)
