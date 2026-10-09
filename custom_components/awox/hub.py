"""Runtime hub for the AwoX integration.

Owns exactly ONE MQTTClient connection for the whole account, shared by
every light. Do not create a second MQTTClient per entity - AwoX/AWS IoT
will treat a second connection using the same identity as a duplicate
client and disconnect the first one.

State is currently optimistic: we don't yet have a defined format for
real device feedback (see parse/client.py note), so entities reflect the
last command sent rather than confirmed device state. When that format
is figured out, hook it in via add_listener()/the on_message callback
below instead of rebuilding this class.
"""
from __future__ import annotations

import json
import logging
from typing import Callable

from homeassistant.core import HomeAssistant

from awox.config import AppConfig
from awox.controls.light import Light
from awox.mqtt.client import MQTTClient, parse_light_state
from awox.provisioning.provisioner import Provisioner
from awox.state import AppState, Device, load_state

_LOGGER = logging.getLogger(__name__)

StateListener = Callable[[], None]

class AwoxHub:
    def __init__(self, hass: HomeAssistant, config: AppConfig) -> None:
        self.hass = hass
        self.config = config
        self.state: AppState | None = None
        self.mqtt_client: MQTTClient | None = None
        self.lights: dict[str, Light] = {}
        self._listeners: dict[str, list[StateListener]] = {}
        self.mqtt_client._client.on_message = self._on_message

    # ------------------------------------------------------------------
    # Setup / teardown
    # ------------------------------------------------------------------

    async def async_setup(self) -> None:
        """Provision certs, open the single MQTT connection, build Light objects."""
        self.state = await self.hass.async_add_executor_job(self._provision)

        connection_device = self._pick_connection_device(self.state)

        # MQTTClient.__init__ reads cert files from disk and builds the
        # paho client - keep it off the event loop.
        self.mqtt_client = await self.hass.async_add_executor_job(
            MQTTClient, self.config, connection_device
        )

        await self.hass.async_add_executor_job(self.mqtt_client.connect)
        await self.hass.async_add_executor_job(self.mqtt_client.wait_for_readiness)
        self.lights = {
            device_uuid: Light(
                mqtt=self.mqtt_client,
                device_id=device_uuid,
                device=device,
            )
            for device_uuid, device in self.state.devices.items()
        }

    async def async_shutdown(self) -> None:
        if self.mqtt_client is not None:
            await self.hass.async_add_executor_job(self.mqtt_client.close)

    def _provision(self) -> AppState:
        # Load whatever was persisted from a previous run first - if it's
        # already provisioned, Provisioner.provision() short-circuits and
        # returns it as-is instead of re-provisioning against AwoX's
        # servers on every HA restart.
        existing_state = load_state(self.config.storage.state_file)
        provisioner = Provisioner(self.config, existing_state)
        return provisioner.provision()

    def _pick_connection_device(self, state: AppState) -> Device:
        # ASSUMPTION: account_id / fingerprint / udn are identical across
        # every entry in state.devices, so any one of them can drive the
        # MQTT session identity. If provisioning actually gives you a
        # distinct hub/gateway identity separate from the bulbs, swap
        # this to return that instead.
        return next(iter(state.devices.values()))

    # ------------------------------------------------------------------
    # Commands - called by entities, run the blocking paho calls off-loop
    # ------------------------------------------------------------------

    async def async_turn_on(self, device_uuid: str) -> None:
        await self.hass.async_add_executor_job(self.lights[device_uuid].turn_on)

    async def async_turn_off(self, device_uuid: str) -> None:
        await self.hass.async_add_executor_job(self.lights[device_uuid].turn_off)

    async def async_set_brightness(self, device_uuid: str, level: int) -> None:
        await self.hass.async_add_executor_job(
            self.lights[device_uuid].set_brightness, level
        )

    async def async_set_color(self, device_uuid: str, r: int, g: int, b: int) -> None:
        await self.hass.async_add_executor_job(
            self.lights[device_uuid].set_color, r, g, b
        )

    async def async_set_temperature(self, device_uuid: str, level: int) -> None:
        await self.hass.async_add_executor_job(
            self.lights[device_uuid].set_temperature, level
        )
    # ------------------------------------------------------------------
    # Incoming state reports - paho thread parses, event loop notifies
    # ------------------------------------------------------------------

    def add_listener(self, device_id: str, listener: StateListener) -> Callable[[], None]:
        """Call listener() on the event loop whenever this light reports state."""
        self._listeners.setdefault(device_id, []).append(listener)

        def remove() -> None:
            self._listeners[device_id].remove(listener)

        return remove

    def _on_message(self, client, userdata, msg) -> None:
        """paho thread: update the matching light's state, then notify its entity."""
        try:
            data = json.loads(msg.payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            _LOGGER.debug("Unparsable payload on %s, ignoring", msg.topic)
            return

        if data.get("rt") != "oic.d.light":
            return  # not a light state report

        device_id = data.get("di")
        device = self.state.devices.get(device_id) if self.state else None
        if device is None or device.state is None:
            _LOGGER.debug("State for unknown device %s, ignoring", device_id)
            return

        parse_light_state(msg.payload, device.state)
        self.hass.loop.call_soon_threadsafe(self._dispatch, device_id)

    def _dispatch(self, device_id: str) -> None:
        """Event loop: notify entities of a device's new state."""
        for listener in list(self._listeners.get(device_id, [])):
            listener()
