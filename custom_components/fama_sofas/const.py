"""Constants for the Fama Sofas integration."""

DOMAIN = "fama_sofas"

# BLE UUIDs
SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

# Command frame: [0x00, 0x00, CMD, 0x01, 0x01, 0x01, 0x00, 0x00]
COMMAND_FRAME = bytearray([0x00, 0x00, 0x00, 0x01, 0x01, 0x01, 0x00, 0x00])
COMMAND_BYTE_INDEX = 2

# Motor commands (byte 2)
CMD_MOTOR1_OPEN = 0x03
CMD_MOTOR1_CLOSE = 0x04
CMD_MOTOR2_OPEN = 0x01
CMD_MOTOR2_CLOSE = 0x02
CMD_BOTH_OPEN = 0x05
CMD_BOTH_CLOSE = 0x06
CMD_STOP = 0x07

# Timing
COMMAND_INTERVAL_SEC = 0.2  # 200ms between repeated commands
DEFAULT_DURATION_SEC = 60  # Default press duration in seconds
MAX_CONTINUOUS_DURATION_SEC = 120  # Safety timeout for gradual control

# Config
CONF_DURATION = "command_duration"

# Motor command groups (for channel resolution)
MOTOR1_COMMANDS = frozenset({CMD_MOTOR1_OPEN, CMD_MOTOR1_CLOSE})
MOTOR2_COMMANDS = frozenset({CMD_MOTOR2_OPEN, CMD_MOTOR2_CLOSE})
BOTH_MOTOR_COMMANDS = frozenset({CMD_BOTH_OPEN, CMD_BOTH_CLOSE})

# Gradual control: command name -> command byte mapping
GRADUAL_COMMANDS: dict[str, int] = {
    "motor1_open": CMD_MOTOR1_OPEN,
    "motor1_close": CMD_MOTOR1_CLOSE,
    "motor2_open": CMD_MOTOR2_OPEN,
    "motor2_close": CMD_MOTOR2_CLOSE,
    "both_open": CMD_BOTH_OPEN,
    "both_close": CMD_BOTH_CLOSE,
}
