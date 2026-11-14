# Better Stack Uptime for Home Assistant

[![](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/yayadrian)
[![](https://img.shields.io/static/v1?label=Support&message=Ko-fi&logo=kofi&color=%23FF6433&logoColor=white)](https://ko-fi.com/yayadrian)

A custom [Home Assistant](https://www.home-assistant.io/) integration that monitors your [Better Stack Uptime](https://betterstack.com/uptime) monitors. Each monitor gets a device with two entities — a binary sensor indicating whether the monitor is up, and a sensor showing the raw status string.

> [!WARNING]
> This is an unofficial community integration. It is not created by, affiliated with, endorsed by, or supported by Better Stack.

## Features

- **Binary sensor** (`connectivity`) — `on` when the monitor status is `up` or `validating`, `off` otherwise.
- **Status sensor** (`enum`) — exposes the raw status string (e.g. `up`, `down`, `pending`, `paused`, `maintenance`, `validating`).
- **Extra attributes** on both entities: `monitor_type`, `url`, `pronounceable_name`, `last_checked_at`.
- Automatic discovery of new monitors on each poll cycle.
- Automatic cleanup of entities for monitors removed from Better Stack.
- Configurable poll interval (15 – 3600 seconds, default 60).
- Full pagination support for accounts with many monitors.
- Prompts for a new API token if Better Stack rejects the current one.
- Diagnostics download with the API token redacted.

## Requirements

- Home Assistant **2026.3.0** or newer.
- A Better Stack API token — generate one at <https://betterstack.com/settings/global-api-tokens> then click `Team-based tokens`

## Installation

### Marketplace (recommended)

[![Open your Home Assistant instance and open this repository in the Marketplace.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=yayadrian&repository=HA-Betterstack-Uptime&category=integration)

On Home Assistant 2026.11 or newer, select the button above, or:

1. Go to **Settings > Marketplace**.
2. In the upper-right corner, select **Add from link**.
3. Under **GitHub link**, enter `yayadrian/HA-Betterstack-Uptime` and select **Add**. If asked for a **Type**, choose **Integration**.
4. Open **Better Stack Uptime** and install it.
5. Restart Home Assistant.

The Marketplace asks you to connect GitHub the first time you add a repository from a link.

### HACS (Home Assistant 2026.10 or older)

1. Open **HACS** and select the three-dot menu in the top-right corner.
2. Select **Custom repositories**, add `https://github.com/yayadrian/HA-Betterstack-Uptime` with type **Integration**, and select **Add**.
3. Search for **Better Stack Uptime** and download it.
4. Restart Home Assistant.

### Manual

1. Copy the `custom_components/betterstack_uptime` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings > Devices & Services > Add Integration**.
2. Search for **Better Stack Uptime**.
3. Enter your API token and (optionally) a custom poll interval in seconds.

If the token is later revoked or expires, Home Assistant shows a **Reauthenticate** prompt for the integration where you can enter a new one. The poll interval can be changed at any time from the integration's **Configure** option.

## Entities

For each monitor returned by the Better Stack API, a device is created with:

| Entity | Type | Description |
| --- | --- | --- |
| **Up** | Binary sensor | `on` if the monitor status is `up` or `validating` |
| **Status** | Enum sensor | `up`, `down`, `pending`, `paused`, `maintenance` or `validating`; any other value from Better Stack is shown as unknown |

## License

[MIT](LICENSE)
