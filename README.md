# Better Stack Uptime for Home Assistant

A custom [Home Assistant](https://www.home-assistant.io/) integration that monitors your [Better Stack Uptime](https://betterstack.com/uptime) monitors. Each monitor gets a device with two entities — a binary sensor indicating whether the monitor is up, and a sensor showing the raw status string.

## Features

- **Binary sensor** (`connectivity`) — `on` when the monitor status is `up` or `validating`, `off` otherwise.
- **Status sensor** (`enum`) — exposes the raw status string (e.g. `up`, `down`, `pending`, `paused`, `maintenance`, `validating`).
- **Extra attributes** on both entities: `monitor_type`, `url`, `pronounceable_name`, `last_checked_at`.
- Automatic discovery of new monitors on each poll cycle.
- Automatic cleanup of entities for monitors removed from Better Stack.
- Configurable poll interval (15 – 3600 seconds, default 60).
- Full pagination support for accounts with many monitors.

## Requirements

- Home Assistant **2026.2.0** or newer.
- A Better Stack API token — generate one at <https://betterstack.com/settings/global-api-tokens>.

## Installation

### HACS (recommended)

1. Open **HACS** in Home Assistant.
2. Go to **Integrations** and click the three-dot menu.
3. Select **Custom repositories** and add this repository URL with category **Integration**.
4. Search for **Better Stack Uptime** and install it.
5. Restart Home Assistant.

### Manual

1. Copy the `custom_components/betterstack_uptime` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings > Devices & Services > Add Integration**.
2. Search for **Better Stack Uptime**.
3. Enter your API token and (optionally) a custom poll interval in seconds.

## Entities

For each monitor returned by the Better Stack API, a device is created with:

| Entity | Type | Description |
| --- | --- | --- |
| **Up** | Binary sensor | `on` if the monitor status is `up` or `validating` |
| **Status** | Enum sensor | Raw status string from Better Stack |

## License

[MIT](LICENSE)
