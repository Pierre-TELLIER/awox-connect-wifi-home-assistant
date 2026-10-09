"""Config flow for AwoX Lights.

Only asks for what actually varies per user: AwoX account credentials
and (optionally) which device to control. MQTT endpoint/port and
storage locations are fixed/derived - see __init__.py.
"""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector
import requests

from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN
from awox.parse.client import ParseClient

def _check_login(username: str, password: str) -> None:
    ParseClient(username, password, requests.Session())  # raises on failure


STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
    }
)


class AwoxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_USERNAME].strip().lower())
            self._abort_if_unique_id_configured()
            try:
                await self.hass.async_add_executor_job(
                    _check_login, user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
            except requests.RequestException:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001  (library raises a bare Exception on bad credentials)
                errors["base"] = "invalid_auth"
            else:
                return self.async_create_entry(title=user_input[CONF_USERNAME], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
