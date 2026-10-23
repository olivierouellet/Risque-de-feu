"""Constants for the Risque de feu integration."""

from datetime import timedelta
from zoneinfo import ZoneInfo

DOMAIN = "risque_de_feu"

# How the place was chosen, and what is stored for it.
CONF_MODE = "mode"
MODE_LOCATION = "location"
MODE_MUNICIPALITY = "municipality"
MODE_ZONE = "zone"
CONF_LOCATION = "location"
CONF_MUNICIPALITY = "municipality"
CONF_ZONE = "zone"

CONF_THRESHOLD = "threshold"
CONF_FIRE_BAN = "fire_ban"

# SOPFEU's five fire danger levels; the states of the danger sensors.
LEVELS = {1: "low", 2: "moderate", 3: "high", 4: "very_high", 5: "extreme"}
DEFAULT_THRESHOLD = 3
DEFAULT_FIRE_BAN = True

# The danger is calculated once or twice a day; restrictions can start at any time.
FETCH_INTERVAL = timedelta(minutes=30)

# SOPFEU's dates and times are Québec local time.
QUEBEC_TZ = ZoneInfo("America/Toronto")

ATTRIBUTION = "Données : SOPFEU, Société de protection des forêts contre le feu"
INFO_URL = "https://www.sopfeu.qc.ca/prevention/danger-incendie/"
