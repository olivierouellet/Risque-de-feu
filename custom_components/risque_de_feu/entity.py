"""Common base for the Risque de feu entities."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, INFO_URL
from .coordinator import RisqueDeFeuCoordinator


class RisqueDeFeuEntity(CoordinatorEntity[RisqueDeFeuCoordinator]):
    """One device per place, named after it: "Risque de feu Gaspé"."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: RisqueDeFeuCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Risque de feu {entry.title}",
            manufacturer="SOPFEU",
            model="Danger d’incendie",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=INFO_URL,
        )
