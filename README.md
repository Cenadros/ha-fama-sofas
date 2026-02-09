# Fama Sofas - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Home Assistant custom integration to control [Fama](https://www.famasofas.com/) motorized sofas via Bluetooth Low Energy (BLE).

## Features

- Automatic discovery of Fama sofas via Bluetooth
- Control seat motors (open/close) with button entities
- Dead man's switch pattern with configurable duration
- Stop button for immediate halt
- Support for multiple sofas

## Supported Models

- Fama Paradis (tested)
- Other Fama models with BLE module (should work -- device name must start with "Sofa")

## Requirements

- Home Assistant 2024.1.0 or newer
- Bluetooth adapter accessible by Home Assistant
- Fama sofa with BLE module (HM-10 compatible)

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click the three dots in the top right corner and select **Custom repositories**
3. Add `https://github.com/Cenadros/ha-fama-sofas` with category **Integration**
4. Click **Install**
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/fama_sofas` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

### Automatic Discovery

If your Home Assistant has a Bluetooth adapter, the sofa will be discovered automatically. You will see a notification to set it up.

### Manual Setup

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for **Fama Sofas**
3. Select your sofa from the list of discovered devices
4. Set the command duration (how long the motor runs per button press)

## Entities

Each configured sofa creates the following button entities:

| Entity | Description |
|--------|-------------|
| **Motor 1 open** | Extends motor 1 |
| **Motor 1 close** | Retracts motor 1 |
| **Motor 2 open** | Extends motor 2 |
| **Motor 2 close** | Retracts motor 2 |
| **Both motors open** | Extends both motors simultaneously |
| **Stop** | Immediately stops all movement |

> **Note:** The motor mapping depends on your sofa configuration. Test each button to identify which motor controls which function (e.g., footrest, backrest).

## Usage Tips

### Move Multiple Sofas at Once

If you have multiple sofa modules, create an HA script or automation that presses the buttons on all devices simultaneously:

```yaml
script:
  open_all_sofas:
    alias: "Open all sofas"
    sequence:
      - parallel:
          - action: button.press
            target:
              entity_id: button.sofa_salon_d_d_motor1_open
          - action: button.press
            target:
              entity_id: button.sofa_salon_d_d_2_motor1_open
```

### Stop All Sofas

```yaml
script:
  stop_all_sofas:
    alias: "Stop all sofas"
    sequence:
      - parallel:
          - action: button.press
            target:
              entity_id: button.sofa_salon_d_d_stop
          - action: button.press
            target:
              entity_id: button.sofa_salon_d_d_2_stop
```

## BLE Protocol

The sofa uses an HM-10 compatible BLE module with the following characteristics:

- **Service UUID:** `FFE0`
- **Characteristic UUID:** `FFE1` (Read, Write, Write Without Response, Notify)
- **Command frame:** 8 bytes `[0x00, 0x00, CMD, 0x01, 0x01, 0x01, 0x00, 0x00]`
- **Dead man's switch:** Commands repeat every 200ms while active; motor stops when commands stop

### Command Bytes

| Byte | Binary | Action |
|------|--------|--------|
| `0x01` | `001` | Motor 2 direction A (open) |
| `0x02` | `010` | Motor 2 direction B (close) |
| `0x03` | `011` | Motor 1 direction A (open) |
| `0x04` | `100` | Motor 1 direction B (close) |
| `0x05` | `101` | Both motors (open) |
| `0x07` | `111` | Stop / idle |

## License

MIT License - see [LICENSE](LICENSE) for details.
