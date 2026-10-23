"""Binary sensors for Risque de feu: the alert for card visibility, and the open-fire ban."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import Restriction
from .coordinator import RisqueDeFeuConfigEntry, RisqueDeFeuCoordinator
from .danger import alert, day_offset, fire_ban, in_effect, place_levels, zone_levels
from .entity import RisqueDeFeuEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: RisqueDeFeuConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the alert and fire ban sensors."""
    coordinator = entry.runtime_data
    async_add_entities([AlertSensor(coordinator), FireBanSensor(coordinator)])


def restriction_attributes(restriction: Restriction) -> dict[str, Any]:
    return {
        "type": restriction.type,
        "rtf_type": restriction.rtf_type,
        "description_fr": restriction.description_fr,
        "description_en": restriction.description_en,
        "start": restriction.start.isoformat() if restriction.start else None,
        "end": restriction.end.isoformat() if restriction.end else None,
    }


class AlertSensor(RisqueDeFeuEntity, BinarySensorEntity):
    """On when today's danger reaches the threshold, or (optionally) a fire ban applies.

    Meant for card visibility; the Risque de feu card reads its `fire_zones` attribute.
    """

    _attr_translation_key = "alert"
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, coordinator: RisqueDeFeuCoordinator) -> None:
        super().__init__(coordinator, "alert")

    @property
    def is_on(self) -> bool:
        c = self.coordinator
        now = dt_util.utcnow()
        level = place_levels(c.data.danger, now)[0]
        return alert(level, fire_ban(c.data.restrictions, now), c.threshold, c.include_fire_ban)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        c = self.coordinator
        now = dt_util.utcnow()
        danger = c.data.danger
        offset = day_offset(danger, now)
        levels = place_levels(danger, now)
        return {
            "place": c.config_entry.title,
            "level": levels[0],
            "levels": levels,
            "threshold": c.threshold,
            "include_fire_ban": c.include_fire_ban,
            "fire_ban": fire_ban(c.data.restrictions, now),
            "fire_zones": [
                {"number": z.number, "name": z.name, "levels": zone_levels(z, offset)} for z in danger.zones
            ],
            "restrictions": [restriction_attributes(r) for r in in_effect(c.data.restrictions, now)],
            "calculated": danger.calculated.isoformat() if danger.calculated else None,
        }


class FireBanSensor(RisqueDeFeuEntity, BinarySensorEntity):
    """On while an open-fire ban in or near the forest applies to the place."""

    _attr_translation_key = "fire_ban"

    def __init__(self, coordinator: RisqueDeFeuCoordinator) -> None:
        super().__init__(coordinator, "fire_ban")

    @property
    def is_on(self) -> bool:
        return fire_ban(self.coordinator.data.restrictions, dt_util.utcnow())

    @property
    def icon(self) -> str:
        return "mdi:campfire" if self.is_on else "mdi:fire-off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        restrictions = in_effect(self.coordinator.data.restrictions, dt_util.utcnow())
        return {"restrictions": [restriction_attributes(r) for r in restrictions]}
