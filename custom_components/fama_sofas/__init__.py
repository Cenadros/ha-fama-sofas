"""The Fama Sofas integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .ble_client import FamaSofaClient
from .const import DOMAIN, GRADUAL_COMMANDS, MAX_CONTINUOUS_DURATION_SEC

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BUTTON]

type FamaSofasConfigEntry = ConfigEntry[FamaSofaClient]

SERVICE_START = "start"
SERVICE_STOP = "stop"

SERVICE_START_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("command"): vol.In(list(GRADUAL_COMMANDS.keys())),
    }
)

SERVICE_STOP_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
    }
)


def _get_client_for_device(
    hass: HomeAssistant, device_id: str
) -> FamaSofaClient | None:
    """Find the FamaSofaClient for a given device ID."""
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get(device_id)
    if not device:
        return None
    for entry_id in device.config_entries:
        if entry_id in hass.data.get(DOMAIN, {}):
            return hass.data[DOMAIN][entry_id]
    return None


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Fama Sofas domain."""
    hass.data.setdefault(DOMAIN, {})

    async def handle_start(call: ServiceCall) -> None:
        """Handle the start service call for gradual motor control."""
        device_id = call.data["device_id"]
        command_name = call.data["command"]
        client = _get_client_for_device(hass, device_id)
        if not client:
            _LOGGER.error("Fama Sofa device %s not found", device_id)
            return
        cmd = GRADUAL_COMMANDS[command_name]
        await client.send_command(cmd, MAX_CONTINUOUS_DURATION_SEC)

    async def handle_stop(call: ServiceCall) -> None:
        """Handle the stop service call."""
        device_id = call.data["device_id"]
        client = _get_client_for_device(hass, device_id)
        if not client:
            _LOGGER.error("Fama Sofa device %s not found", device_id)
            return
        await client.stop()

    hass.services.async_register(
        DOMAIN, SERVICE_START, handle_start, schema=SERVICE_START_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP, handle_stop, schema=SERVICE_STOP_SCHEMA
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: FamaSofasConfigEntry) -> bool:
    """Set up Fama Sofas from a config entry."""
    address: str = entry.data[CONF_ADDRESS]
    client = FamaSofaClient(hass, address)
    entry.runtime_data = client
    hass.data[DOMAIN][entry.entry_id] = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FamaSofasConfigEntry) -> bool:
    """Unload a Fama Sofas config entry."""
    client: FamaSofaClient = entry.runtime_data
    await client.disconnect()
    hass.data[DOMAIN].pop(entry.entry_id, None)

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
