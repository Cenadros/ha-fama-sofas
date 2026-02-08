"""The Fama Sofas integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant

from .ble_client import FamaSofaClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BUTTON]

type FamaSofasConfigEntry = ConfigEntry[FamaSofaClient]


async def async_setup_entry(hass: HomeAssistant, entry: FamaSofasConfigEntry) -> bool:
    """Set up Fama Sofas from a config entry."""
    address: str = entry.data[CONF_ADDRESS]
    client = FamaSofaClient(hass, address)
    entry.runtime_data = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FamaSofasConfigEntry) -> bool:
    """Unload a Fama Sofas config entry."""
    client: FamaSofaClient = entry.runtime_data
    await client.disconnect()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
