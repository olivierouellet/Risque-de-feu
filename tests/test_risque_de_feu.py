"""Tests for the Risque de feu integration: parsing, day logic, flows and entities."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.risque_de_feu.api import (
    DangerReport,
    DangerZone,
    SopfeuApiError,
    parse_danger,
    parse_datetime,
    parse_level,
    parse_municipalities,
    parse_restrictions,
    place_params,
)
from custom_components.risque_de_feu.const import DOMAIN, QUEBEC_TZ
from custom_components.risque_de_feu.danger import alert, fire_ban, in_effect, next_midnight, place_levels

from .conftest import AFTER_CALCULATION, TORONTO, load_text

INTEGRATION = Path(__file__).parent.parent / "custom_components" / DOMAIN
SAGUENAY_IDS = "risque_de_feu_saguenay"


def _local(*args: int) -> datetime:
    return datetime(*args, tzinfo=QUEBEC_TZ)


# ---------- parsing and day logic ----------


def test_parse_recorded_danger() -> None:
    report = parse_danger(json.loads(load_text("danger_all.json")))
    assert len(report.zones) == 64
    assert report.calculated == _local(2026, 10, 22, 14, 30)
    saguenay = next(z for z in report.zones if z.number == 31)
    assert saguenay.name == "Saguenay"
    assert parse_danger(json.loads(load_text("danger_saguenay.json"))).zones == (saguenay,)


def test_parse_documented_shape_and_unknown_levels() -> None:
    """The Swagger documents an object; the service sends a list. Both work."""
    report = parse_danger(
        {
            "Zones": [{"NumeroZone": 12, "NomZone": "Pontiac", "DangerJour1": {"Id": 0}, "DangerJour2": None}],
            "DateDernierCalculDanger": "2024/06/08 14:11:23",
        }
    )
    assert report == DangerReport(
        zones=(DangerZone(12, "Pontiac", (None, None, None)),), calculated=_local(2024, 6, 8, 14, 11)
    )
    assert parse_level({"Id": "5"}) == 5
    assert parse_level({"Id": 6}) is None
    assert parse_datetime("bientôt") is None
    with pytest.raises(SopfeuApiError):
        parse_danger("<html>")
    with pytest.raises(SopfeuApiError):
        parse_danger([[{"NomZone": "sans numéro"}], {}])


def test_parse_restrictions_and_municipalities() -> None:
    restrictions = parse_restrictions(json.loads(load_text("mesures_test_zone_6.json")))
    assert [(r.type, r.rtf_type) for r in restrictions] == [(2, 3), (1, None), (2, 1)]
    assert restrictions[1].description_en == "Ban on open fires"
    assert restrictions[1].start == _local(2026, 10, 22, 2, 42)
    assert restrictions[1].end == _local(2026, 11, 2, 2, 42)

    municipalities = {m.code: m for m in parse_municipalities(json.loads(load_text("codes_geographiques.json")))}
    assert municipalities["03005"].name == "Gaspé"
    assert municipalities["03005"].region == "Gaspésie - Îles-de-la-Madeleine"
    assert "1" not in municipalities  # administrative regions are not places


def test_place_params() -> None:
    assert place_params(48.43, -71.07) == {"lat": "48.43000", "lon": "-71.07000"}
    assert place_params(municipality="03005") == {"noMun": "03005"}
    assert place_params(zone=31) == {"noZdi": "31"}


def test_today_moves_with_the_calendar() -> None:
    """Day 1 is the calculation's day: the next day, before a new calculation, today is day 2."""
    report = DangerReport(
        zones=(DangerZone(1, "A", (2, 4, 3)), DangerZone(2, "B", (3, 1, None))), calculated=_local(2026, 7, 1, 14, 30)
    )
    assert place_levels(report, _local(2026, 7, 1, 23, 59)) == [3, 4, 3]  # the highest of the zones
    assert place_levels(report, _local(2026, 7, 2, 0, 0)) == [4, 3, None]
    assert place_levels(report, _local(2026, 7, 3, 9, 0)) == [3, None, None]
    assert place_levels(report, _local(2026, 7, 4, 9, 0)) == [None, None, None]  # stale: off season
    assert next_midnight(_local(2026, 7, 1, 14, 0)) == _local(2026, 7, 2, 0, 0)


def test_fire_ban_and_alert() -> None:
    restrictions = parse_restrictions(json.loads(load_text("mesures_test_zone_6.json")))
    assert not fire_ban(restrictions, _local(2026, 10, 22, 2, 41))
    assert fire_ban(restrictions, _local(2026, 10, 22, 2, 42))
    assert not fire_ban(restrictions, _local(2026, 11, 2, 2, 42))
    assert in_effect(restrictions, _local(2026, 11, 2, 2, 42)) == []

    assert alert(3, False, 3, True)
    assert not alert(2, False, 3, True)
    assert alert(2, True, 3, True)
    assert not alert(2, True, 3, False)
    assert not alert(None, False, 2, True)


def test_translations_match_strings() -> None:
    """en.json is a copy of strings.json, and fr.json has exactly the same keys."""

    def keys(node, path=""):
        if isinstance(node, dict):
            return {k for key, value in node.items() for k in keys(value, f"{path}.{key}")}
        return {path}

    strings = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
    for language in ("en", "fr"):
        translation = json.loads((INTEGRATION / "translations" / f"{language}.json").read_text(encoding="utf-8"))
        assert keys(translation) == keys(strings), language
    assert json.loads((INTEGRATION / "translations" / "en.json").read_text(encoding="utf-8")) == strings


# ---------- config and options flows ----------


async def _start(hass: HomeAssistant, mode: str) -> dict:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["location", "municipality", "zone"]
    return await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": mode})


async def _add(hass: HomeAssistant, mode: str, user_input: dict) -> config_entries.ConfigEntry:
    result = await _start(hass, mode)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"threshold": "3", "fire_ban": True, **user_input}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY, result
    await hass.async_block_till_done()
    return result["result"]


@pytest.mark.freeze_time(AFTER_CALCULATION)
async def test_location_flow_defaults_to_home(quebec_home, sopfeu_api) -> None:
    hass = quebec_home
    result = await _start(hass, "location")
    assert result["type"] is FlowResultType.FORM
    defaults = result["data_schema"]({})
    assert defaults["location"] == {"latitude": 48.43, "longitude": -71.07}
    assert defaults["threshold"] == "3"
    assert defaults["fire_ban"] is True

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {**defaults, "threshold": "4"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Saguenay"
    assert result["data"] == {"mode": "location", "location": {"latitude": 48.43, "longitude": -71.07}}
    assert result["result"].options == {"threshold": 4, "fire_ban": True}


async def test_location_flow_rejects_points_outside_quebec(quebec_home, sopfeu_api) -> None:
    hass = quebec_home
    result = await _start(hass, "location")
    latitude, longitude = TORONTO
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"location": {"latitude": latitude, "longitude": longitude}, "threshold": "3", "fire_ban": True},
    )
    assert result["errors"] == {"location": "outside_quebec"}


async def test_location_flow_service_down(quebec_home, aioclient_mock: AiohttpClientMocker) -> None:
    hass = quebec_home
    aioclient_mock.get("https://geofeux.sopfeu.qc.ca/sopfeu-api/public/contour-municipalite", status=503)
    result = await _start(hass, "location")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"location": {"latitude": 48.43, "longitude": -71.07}, "threshold": "3", "fire_ban": True}
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_municipality_flow(quebec_home, sopfeu_api) -> None:
    hass = quebec_home
    result = await _start(hass, "municipality")
    assert result["data_schema"]({"threshold": "3", "fire_ban": True})["municipality"] == "94068"  # Saguenay

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"municipality": "Nulle-Part", "threshold": "3", "fire_ban": True}
    )
    assert result["errors"] == {"municipality": "unknown_municipality"}

    # Typed rather than picked: the name works too, whatever the accents and case.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"municipality": "la tuque", "threshold": "2", "fire_ban": False}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "La Tuque"
    assert result["data"] == {"mode": "municipality", "municipality": "90012"}
    assert result["result"].options == {"threshold": 2, "fire_ban": False}


async def test_zone_flow_and_duplicates(quebec_home, sopfeu_api) -> None:
    hass = quebec_home
    result = await _start(hass, "zone")
    assert result["data_schema"]({"threshold": "3", "fire_ban": True})["zone"] == "31"  # Saguenay's zone
    await _add(hass, "zone", {"zone": "6"})

    result = await _start(hass, "zone")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"zone": "6", "threshold": "3", "fire_ban": True}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_zone_flow_service_down(quebec_home, aioclient_mock: AiohttpClientMocker) -> None:
    hass = quebec_home
    aioclient_mock.get("https://geofeux.sopfeu.qc.ca/sopfeu-api/public/danger-incendie", status=500)
    result = await _start(hass, "zone")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


# ---------- entities ----------


@pytest.mark.freeze_time(AFTER_CALCULATION)
async def test_entities_for_a_point(quebec_home, sopfeu_api) -> None:
    hass = quebec_home
    await _add(hass, "location", {"location": {"latitude": 48.43, "longitude": -71.07}})

    today = hass.states.get(f"sensor.{SAGUENAY_IDS}_danger")
    assert today.state == "moderate"
    assert today.attributes["level"] == 2
    assert today.attributes["date"] == "2026-10-22"
    assert today.attributes["zones"] == [{"number": 31, "name": "Saguenay", "level": 2}]
    assert hass.states.get(f"sensor.{SAGUENAY_IDS}_danger_tomorrow").state == "low"
    assert hass.states.get(f"sensor.{SAGUENAY_IDS}_danger_day_after_tomorrow").state == "low"

    alert_state = hass.states.get(f"binary_sensor.{SAGUENAY_IDS}_alert")
    assert alert_state.state == "off"  # moderate, below "high"
    assert alert_state.attributes["levels"] == [2, 1, 1]
    assert alert_state.attributes["place"] == "Saguenay"
    assert alert_state.attributes["fire_zones"] == [{"number": 31, "name": "Saguenay", "levels": [2, 1, 1]}]
    assert alert_state.attributes["calculated"] == "2026-10-22T14:30:00-04:00"
    assert hass.states.get(f"binary_sensor.{SAGUENAY_IDS}_fire_ban").state == "off"


@pytest.mark.freeze_time(AFTER_CALCULATION)
async def test_entities_with_a_fire_ban(quebec_home, sopfeu_api) -> None:
    hass = quebec_home
    await _add(hass, "zone", {"zone": "6"})

    assert hass.states.get("sensor.risque_de_feu_megiscane_gouin_danger").state == "high"
    assert hass.states.get("sensor.risque_de_feu_megiscane_gouin_danger_tomorrow").state == "very_high"
    assert hass.states.get("binary_sensor.risque_de_feu_megiscane_gouin_alert").state == "on"
    ban = hass.states.get("binary_sensor.risque_de_feu_megiscane_gouin_fire_ban")
    assert ban.state == "on"
    assert [r["description_en"] for r in ban.attributes["restrictions"]] == [
        "Forestry operations restrictions (8h/20h)",
        "Ban on open fires",
        "Forestry operations restrictions (Noon/20h)",
    ]
    assert ban.attributes["restrictions"][1]["end"] == "2026-11-02T02:42:00-05:00"


@pytest.mark.freeze_time(AFTER_CALCULATION)
async def test_municipality_spanning_zones_takes_the_highest(quebec_home, sopfeu_api) -> None:
    hass = quebec_home
    await _add(hass, "municipality", {"municipality": "90012"})
    alert_state = hass.states.get("binary_sensor.risque_de_feu_la_tuque_alert")
    assert len(alert_state.attributes["fire_zones"]) == 8
    assert alert_state.attributes["levels"] == [2, 2, 2]


@pytest.mark.freeze_time(AFTER_CALCULATION)
async def test_today_moves_at_midnight(quebec_home, sopfeu_api, freezer: FrozenDateTimeFactory) -> None:
    hass = quebec_home
    await _add(hass, "location", {"location": {"latitude": 48.43, "longitude": -71.07}})

    midnight = _local(2026, 10, 23, 0, 0)
    freezer.move_to(midnight)
    async_fire_time_changed(hass, midnight)
    await hass.async_block_till_done()
    assert hass.states.get(f"sensor.{SAGUENAY_IDS}_danger").state == "low"  # the calculation's day 2
    assert hass.states.get(f"sensor.{SAGUENAY_IDS}_danger_day_after_tomorrow").state == "unknown"


@pytest.mark.freeze_time(AFTER_CALCULATION)
async def test_options_change_the_threshold(quebec_home, sopfeu_api) -> None:
    hass = quebec_home
    entry = await _add(hass, "location", {"location": {"latitude": 48.43, "longitude": -71.07}})
    assert hass.states.get(f"binary_sensor.{SAGUENAY_IDS}_alert").state == "off"

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["data_schema"]({})["threshold"] == "3"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"threshold": "2", "fire_ban": True})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    alert_state = hass.states.get(f"binary_sensor.{SAGUENAY_IDS}_alert")
    assert alert_state.state == "on"
    assert alert_state.attributes["threshold"] == 2


@pytest.mark.freeze_time(AFTER_CALCULATION)
async def test_service_down_keeps_last_data(quebec_home, sopfeu_api, freezer: FrozenDateTimeFactory) -> None:
    hass = quebec_home
    await _add(hass, "location", {"location": {"latitude": 48.43, "longitude": -71.07}})
    sopfeu_api.clear_requests()
    sopfeu_api.get("https://geofeux.sopfeu.qc.ca/sopfeu-api/public/danger-incendie", status=503)

    freezer.tick(timedelta(minutes=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert len(sopfeu_api.mock_calls) == 1
    assert hass.states.get(f"sensor.{SAGUENAY_IDS}_danger").state == "moderate"


async def test_setup_fails_when_service_down(quebec_home, aioclient_mock: AiohttpClientMocker) -> None:
    hass = quebec_home
    aioclient_mock.get("https://geofeux.sopfeu.qc.ca/sopfeu-api/public/danger-incendie", status=503)
    entry = MockConfigEntry(domain=DOMAIN, title="Saguenay", data={"mode": "zone", "zone": 31})
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is config_entries.ConfigEntryState.SETUP_RETRY


@pytest.mark.freeze_time(AFTER_CALCULATION)
async def test_french_entity_ids(quebec_home, sopfeu_api) -> None:
    """The IDs the README gives for a Home Assistant set to French."""
    hass = quebec_home
    hass.config.language = "fr"
    await _add(hass, "location", {"location": {"latitude": 48.43, "longitude": -71.07}})

    assert hass.states.get(f"sensor.{SAGUENAY_IDS}_danger") is not None
    assert hass.states.get(f"sensor.{SAGUENAY_IDS}_danger_demain").state == "low"
    assert hass.states.get(f"sensor.{SAGUENAY_IDS}_danger_apres_demain") is not None
    alert_state = hass.states.get(f"binary_sensor.{SAGUENAY_IDS}_alerte")
    assert alert_state.attributes["friendly_name"] == "Risque de feu Saguenay Alerte"
    assert hass.states.get(f"binary_sensor.{SAGUENAY_IDS}_interdiction_de_feux").state == "off"
