"""Config and options flows for Risque de feu: the place (a point, a municipality or a zone) and the alert threshold."""

from __future__ import annotations

import logging
import unicodedata
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    LocationSelector,
    LocationSelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import Municipality, SopfeuApiError, SopfeuClient, place_params
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
    LEVELS,
    MODE_LOCATION,
    MODE_MUNICIPALITY,
    MODE_ZONE,
)

_LOGGER = logging.getLogger(__name__)


def _sort_key(name: str) -> str:
    """Alphabetical order that ignores accents: Île after Iberville, not after Z."""
    return "".join(c for c in unicodedata.normalize("NFD", name.casefold()) if not unicodedata.combining(c))


def _alert_fields(defaults: dict[str, Any]) -> dict:
    return {
        # Options are strings: selector values and translation keys must be.
        vol.Required(CONF_THRESHOLD, default=str(defaults.get(CONF_THRESHOLD, DEFAULT_THRESHOLD))): SelectSelector(
            SelectSelectorConfig(
                options=[str(level) for level in LEVELS if level > 1],
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="threshold",
            )
        ),
        vol.Required(CONF_FIRE_BAN, default=defaults.get(CONF_FIRE_BAN, DEFAULT_FIRE_BAN)): BooleanSelector(),
    }


def _options(user_input: dict[str, Any]) -> dict[str, Any]:
    return {CONF_THRESHOLD: int(user_input[CONF_THRESHOLD]), CONF_FIRE_BAN: bool(user_input[CONF_FIRE_BAN])}


class RisqueDeFeuConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a place to follow; one entry per place (home, cottage, and so on)."""

    VERSION = 1

    def __init__(self) -> None:
        self._municipalities: list[Municipality] | None = None

    @property
    def _client(self) -> SopfeuClient:
        return SopfeuClient(async_get_clientsession(self.hass))

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=[MODE_LOCATION, MODE_MUNICIPALITY, MODE_ZONE])

    async def async_step_location(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """A point on the map, the home location to start with. Its own zone, and the measures right there."""
        errors: dict[str, str] = {}
        if user_input is not None:
            latitude = float(user_input[CONF_LOCATION]["latitude"])
            longitude = float(user_input[CONF_LOCATION]["longitude"])
            try:
                name = await self._client.async_municipality_at(latitude, longitude)
                if name:
                    await self._client.async_get_danger(place_params(latitude, longitude))
            except SopfeuApiError as err:
                _LOGGER.warning("Could not look up the location: %s", err)
                errors["base"] = "cannot_connect"
            else:
                if not name:
                    errors[CONF_LOCATION] = "outside_quebec"
                else:
                    await self.async_set_unique_id(f"{MODE_LOCATION}_{latitude:.4f}_{longitude:.4f}")
                    self._abort_if_unique_id_configured()
                    data = {CONF_MODE: MODE_LOCATION, CONF_LOCATION: {"latitude": latitude, "longitude": longitude}}
                    return self.async_create_entry(title=name, data=data, options=_options(user_input))

        defaults = user_input or {
            CONF_LOCATION: {"latitude": self.hass.config.latitude, "longitude": self.hass.config.longitude}
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_LOCATION, default=defaults[CONF_LOCATION]): LocationSelector(
                    LocationSelectorConfig(radius=False)
                ),
                **_alert_fields(defaults),
            }
        )
        return self.async_show_form(step_id=MODE_LOCATION, data_schema=schema, errors=errors)

    async def async_step_municipality(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """One of Québec's municipalities; the highest danger of its zones."""
        if self._municipalities is None:
            try:
                self._municipalities = sorted(
                    await self._client.async_get_municipalities(), key=lambda m: _sort_key(m.name)
                )
            except SopfeuApiError as err:
                _LOGGER.warning("Could not load the municipalities: %s", err)
                return self.async_abort(reason="cannot_connect")
        by_code = {m.code: m for m in self._municipalities}

        errors: dict[str, str] = {}
        if user_input is not None:
            chosen = str(user_input[CONF_MUNICIPALITY]).strip()
            # The list accepts typing: take a name as well as a code.
            municipality = by_code.get(chosen) or next(
                (m for m in self._municipalities if _sort_key(m.name) == _sort_key(chosen)), None
            )
            if municipality is None:
                errors[CONF_MUNICIPALITY] = "unknown_municipality"
            else:
                try:
                    await self._client.async_get_danger(place_params(municipality=municipality.code))
                except SopfeuApiError as err:
                    _LOGGER.warning("Could not load the fire danger: %s", err)
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(f"{MODE_MUNICIPALITY}_{municipality.code}")
                    self._abort_if_unique_id_configured()
                    data = {CONF_MODE: MODE_MUNICIPALITY, CONF_MUNICIPALITY: municipality.code}
                    return self.async_create_entry(title=municipality.name, data=data, options=_options(user_input))

        defaults = user_input or {CONF_MUNICIPALITY: await self._async_home_municipality()}
        field = (
            vol.Required(CONF_MUNICIPALITY, default=defaults[CONF_MUNICIPALITY])
            if defaults[CONF_MUNICIPALITY]
            else vol.Required(CONF_MUNICIPALITY)
        )
        schema = vol.Schema(
            {
                field: SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=m.code, label=f"{m.name} · {m.region}" if m.region else m.name)
                            for m in self._municipalities
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                        # A searchable list: there are more than 1,300.
                        custom_value=True,
                    )
                ),
                **_alert_fields(defaults),
            }
        )
        return self.async_show_form(step_id=MODE_MUNICIPALITY, data_schema=schema, errors=errors)

    async def async_step_zone(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """One of SOPFEU's fire danger zones."""
        try:
            zones = sorted((await self._client.async_get_danger()).zones, key=lambda z: z.number)
        except SopfeuApiError as err:
            _LOGGER.warning("Could not load the fire danger zones: %s", err)
            return self.async_abort(reason="cannot_connect")
        names = {str(z.number): z.name for z in zones}

        if user_input is not None and user_input[CONF_ZONE] in names:
            number = user_input[CONF_ZONE]
            await self.async_set_unique_id(f"{MODE_ZONE}_{number}")
            self._abort_if_unique_id_configured()
            data = {CONF_MODE: MODE_ZONE, CONF_ZONE: int(number)}
            return self.async_create_entry(title=names[number], data=data, options=_options(user_input))

        defaults = user_input or {CONF_ZONE: await self._async_home_zone()}
        schema = vol.Schema(
            {
                vol.Required(CONF_ZONE, default=defaults[CONF_ZONE] or str(zones[0].number)): SelectSelector(
                    SelectSelectorConfig(
                        options=[SelectOptionDict(value=str(z.number), label=f"{z.number} · {z.name}") for z in zones],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                **_alert_fields(defaults),
            }
        )
        return self.async_show_form(step_id=MODE_ZONE, data_schema=schema)

    async def _async_home_municipality(self) -> str | None:
        """The code of the municipality of the Home Assistant home location, when it is in Québec."""
        try:
            name = await self._client.async_municipality_at(self.hass.config.latitude, self.hass.config.longitude)
        except SopfeuApiError as err:
            _LOGGER.debug("Could not find the municipality of the home location: %s", err)
            return None
        return next((m.code for m in self._municipalities or [] if m.name == name), None)

    async def _async_home_zone(self) -> str | None:
        """The zone of the Home Assistant home location, when it is in Québec."""
        latitude, longitude = self.hass.config.latitude, self.hass.config.longitude
        try:
            if not await self._client.async_municipality_at(latitude, longitude):
                return None
            report = await self._client.async_get_danger(place_params(latitude, longitude))
        except SopfeuApiError as err:
            _LOGGER.debug("Could not find the zone of the home location: %s", err)
            return None
        return str(report.zones[0].number)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> RisqueDeFeuOptionsFlow:
        return RisqueDeFeuOptionsFlow()


class RisqueDeFeuOptionsFlow(OptionsFlow):
    """Change the alert threshold, and whether a fire ban turns the alert on."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=_options(user_input))
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(_alert_fields(dict(self.config_entry.options)))
        )
