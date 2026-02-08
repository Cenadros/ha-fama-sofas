"""Constants for the Fama Sofas integration."""

DOMAIN = "fama_sofas"

# BLE UUIDs
SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

# Command frame: [0x00, 0x00, CMD, 0x01, 0x01, 0x01, 0x00, 0x00]
COMMAND_FRAME = bytearray([0x00, 0x00, 0x00, 0x01, 0x01, 0x01, 0x00, 0x00])
COMMAND_BYTE_INDEX = 2

# Motor commands (byte 2)
CMD_MOTOR1_OPEN = 0x01
CMD_MOTOR1_CLOSE = 0x02
CMD_MOTOR2_OPEN = 0x03
CMD_MOTOR2_CLOSE = 0x04
CMD_BOTH_OPEN = 0x05
CMD_STOP = 0x07

# Timing
COMMAND_INTERVAL_SEC = 0.2  # 200ms between repeated commands
DEFAULT_DURATION_SEC = 60  # Default press duration in seconds

# Config
CONF_DURATION = "command_duration"
