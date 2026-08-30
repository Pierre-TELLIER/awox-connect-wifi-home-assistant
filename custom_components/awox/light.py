"""Light platform for AwoX Lights."""
from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .hub import AwoxHub


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub: AwoxHub = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        AwoxLightEntity(hub, device_uuid)
        for device_uuid in hub.state.devices
    )


class AwoxLightEntity(LightEntity):
    """A single bulb. State is optimistic - see hub.py for why."""

    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_supported_color_modes = {ColorMode.RGB, ColorMode.COLOR_TEMP}

    # PLACEHOLDER: adjust to the bulb's real range once you know it. This
    # only affects how HA's kelvin slider maps onto your 0-100 scale.
    _attr_min_color_temp_kelvin = 2000
    _attr_max_color_temp_kelvin = 6500

    def __init__(self, hub: AwoxHub, device_uuid: str) -> None:
        self._hub = hub
        self._device_uuid = device_uuid
        device = hub.state.devices[device_uuid]

        self._attr_unique_id = device_uuid
        self._attr_name = device.udn or device_uuid

        self._attr_is_on = False
        self._attr_brightness: int | None = None
        self._attr_rgb_color: tuple[int, int, int] | None = None
        self._attr_color_temp_kelvin: int | None = None
        # Device is either RGB or color-temp, never both - this is the
        # single source of truth for which one HA currently shows as active.
        self._attr_color_mode = ColorMode.COLOR_TEMP

    async def async_turn_on(self, **kwargs: Any) -> None:
        if ATTR_BRIGHTNESS in kwargs:
            ha_brightness = kwargs[ATTR_BRIGHTNESS]  # HA scale: 0-255
            device_brightness = round(ha_brightness * 100 / 255)  # your API: 0-100
            await self._hub.async_set_brightness(self._device_uuid, device_brightness)
            self._attr_brightness = ha_brightness

        if ATTR_RGB_COLOR in kwargs:
            r, g, b = kwargs[ATTR_RGB_COLOR]
            await self._hub.async_set_color(self._device_uuid, r, g, b)
            self._attr_rgb_color = (r, g, b)
            self._attr_color_mode = ColorMode.RGB

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
            span = self._attr_max_color_temp_kelvin - self._attr_min_color_temp_kelvin
            device_temp = round((kelvin - self._attr_min_color_temp_kelvin) / span * 100)
            device_temp = max(0, min(100, device_temp))  # clamp, just in case
            await self._hub.async_set_temperature(self._device_uuid, device_temp)
            self._attr_color_temp_kelvin = kelvin
            self._attr_color_mode = ColorMode.COLOR_TEMP

        await self._hub.async_turn_on(self._device_uuid)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._hub.async_turn_off(self._device_uuid)
        self._attr_is_on = False
        self.async_write_ha_state()