"""Stałe integracji Wirtualny Tauron."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "wirtualny_tauron"
PLATFORMS: list[Platform] = [Platform.SENSOR]

# Klucze konfiguracji (config entry)
CONF_SOURCE_FED = "source_fed"
CONF_SOURCE_RETRIEVED = "source_retrieved"
CONF_COEFFICIENT = "coefficient"
CONF_INITIAL_STORED = "initial_stored"

# Stan wewnętrzny przechowywany w config entry (przeżywa restarty)
CONF_BASE_STORED = "base_stored"
CONF_REF_FED = "ref_fed"
CONF_REF_RETRIEVED = "ref_retrieved"

DEFAULT_COEFFICIENT = 0.8
DEFAULT_INITIAL_STORED = 0.0

# Usługa
SERVICE_SET_STORED_ENERGY = "set_stored_energy"
ATTR_STORED_ENERGY = "stored_energy"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"

# Częstotliwość przeliczania (sekundy)
UPDATE_INTERVAL_SECONDS = 30
