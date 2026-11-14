"""Integracja Wirtualny Tauron — emulator magazynu energii dla systemu opustów.

Model (stary system netto / opustów):
    stan_magazynu = stan_bazowy + oddana * współczynnik - pobrana
gdzie "oddana" i "pobrana" to przyrosty energii od momentu instalacji
(konfiguracji lub ostatniej korekty usługą set_stored_energy).
"""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfEnergy
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
import voluptuous as vol

from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_STORED_ENERGY,
    CONF_BASE_STORED,
    CONF_COEFFICIENT,
    CONF_INITIAL_STORED,
    CONF_REF_FED,
    CONF_REF_RETRIEVED,
    CONF_SOURCE_FED,
    CONF_SOURCE_RETRIEVED,
    DEFAULT_COEFFICIENT,
    DEFAULT_INITIAL_STORED,
    DOMAIN,
    PLATFORMS,
    SERVICE_SET_STORED_ENERGY,
    UPDATE_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_STORED_ENERGY): vol.All(
            vol.Coerce(float), vol.Range(min=0)
        ),
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
    }
)


def read_total(hass: HomeAssistant, entity_id: str) -> float | None:
    """Odczytaj licznik energii z encji źródłowej (kWh; Wh przelicza na kWh)."""
    state = hass.states.get(entity_id)
    if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        return None
    try:
        value = float(state.state)
    except (TypeError, ValueError):
        return None
    if state.attributes.get("unit_of_measurement") == UnitOfEnergy.WATT_HOUR:
        value /= 1000.0
    return value


class WirtualnyTauronCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Koordynator przeliczający stan wirtualnego magazynu."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.entry = entry

    @property
    def coefficient(self) -> float:
        """Współczynnik dopisywany za każdą oddaną kWh."""
        return float(
            self.entry.options.get(
                CONF_COEFFICIENT,
                self.entry.data.get(CONF_COEFFICIENT, DEFAULT_COEFFICIENT),
            )
        )

    async def _async_update_data(self) -> dict[str, Any]:
        fed = read_total(self.hass, self.entry.data[CONF_SOURCE_FED])
        retrieved = read_total(self.hass, self.entry.data[CONF_SOURCE_RETRIEVED])

        if fed is None or retrieved is None:
            if self.data:
                # Zachowaj ostatni poprawny wynik, oznacz jako nieaktualny.
                return {**self.data, "stale": True}
            raise UpdateFailed(
                "Encje źródłowe niedostępne: "
                f"{self.entry.data[CONF_SOURCE_FED]}, "
                f"{self.entry.data[CONF_SOURCE_RETRIEVED]}"
            )

        base = float(self.entry.data[CONF_BASE_STORED])
        ref_fed = float(self.entry.data[CONF_REF_FED])
        ref_retrieved = float(self.entry.data[CONF_REF_RETRIEVED])

        fed_since = max(0.0, fed - ref_fed)
        retrieved_since = max(0.0, retrieved - ref_retrieved)
        stored = base + self.coefficient * fed_since - retrieved_since

        return {
            "stored": stored,
            "fed_since": fed_since,
            "retrieved_since": retrieved_since,
            "fed_total": fed,
            "retrieved_total": retrieved,
            "stale": False,
        }


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Rejestracja usług integracji."""

    async def async_handle_set_stored(call: ServiceCall) -> None:
        entries = hass.config_entries.async_entries(DOMAIN)
        entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
        if entry_id:
            entry = next((e for e in entries if e.entry_id == entry_id), None)
            if entry is None:
                _LOGGER.error("Nie znaleziono wpisu konfiguracji %s", entry_id)
                return
        elif len(entries) == 1:
            entry = entries[0]
        else:
            _LOGGER.error(
                "Podaj config_entry_id — zainstalowanych jest %d instancji",
                len(entries),
            )
            return

        fed = read_total(hass, entry.data[CONF_SOURCE_FED])
        retrieved = read_total(hass, entry.data[CONF_SOURCE_RETRIEVED])
        new_data = dict(entry.data)
        new_data[CONF_BASE_STORED] = float(call.data[ATTR_STORED_ENERGY])
        if fed is not None:
            new_data[CONF_REF_FED] = fed
        if retrieved is not None:
            new_data[CONF_REF_RETRIEVED] = retrieved
        hass.config_entries.async_update_entry(entry, data=new_data)

        coordinator: WirtualnyTauronCoordinator | None = hass.data.get(DOMAIN, {}).get(
            entry.entry_id
        )
        if coordinator is not None:
            await coordinator.async_request_refresh()
        _LOGGER.info(
            "Wirtualny Tauron: ustawiono stan magazynu na %.3f kWh",
            float(call.data[ATTR_STORED_ENERGY]),
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_STORED_ENERGY,
        async_handle_set_stored,
        schema=SERVICE_SCHEMA,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Konfiguracja wpisu."""
    hass.data.setdefault(DOMAIN, {})

    data = dict(entry.data)
    if CONF_REF_FED not in data or CONF_REF_RETRIEVED not in data:
        # Pierwsze uruchomienie: punkty odniesienia = aktualne stany źródeł.
        data[CONF_REF_FED] = read_total(hass, data[CONF_SOURCE_FED]) or 0.0
        data[CONF_REF_RETRIEVED] = read_total(hass, data[CONF_SOURCE_RETRIEVED]) or 0.0
        data.setdefault(
            CONF_BASE_STORED,
            float(data.get(CONF_INITIAL_STORED, DEFAULT_INITIAL_STORED)),
        )
        hass.config_entries.async_update_entry(entry, data=data)

    coordinator = WirtualnyTauronCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Usunięcie wpisu."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


@callback
def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reakcja na zmianę opcji: rebase przy zmianie współczynnika lub źródeł."""
    coordinator: WirtualnyTauronCoordinator | None = hass.data[DOMAIN].get(
        entry.entry_id
    )
    if coordinator is None:
        return

    data = dict(entry.data)
    opts = entry.options
    new_coeff = float(
        opts.get(CONF_COEFFICIENT, data.get(CONF_COEFFICIENT, DEFAULT_COEFFICIENT))
    )
    new_fed = opts.get(CONF_SOURCE_FED, data[CONF_SOURCE_FED])
    new_retrieved = opts.get(CONF_SOURCE_RETRIEVED, data[CONF_SOURCE_RETRIEVED])

    coeff_changed = new_coeff != float(
        data.get(CONF_COEFFICIENT, DEFAULT_COEFFICIENT)
    )
    sources_changed = (
        new_fed != data[CONF_SOURCE_FED] or new_retrieved != data[CONF_SOURCE_RETRIEVED]
    )

    if coeff_changed or sources_changed:
        current = coordinator.data or {}
        # Nowy współczynnik/źródła działają od teraz: baza = aktualny stan magazynu.
        data[CONF_BASE_STORED] = float(
            current.get("stored", data.get(CONF_BASE_STORED, 0.0))
        )
        fed = read_total(hass, new_fed)
        retrieved = read_total(hass, new_retrieved)
        if fed is not None:
            data[CONF_REF_FED] = fed
        if retrieved is not None:
            data[CONF_REF_RETRIEVED] = retrieved
        data[CONF_SOURCE_FED] = new_fed
        data[CONF_SOURCE_RETRIEVED] = new_retrieved
        data[CONF_COEFFICIENT] = new_coeff
        hass.config_entries.async_update_entry(entry, data=data)

    coordinator.async_set_updated_data(coordinator.data or {})
