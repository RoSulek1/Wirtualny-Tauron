"""Config flow integracji Wirtualny Tauron."""
from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
import voluptuous as vol

from .const import (
    CONF_COEFFICIENT,
    CONF_INITIAL_STORED,
    CONF_SOURCE_FED,
    CONF_SOURCE_RETRIEVED,
    DEFAULT_COEFFICIENT,
    DEFAULT_INITIAL_STORED,
    DOMAIN,
)

ENERGY_SOURCE_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor", device_class="energy")
)

COEFFICIENT_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0, max=1, step=0.001, mode=selector.NumberSelectorMode.BOX
    )
)

INITIAL_STORED_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0,
        max=1000000,
        step=0.1,
        mode=selector.NumberSelectorMode.BOX,
        unit_of_measurement="kWh",
    )
)


def _build_schema(defaults: dict[str, Any], with_initial: bool) -> vol.Schema:
    fields: dict[vol.Marker, Any] = {
        vol.Required(
            CONF_SOURCE_FED, default=defaults.get(CONF_SOURCE_FED, "")
        ): ENERGY_SOURCE_SELECTOR,
        vol.Required(
            CONF_SOURCE_RETRIEVED, default=defaults.get(CONF_SOURCE_RETRIEVED, "")
        ): ENERGY_SOURCE_SELECTOR,
        vol.Required(
            CONF_COEFFICIENT,
            default=defaults.get(CONF_COEFFICIENT, DEFAULT_COEFFICIENT),
        ): COEFFICIENT_SELECTOR,
    }
    if with_initial:
        fields[
            vol.Required(
                CONF_INITIAL_STORED,
                default=defaults.get(CONF_INITIAL_STORED, DEFAULT_INITIAL_STORED),
            )
        ] = INITIAL_STORED_SELECTOR
    return vol.Schema(fields)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Przepływ konfiguracji Wirtualnego Taurona."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            for key in (CONF_SOURCE_FED, CONF_SOURCE_RETRIEVED):
                if self.hass.states.get(user_input[key]) is None:
                    errors[key] = "entity_missing"
            if not errors:
                return self.async_create_entry(
                    title="Wirtualny Tauron", data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(user_input or {}, with_initial=True),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlow:
        return OptionsFlow()


class OptionsFlow(config_entries.OptionsFlow):
    """Opcje: zmiana źródeł i współczynnika (z rebasingiem magazynu)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        entry = self.config_entry
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {**entry.data, **entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(defaults, with_initial=False),
        )
