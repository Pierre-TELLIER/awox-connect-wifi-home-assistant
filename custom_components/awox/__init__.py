"""The AwoX Lights integration."""
from __future__ import annotations

import shutil
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from awox.config import AppConfig, AwoxConfig, MqttConfig, StorageConfig

from .const import (
    CONF_PASSWORD, CONF_USERNAME, DEFAULT_MQTT_ENDPOINT, DEFAULT_MQTT_PORT, DOMAIN,
)
from .hub import AwoxHub

PLATFORMS = ["light"]

type AwoxConfigEntry = ConfigEntry[AwoxHub]


def _storage_dir(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(DOMAIN))


def _build_app_config(hass: HomeAssistant, entry: ConfigEntry) -> AppConfig:
    storage_dir = _storage_dir(hass)   # the library creates the dirs itself
    return AppConfig(
        awox=AwoxConfig(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
        ),
        mqtt=MqttConfig(endpoint=DEFAULT_MQTT_ENDPOINT, port=DEFAULT_MQTT_PORT),
        storage=StorageConfig(
            state_file=storage_dir / "state.yaml",
            certificate_directory=storage_dir / "certs",
        ),
    )


async def async_setup_entry(hass: HomeAssistant, entry: AwoxConfigEntry) -> bool:
    hub = AwoxHub(hass, _build_app_config(hass, entry))
    try:
        await hub.async_setup()
    except Exception as err:  # the library raises bare exceptions for now
        await hub.async_shutdown()
        raise ConfigEntryNotReady(f"AwoX setup failed: {err}") from err

    entry.runtime_data = hub
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AwoxConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_shutdown()
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete certificates and state when the integration is removed."""
    await hass.async_add_executor_job(
        shutil.rmtree, _storage_dir(hass), True  # ignore_errors
    )
