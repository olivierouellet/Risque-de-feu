"""Sensors for Risque de feu: the fire danger today, tomorrow and the day after."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import LEVELS
from .coordinator import RisqueDeFeuConfigEntry, RisqueDeFeuCoordinator
from .danger import day_offset, place_levels, quebec_date, zone_levels
from .entity import RisqueDeFeuEntity

DAY_KEYS = ("danger", "danger_tomorrow", "danger_day_after")


async def async_setup_entry(
    hass: HomeAssistant, entry: RisqueDeFeuConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up one danger sensor per day."""
    coordinator = entry.runtime_data
    async_add_entities(DangerSensor(coordinator, day) for day in range(len(DAY_KEYS)))


class DangerSensor(RisqueDeFeuEntity, SensorEntity):
    """SOPFEU's fire danger for one day: low, moderate, high, very high or extreme.

    Where the place spans several zones (large municipalities), the highest of them.
    """

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:fire"

    def __init__(self, coordinator: RisqueDeFeuCoordinator, day: int) -> None:
        super().__init__(coordinator, DAY_KEYS[day])
        self._day = day
        self._attr_translation_key = DAY_KEYS[day]
        self._attr_options = list(LEVELS.values())

    def _level(self) -> int | None:
        return place_levels(self.coordinator.data.danger, dt_util.utcnow())[self._day]

    @property
    def native_value(self) -> str | None:
        level = self._level()
        return LEVELS[level] if level else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        now = dt_util.utcnow()
        danger = self.coordinator.data.danger
        offset = day_offset(danger, now)
        return {
            "level": self._level(),
            "date": (quebec_date(now) + timedelta(days=self._day)).isoformat(),
            "zones": [
                {"number": z.number, "name": z.name, "level": zone_levels(z, offset)[self._day]} for z in danger.zones
            ],
        }
