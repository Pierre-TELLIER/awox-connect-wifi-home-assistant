"""The AwoX Lights integration."""
from __future__ import annotations

from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from awox.config import AppConfig, AwoxConfig, MqttConfig, StorageConfig

from .const import (
    CONF_PASSWORD,
    CONF_TARGET_DEVICE_NAME,
    CONF_USERNAME,
    DEFAULT_MQTT_ENDPOINT,
    DEFAULT_MQTT_PORT,
    DOMAIN,
)
from .hub import AwoxHub

PLATFORMS = ["light"]


def _build_app_config(hass: HomeAssistant, entry: ConfigEntry) -> AppConfig:
    """Build an AppConfig from the config entry + HA's own storage paths.

    Deliberately doesn't touch load_config()/config.yaml - the entry is
    the single source of truth once the integration is set up via the UI.
    """
    storage_dir = Path(hass.config.path(DOMAIN))
    cert_dir = storage_dir / "certs"
    cert_dir.mkdir(parents=True, exist_ok=True)

    return AppConfig(
        awox=AwoxConfig(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            target_device_name=entry.data.get(CONF_TARGET_DEVICE_NAME, ""),
        ),
        mqtt=MqttConfig(
            endpoint=DEFAULT_MQTT_ENDPOINT,
            port=DEFAULT_MQTT_PORT,
        ),
        storage=StorageConfig(
            state_file=storage_dir / "state.yaml",
            certificate_directory=cert_dir,
        ),
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    config = _build_app_config(hass, entry)

    hub = AwoxHub(hass, config)
    await hub.async_setup()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = hub

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hub: AwoxHub = hass.data[DOMAIN][entry.entry_id]
    await hub.async_shutdown()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
