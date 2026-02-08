"""BLE client for communicating with Fama Sofas."""

from __future__ import annotations

import asyncio
import logging

from bleak import BleakClient
from bleak.exc import BleakError
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.core import HomeAssistant

from .const import (
    CHARACTERISTIC_UUID,
    COMMAND_BYTE_INDEX,
    COMMAND_FRAME,
    COMMAND_INTERVAL_SEC,
    CMD_STOP,
)

_LOGGER = logging.getLogger(__name__)


def _build_command(cmd: int) -> bytearray:
    """Build an 8-byte command frame with the given command byte."""
    frame = bytearray(COMMAND_FRAME)
    frame[COMMAND_BYTE_INDEX] = cmd
    return frame


class FamaSofaClient:
    """BLE client that manages connection and command sending for a Fama sofa."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        """Initialize the client."""
        self._hass = hass
        self._address = address
        self._client: BleakClient | None = None
        self._command_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    @property
    def address(self) -> str:
        """Return the BLE address."""
        return self._address

    @property
    def is_running(self) -> bool:
        """Return True if a command loop is currently running."""
        return self._command_task is not None and not self._command_task.done()

    async def _ensure_connected(self) -> BleakClient:
        """Ensure we have an active BLE connection."""
        if self._client and self._client.is_connected:
            return self._client

        ble_device = async_ble_device_from_address(self._hass, self._address, True)
        if not ble_device:
            raise BleakError(f"Could not find BLE device {self._address}")

        self._client = BleakClient(ble_device)
        await self._client.connect()
        _LOGGER.debug("Connected to %s", self._address)
        return self._client

    async def _send_single_command(self, cmd: int) -> None:
        """Send a single command frame."""
        client = await self._ensure_connected()
        frame = _build_command(cmd)
        await client.write_gatt_char(CHARACTERISTIC_UUID, frame, response=False)

    async def _command_loop(self, cmd: int, duration: float) -> None:
        """Send a command repeatedly for the given duration (dead man's switch)."""
        try:
            end_time = asyncio.get_event_loop().time() + duration
            while asyncio.get_event_loop().time() < end_time:
                await self._send_single_command(cmd)
                await asyncio.sleep(COMMAND_INTERVAL_SEC)
        except asyncio.CancelledError:
            _LOGGER.debug("Command loop cancelled for %s", self._address)
        except BleakError as err:
            _LOGGER.error("BLE error during command loop for %s: %s", self._address, err)
        finally:
            try:
                await self._send_single_command(CMD_STOP)
            except BleakError:
                _LOGGER.warning("Failed to send stop command to %s", self._address)

    async def send_command(self, cmd: int, duration: float) -> None:
        """Start sending a command for the specified duration.

        Cancels any previously running command first.
        """
        async with self._lock:
            await self._cancel_command_task()
            self._command_task = asyncio.create_task(
                self._command_loop(cmd, duration)
            )

    async def stop(self) -> None:
        """Stop any running command and send the stop command."""
        async with self._lock:
            await self._cancel_command_task()
            try:
                await self._send_single_command(CMD_STOP)
            except BleakError as err:
                _LOGGER.error("Failed to send stop to %s: %s", self._address, err)

    async def _cancel_command_task(self) -> None:
        """Cancel the current command task if running."""
        if self._command_task and not self._command_task.done():
            self._command_task.cancel()
            try:
                await self._command_task
            except asyncio.CancelledError:
                pass
            self._command_task = None

    async def disconnect(self) -> None:
        """Disconnect from the BLE device."""
        await self._cancel_command_task()
        if self._client and self._client.is_connected:
            await self._client.disconnect()
            _LOGGER.debug("Disconnected from %s", self._address)
        self._client = None
