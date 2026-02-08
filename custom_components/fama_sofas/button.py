"""Button platform for Fama Sofas integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FamaSofasConfigEntry
from .ble_client import FamaSofaClient
from .const import (
    CMD_BOTH_CLOSE,
    CMD_BOTH_OPEN,
    CMD_MOTOR1_CLOSE,
    CMD_MOTOR1_OPEN,
    CMD_MOTOR2_CLOSE,
    CMD_MOTOR2_OPEN,
    CMD_STOP,
    CONF_DURATION,
    DEFAULT_DURATION_SEC,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class FamaSofaButtonDescription(ButtonEntityDescription):
    """Describe a Fama Sofa button."""

    command: int
    is_stop: bool = False


BUTTON_DESCRIPTIONS: tuple[FamaSofaButtonDescription, ...] = (
    FamaSofaButtonDescription(
        key="motor1_open",
        translation_key="motor1_open",
        command=CMD_MOTOR1_OPEN,
    ),
    FamaSofaButtonDescription(
        key="motor1_close",
        translation_key="motor1_close",
        command=CMD_MOTOR1_CLOSE,
    ),
    FamaSofaButtonDescription(
        key="motor2_open",
        translation_key="motor2_open",
        command=CMD_MOTOR2_OPEN,
    ),
    FamaSofaButtonDescription(
        key="motor2_close",
        translation_key="motor2_close",
        command=CMD_MOTOR2_CLOSE,
    ),
    FamaSofaButtonDescription(
        key="both_open",
        translation_key="both_open",
        command=CMD_BOTH_OPEN,
    ),
    FamaSofaButtonDescription(
        key="both_close",
        translation_key="both_close",
        command=CMD_BOTH_CLOSE,
    ),
    FamaSofaButtonDescription(
        key="stop",
        translation_key="stop",
        command=CMD_STOP,
        is_stop=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FamaSofasConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fama Sofa buttons from a config entry."""
    client = entry.runtime_data
    address = entry.data[CONF_ADDRESS]
    name = entry.data.get(CONF_NAME, address)
    duration = entry.options.get(CONF_DURATION, DEFAULT_DURATION_SEC)

    async_add_entities(
        FamaSofaButton(
            client=client,
            address=address,
            device_name=name,
            description=desc,
            duration=duration,
        )
        for desc in BUTTON_DESCRIPTIONS
    )


class FamaSofaButton(ButtonEntity):
    """Representation of a Fama Sofa button."""

    entity_description: FamaSofaButtonDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        client: FamaSofaClient,
        address: str,
        device_name: str,
        description: FamaSofaButtonDescription,
        duration: int,
    ) -> None:
        """Initialize the button."""
        self._client = client
        self._duration = duration
        self.entity_description = description

        self._attr_unique_id = f"{address}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            name=device_name,
            manufacturer="Fama",
            model="Paradis",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        if self.entity_description.is_stop:
            await self._client.stop()
        else:
            await self._client.send_command(
                self.entity_description.command, self._duration
            )
