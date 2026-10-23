"""Risque de feu: SOPFEU's forest fire danger in Québec for Home Assistant."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import RisqueDeFeuConfigEntry, RisqueDeFeuCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: RisqueDeFeuConfigEntry) -> bool:
    """Set up one place from a config entry."""
    coordinator = RisqueDeFeuCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    coordinator.schedule_midnight()
    entry.async_on_unload(coordinator.cancel_midnight)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RisqueDeFeuConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: RisqueDeFeuConfigEntry) -> None:
    """Reload when the threshold changes."""
    await hass.config_entries.async_reload(entry.entry_id)
