"""BLE client for communicating with Fama Sofas."""

from __future__ import annotations

import asyncio
import logging

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.exc import BleakError
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.core import HomeAssistant

from .const import (
    CHARACTERISTIC_UUID,
    COMMAND_BYTE_INDEX,
    COMMAND_FRAME,
    COMMAND_INTERVAL_SEC,
    CMD_STOP,
    MOTOR1_COMMANDS,
    MOTOR2_COMMANDS,
    SERVICE_UUID,
)

_LOGGER = logging.getLogger(__name__)

CONNECT_TIMEOUT = 15.0
MAX_CONNECT_RETRIES = 3


def _build_command(cmd: int) -> bytearray:
    """Build an 8-byte command frame with the given command byte."""
    frame = bytearray(COMMAND_FRAME)
    frame[COMMAND_BYTE_INDEX] = cmd
    return frame


def _command_channel(cmd: int) -> str:
    """Return the channel name for a motor command."""
    if cmd in MOTOR1_COMMANDS:
        return "motor1"
    if cmd in MOTOR2_COMMANDS:
        return "motor2"
    return "both"


def _conflicting_channels(cmd: int) -> set[str]:
    """Return the set of channels that must be cancelled before starting *cmd*.

    - An individual motor command conflicts with its own channel and "both".
    - A both-motors command conflicts with all channels.
    """
    if cmd in MOTOR1_COMMANDS:
        return {"motor1", "both"}
    if cmd in MOTOR2_COMMANDS:
        return {"motor2", "both"}
    # CMD_BOTH_OPEN / CMD_BOTH_CLOSE → cancel everything
    return {"motor1", "motor2", "both"}


class FamaSofaClient:
    """BLE client that manages connection and command sending for a Fama sofa."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        """Initialize the client."""
        self._hass = hass
        self._address = address
        self._client: BleakClient | None = None
        self._target_char: BleakGATTCharacteristic | None = None
        self._command_tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    @property
    def address(self) -> str:
        """Return the BLE address."""
        return self._address

    @property
    def is_running(self) -> bool:
        """Return True if any command loop is currently running."""
        return any(
            not task.done() for task in self._command_tasks.values()
        )

    async def _ensure_connected(self) -> BleakClient:
        """Ensure we have an active BLE connection with retry logic."""
        if self._client and self._client.is_connected:
            return self._client

        # Clean up any stale client
        self._client = None
        self._target_char = None

        last_error: Exception | None = None
        for attempt in range(1, MAX_CONNECT_RETRIES + 1):
            try:
                _LOGGER.debug(
                    "Connection attempt %d/%d to %s",
                    attempt,
                    MAX_CONNECT_RETRIES,
                    self._address,
                )

                ble_device = async_ble_device_from_address(
                    self._hass, self._address, connectable=True
                )
                if not ble_device:
                    raise BleakError(
                        f"Device {self._address} not found by HA Bluetooth scanner"
                    )

                client = BleakClient(
                    ble_device,
                    timeout=CONNECT_TIMEOUT,
                    disconnected_callback=self._on_disconnect,
                )
                await client.connect()
                self._client = client

                # Resolve the correct FFE1 characteristic on service FFE0.
                # The device advertises duplicate FFE0 services, so we need
                # to find the characteristic explicitly.
                self._target_char = self._find_characteristic(client)

                _LOGGER.info(
                    "Connected to %s (char handle=%s)",
                    self._address,
                    self._target_char.handle if self._target_char else "UUID-fallback",
                )
                return client

            except (BleakError, TimeoutError, OSError) as err:
                last_error = err
                _LOGGER.warning(
                    "Connection attempt %d failed for %s: %s",
                    attempt,
                    self._address,
                    err,
                )
                if attempt < MAX_CONNECT_RETRIES:
                    await asyncio.sleep(1.0 * attempt)

        raise BleakError(
            f"Failed to connect to {self._address} after {MAX_CONNECT_RETRIES} attempts: {last_error}"
        )

    def _find_characteristic(
        self, client: BleakClient
    ) -> BleakGATTCharacteristic | None:
        """Find the FFE1 characteristic on the FFE0 service.

        Handles devices with duplicate FFE0 services by returning the first
        FFE1 characteristic that supports write.
        """
        for service in client.services:
            if service.uuid == SERVICE_UUID:
                for char in service.characteristics:
                    if char.uuid == CHARACTERISTIC_UUID and (
                        "write" in char.properties
                        or "write-without-response" in char.properties
                    ):
                        _LOGGER.debug(
                            "Found characteristic %s handle=%d on service %s",
                            char.uuid,
                            char.handle,
                            service.uuid,
                        )
                        return char
        _LOGGER.warning(
            "Could not find FFE1 characteristic on FFE0 service for %s, "
            "will fall back to UUID-based write",
            self._address,
        )
        return None

    def _on_disconnect(self, client: BleakClient) -> None:
        """Handle BLE disconnection."""
        _LOGGER.warning("Disconnected from %s", self._address)
        self._client = None
        self._target_char = None

    async def _send_single_command(self, cmd: int) -> None:
        """Send a single command frame."""
        client = await self._ensure_connected()
        frame = _build_command(cmd)

        if self._target_char:
            # Write to the specific characteristic handle (avoids duplicate UUID issues)
            await client.write_gatt_char(self._target_char, frame, response=True)
        else:
            # Fallback to UUID-based write
            await client.write_gatt_char(CHARACTERISTIC_UUID, frame, response=True)

        _LOGGER.debug("Sent command 0x%02X to %s", cmd, self._address)

    async def _command_loop(self, cmd: int, duration: float, channel: str) -> None:
        """Send a command repeatedly for the given duration (dead man's switch)."""
        _LOGGER.info(
            "Starting command loop: cmd=0x%02X duration=%ss channel=%s for %s",
            cmd,
            duration,
            channel,
            self._address,
        )
        cancelled = False
        try:
            end_time = asyncio.get_event_loop().time() + duration
            count = 0
            while asyncio.get_event_loop().time() < end_time:
                await self._send_single_command(cmd)
                count += 1
                await asyncio.sleep(COMMAND_INTERVAL_SEC)
            _LOGGER.info(
                "Command loop finished naturally after %d sends for %s",
                count,
                self._address,
            )
        except asyncio.CancelledError:
            cancelled = True
            _LOGGER.debug("Command loop cancelled for %s", self._address)
        except Exception as err:
            _LOGGER.error(
                "Error during command loop for %s: %s (%s)",
                self._address,
                err,
                type(err).__name__,
            )
        finally:
            # Remove ourselves from the task dict
            self._command_tasks.pop(channel, None)

            # Send a STOP only when the loop ended on its own (natural
            # completion or error) and no other motors are still running.
            # When the loop was *cancelled* the caller takes care of what
            # comes next (either an explicit stop() or a replacement command),
            # so we must not inject a STOP that would kill other motors.
            if not cancelled:
                has_others = any(
                    not t.done() for t in self._command_tasks.values()
                )
                if not has_others:
                    try:
                        await self._send_single_command(CMD_STOP)
                        _LOGGER.debug(
                            "Stop command sent after loop for %s", self._address
                        )
                    except Exception:
                        _LOGGER.warning(
                            "Failed to send stop command to %s",
                            self._address,
                            exc_info=True,
                        )

    async def send_command(self, cmd: int, duration: float) -> None:
        """Start sending a command for the specified duration.

        Only cancels command tasks on conflicting channels, allowing
        independent motors to run concurrently.
        """
        async with self._lock:
            channel = _command_channel(cmd)
            for ch in _conflicting_channels(cmd):
                await self._cancel_channel(ch)
            self._command_tasks[channel] = asyncio.create_task(
                self._command_loop(cmd, duration, channel)
            )

    async def stop(self) -> None:
        """Stop any running command and send the stop command."""
        async with self._lock:
            await self._cancel_all_channels()
            try:
                await self._send_single_command(CMD_STOP)
                _LOGGER.info("Stop command sent to %s", self._address)
            except Exception as err:
                _LOGGER.error(
                    "Failed to send stop to %s: %s (%s)",
                    self._address,
                    err,
                    type(err).__name__,
                )

    async def _cancel_channel(self, channel: str) -> None:
        """Cancel the command task for the given channel if running."""
        task = self._command_tasks.get(channel)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._command_tasks.pop(channel, None)

    async def _cancel_all_channels(self) -> None:
        """Cancel command tasks on all channels."""
        for channel in list(self._command_tasks):
            await self._cancel_channel(channel)

    async def disconnect(self) -> None:
        """Disconnect from the BLE device."""
        await self._cancel_all_channels()
        if self._client and self._client.is_connected:
            await self._client.disconnect()
            _LOGGER.debug("Disconnected from %s", self._address)
        self._client = None
        self._target_char = None
