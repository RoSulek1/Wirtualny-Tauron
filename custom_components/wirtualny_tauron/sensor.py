"""Sensory integracji Wirtualny Tauron."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WirtualnyTauronCoordinator
from .const import (
    CONF_BASE_STORED,
    CONF_SOURCE_FED,
    CONF_SOURCE_RETRIEVED,
    DOMAIN,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Dodaj sensory wpisu."""
    coordinator: WirtualnyTauronCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            MagazynSensor(coordinator, entry),
            DopisaneSensor(coordinator, entry),
            OddaneSensor(coordinator, entry),
            PobraneSensor(coordinator, entry),
        ]
    )


class WirtualnyTauronSensor(CoordinatorEntity[WirtualnyTauronCoordinator], SensorEntity):
    """Bazowa klasa sensory Wirtualnego Taurona."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WirtualnyTauronCoordinator,
        entry: ConfigEntry,
        kind: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{kind}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Wirtualny Tauron",
            manufacturer="RoSulek1",
            model="Emulator magazynu energii (system opustów)",
            sw_version="1.1.0",
        )


class MagazynSensor(WirtualnyTauronSensor):
    """Stan wirtualnego magazynu (kWh do odebrania u sprzedawcy)."""

    _attr_name = "Magazyn"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY_STORAGE
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:battery-charging"
    _attr_suggested_display_precision = 2

    def __init__(
        self, coordinator: WirtualnyTauronCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "magazyn")

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data:
            return None
        return round(float(data["stored"]), 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "coefficient": self.coordinator.coefficient,
            "source_fed": self._entry.data[CONF_SOURCE_FED],
            "source_retrieved": self._entry.data[CONF_SOURCE_RETRIEVED],
            "base_stored": self._entry.data.get(CONF_BASE_STORED),
            "stale": bool(data.get("stale", False)),
        }


class DopisaneSensor(WirtualnyTauronSensor):
    """Energia dopisana do wirtualnego magazynu (stan + wspolczynnik * oddana).

    Licznik total_increasing dla panelu Energii (pole "energia wprowadzona
    do magazynu"). Zawiera w sobie stan poczatkowy, wiec panel wyliczy
    poziom magazynu jako: dopisane - pobrane.
    """

    _attr_name = "Dopisane do magazynu"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:battery-arrow-up"
    _attr_suggested_display_precision = 2

    def __init__(
        self, coordinator: WirtualnyTauronCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "dopisane")

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data:
            return None
        return round(
            float(data["stored"]) + float(data["retrieved_since"]), 3
        )


class OddaneSensor(WirtualnyTauronSensor):
    """Energia oddana do sieci od instalacji komponentu."""

    _attr_name = "Oddane od instalacji"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:transmission-tower-export"
    _attr_suggested_display_precision = 2

    def __init__(
        self, coordinator: WirtualnyTauronCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "oddane")

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data:
            return None
        return round(float(data["fed_since"]), 3)


class PobraneSensor(WirtualnyTauronSensor):
    """Energia pobrana z sieci od instalacji komponentu."""

    _attr_name = "Pobrane od instalacji"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:transmission-tower-import"
    _attr_suggested_display_precision = 2

    def __init__(
        self, coordinator: WirtualnyTauronCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "pobrane")

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data:
            return None
        return round(float(data["retrieved_since"]), 3)
