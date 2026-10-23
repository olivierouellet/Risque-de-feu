"""Data coordinator for Risque de feu."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import DangerReport, Restriction, SopfeuApiError, SopfeuClient, place_params
from .const import (
    CONF_FIRE_BAN,
    CONF_LOCATION,
    CONF_MODE,
    CONF_MUNICIPALITY,
    CONF_THRESHOLD,
    CONF_ZONE,
    DEFAULT_FIRE_BAN,
    DEFAULT_THRESHOLD,
    DOMAIN,
    FETCH_INTERVAL,
    MODE_LOCATION,
    MODE_MUNICIPALITY,
)
from .danger import next_midnight

_LOGGER = logging.getLogger(__name__)

type RisqueDeFeuConfigEntry = ConfigEntry[RisqueDeFeuCoordinator]


@dataclass(frozen=True)
class FireData:
    danger: DangerReport
    restrictions: list[Restriction]


def entry_params(data: dict) -> dict[str, str]:
    """The API query for the entry's place."""
    if data[CONF_MODE] == MODE_LOCATION:
        location = data[CONF_LOCATION]
        return place_params(latitude=location["latitude"], longitude=location["longitude"])
    if data[CONF_MODE] == MODE_MUNICIPALITY:
        return place_params(municipality=data[CONF_MUNICIPALITY])
    return place_params(zone=int(data[CONF_ZONE]))


class RisqueDeFeuCoordinator(DataUpdateCoordinator[FireData]):
    """Fetches the danger and the measures for one place, and moves "today" forward at midnight."""

    config_entry: RisqueDeFeuConfigEntry

    def __init__(self, hass: HomeAssistant, entry: RisqueDeFeuConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=FETCH_INTERVAL,
        )
        self.client = SopfeuClient(async_get_clientsession(hass))
        self.params = entry_params(dict(entry.data))
        self.threshold: int = int(entry.options.get(CONF_THRESHOLD, DEFAULT_THRESHOLD))
        self.include_fire_ban: bool = bool(entry.options.get(CONF_FIRE_BAN, DEFAULT_FIRE_BAN))
        self._unsub_midnight: CALLBACK_TYPE | None = None

    async def _async_update_data(self) -> FireData:
        try:
            danger = await self.client.async_get_danger(self.params)
            restrictions = await self.client.async_get_restrictions(self.params)
        except SopfeuApiError as err:
            if self.data is None:
                raise UpdateFailed(str(err)) from err
            # The levels cover three days: keep the last ones rather than make cards flicker.
            _LOGGER.warning("Could not refresh the fire danger, keeping the last data: %s", err)
            return self.data
        return FireData(danger=danger, restrictions=restrictions)

    @callback
    def schedule_midnight(self) -> None:
        """Polling alone could leave yesterday's level up to 30 minutes into the new day."""
        self.cancel_midnight()
        self._unsub_midnight = async_track_point_in_utc_time(
            self.hass, self._async_midnight, next_midnight(dt_util.utcnow())
        )

    @callback
    def _async_midnight(self, _now: datetime) -> None:
        self._unsub_midnight = None
        self.async_update_listeners()
        self.schedule_midnight()

    @callback
    def cancel_midnight(self) -> None:
        if self._unsub_midnight:
            self._unsub_midnight()
            self._unsub_midnight = None
