"""Client for SOPFEU's public API: fire danger, preventive measures and municipalities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp

from .const import LEVELS, QUEBEC_TZ

API_URL = "https://geofeux.sopfeu.qc.ca/sopfeu-api/public"
TIMEOUT = aiohttp.ClientTimeout(total=30)

# Every measure type is excluded unless asked for.
RESTRICTION_FILTERS = {
    name: "true"
    for name in (
        "ifco",
        "rtf12_20",
        "rtf24",
        "rtf8_20",
        "prohibitionAcces",
        "fermeture",
        "interdictionVol",
        "zoneRisque",
    )
}
# "Interdiction de faire des feux à ciel ouvert en forêt ou à proximité".
FIRE_BAN_TYPE = 1
MUNICIPALITY_TYPE = 3
REGION_TYPE = 1

# "2026-10-22 14:30:52" for the danger, "2026/10/22 02:39" for the measures.
_DATE = re.compile(r"(\d{4})[-/](\d{2})[-/](\d{2})[ T](\d{1,2}):(\d{2})")


class SopfeuApiError(Exception):
    """The service could not be reached or returned something unexpected."""


@dataclass(frozen=True)
class DangerZone:
    """One fire danger zone and its levels for the three days of the calculation (None when not given)."""

    number: int
    name: str
    levels: tuple[int | None, int | None, int | None]


@dataclass(frozen=True)
class DangerReport:
    """The zones covering a place, and when SOPFEU calculated the danger (day 1 is that day)."""

    zones: tuple[DangerZone, ...]
    calculated: datetime | None


@dataclass(frozen=True)
class Restriction:
    """A preventive measure in effect: an open-fire ban, forestry restrictions, closures, and so on."""

    id: int
    type: int
    rtf_type: int | None
    description_fr: str
    description_en: str
    start: datetime | None
    end: datetime | None


@dataclass(frozen=True)
class Municipality:
    code: str
    name: str
    region: str


def parse_datetime(text: str | None) -> datetime | None:
    """Québec local time from SOPFEU's dates; None when missing or unreadable."""
    match = _DATE.search(text or "")
    if not match:
        return None
    year, month, day, hour, minute = (int(g) for g in match.groups())
    return datetime(year, month, day, hour, minute, tzinfo=QUEBEC_TZ)


def parse_level(day: Any) -> int | None:
    """1 (low) to 5 (extreme); None outside the season or when the value is unknown."""
    if not isinstance(day, dict):
        return None
    try:
        level = int(day.get("Id"))
    except (TypeError, ValueError):
        return None
    return level if level in LEVELS else None


def parse_danger(data: Any) -> DangerReport:
    """The danger report, as served (`[[zones], {date}]`) or as documented (`{"Zones": [...], ...}`)."""
    if isinstance(data, list) and data and isinstance(data[0], list):
        raw_zones = data[0]
        meta = next((x for x in data[1:] if isinstance(x, dict)), {})
    elif isinstance(data, dict):
        raw_zones = data.get("Zones") or []
        meta = data
    else:
        raise SopfeuApiError(f"Unexpected danger response: {str(data)[:100]}")
    try:
        zones = tuple(
            DangerZone(
                number=int(z["NumeroZone"]),
                name=str(z.get("NomZone") or "").strip(),
                levels=(
                    parse_level(z.get("DangerJour1")),
                    parse_level(z.get("DangerJour2")),
                    parse_level(z.get("DangerJour3")),
                ),
            )
            for z in raw_zones
        )
    except (KeyError, TypeError, ValueError) as err:
        raise SopfeuApiError(f"Unexpected danger zone: {err}") from err
    return DangerReport(zones=zones, calculated=parse_datetime(meta.get("DateDernierCalculDanger")))


def parse_restrictions(data: Any) -> list[Restriction]:
    """The measures, without their polygons."""
    if not isinstance(data, list):
        raise SopfeuApiError(f"Unexpected measures response: {str(data)[:100]}")
    try:
        return [
            Restriction(
                id=int(m["MesurePreventiveId"]),
                type=int(m["TypeMesureId"]),
                rtf_type=int(m["TypeRtfId"]) if m.get("TypeRtfId") is not None else None,
                description_fr=str(m.get("DescriptionFr") or "").strip(),
                description_en=str(m.get("DescriptionEn") or "").strip(),
                start=parse_datetime(m.get("DateDebut")),
                end=parse_datetime(m.get("DateFin")),
            )
            for m in data
        ]
    except (KeyError, TypeError, ValueError) as err:
        raise SopfeuApiError(f"Unexpected measure: {err}") from err


def parse_municipalities(data: Any) -> list[Municipality]:
    """Québec's municipalities with their administrative region."""
    if not isinstance(data, list):
        raise SopfeuApiError("Unexpected geographic codes")
    regions = {str(x.get("CodeGeo")): str(x.get("Nom")) for x in data if x.get("Type") == REGION_TYPE}
    return [
        Municipality(
            code=str(x["CodeGeo"]),
            name=str(x["Nom"]),
            region=regions.get(str(x.get("RegionAdministrativeId")), ""),
        )
        for x in data
        if x.get("Type") == MUNICIPALITY_TYPE and x.get("CodeGeo") and x.get("Nom")
    ]


def place_params(
    latitude: float | None = None,
    longitude: float | None = None,
    municipality: str | None = None,
    zone: int | None = None,
) -> dict[str, str]:
    """Query for one place: a point, a municipality (geographic code) or a fire danger zone."""
    if municipality:
        return {"noMun": municipality}
    if zone is not None:
        return {"noZdi": str(zone)}
    if latitude is None or longitude is None:
        raise ValueError("A place needs a point, a municipality or a zone")
    # The service takes up to five decimals.
    return {"lat": f"{latitude:.5f}", "lon": f"{longitude:.5f}"}


class SopfeuClient:
    """Small JSON requests to SOPFEU's public API; no key needed."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _async_get(self, path: str, params: dict[str, str] | None = None) -> Any:
        try:
            async with self._session.get(f"{API_URL}/{path}", params=params, timeout=TIMEOUT) as resp:
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise SopfeuApiError(str(err) or type(err).__name__) from err

    async def async_get_danger(self, params: dict[str, str] | None = None) -> DangerReport:
        """The zones covering the place (every zone without `params`) and their danger."""
        report = parse_danger(await self._async_get("danger-incendie", params))
        if not report.zones:
            raise SopfeuApiError("No fire danger zone returned")
        return report

    async def async_get_restrictions(self, params: dict[str, str]) -> list[Restriction]:
        return parse_restrictions(await self._async_get("mesures-preventives", {**RESTRICTION_FILTERS, **params}))

    async def async_get_municipalities(self) -> list[Municipality]:
        return parse_municipalities(await self._async_get("codes-geographiques"))

    async def async_municipality_at(self, latitude: float, longitude: float) -> str | None:
        """Name of the municipality containing a point, or None outside Québec.

        The danger lookup always answers with the nearest zone, even from Toronto; this one doesn't.
        """
        data = await self._async_get("contour-municipalite", place_params(latitude, longitude))
        if not isinstance(data, list) or not data or not isinstance(data[0], dict):
            return None
        return str(data[0].get("Nom") or "") or None
