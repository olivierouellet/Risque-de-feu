"""Fixtures for the Risque de feu tests."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FIXTURES = Path(__file__).parent / "fixtures"

# Recorded 2026-10-22, calculated that day at 14:30. Saguenay (zone 31): moderate, low, low.
# La Tuque spans 8 zones. Zone 6 with `test=true`: high, very high, high, with an open-fire ban
# and two forestry restrictions from 2026-10-22 02:42 to 2026-11-02 02:42.
AFTER_CALCULATION = "2026-10-22T20:00:00+00:00"  # 16:00 in Québec
SAGUENAY = (48.43, -71.07)
TORONTO = (43.65, -79.38)


def load_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/ in every test."""
    yield


@pytest.fixture
async def quebec_home(hass):
    """Home Assistant located in Saguenay."""
    await hass.config.async_set_time_zone("America/Toronto")
    hass.config.latitude, hass.config.longitude = SAGUENAY
    hass.config.country = "CA"
    return hass


@pytest.fixture
def sopfeu_api(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """Serve recorded SOPFEU responses. The first matching pattern wins."""
    api = "https://geofeux.sopfeu.qc.ca/sopfeu-api/public/"
    aioclient_mock.get(re.compile(r"contour-municipalite\?.*lat=48\.43"), text=load_text("contour_saguenay.json"))
    aioclient_mock.get(re.compile(r"contour-municipalite"), text="[]")
    aioclient_mock.get(re.compile(r"danger-incendie\?.*noZdi=6"), text=load_text("danger_test_zone_6.json"))
    aioclient_mock.get(re.compile(r"danger-incendie\?.*noMun=90012"), text=load_text("danger_la_tuque.json"))
    aioclient_mock.get(re.compile(r"danger-incendie\?.*lat="), text=load_text("danger_saguenay.json"))
    aioclient_mock.get(f"{api}danger-incendie", text=load_text("danger_all.json"))
    aioclient_mock.get(re.compile(r"mesures-preventives\?.*noZdi=6"), text=load_text("mesures_test_zone_6.json"))
    aioclient_mock.get(re.compile(r"mesures-preventives"), text="[]")
    aioclient_mock.get(f"{api}codes-geographiques", text=load_text("codes_geographiques.json"))
    return aioclient_mock
