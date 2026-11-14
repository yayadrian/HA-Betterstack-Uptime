---
name: verify
description: Run this integration in a real Home Assistant against a fake Better Stack API and observe entities. Use to verify a change at runtime.
---

# Verify in a running Home Assistant

There is no real Better Stack token, so run a local fake API and point a *copy* of the integration at it.

## Setup (all under a scratch dir `$S`)

1. A venv with `pytest-homeassistant-custom-component` already has `homeassistant`. Home Assistant drops into recovery mode (custom integrations not loaded) without the frontend, so install it separately, pinned to `home-assistant-frontend` in `homeassistant/package_constraints.txt`:
   `python -m pip install --target $S/extra --no-deps home-assistant-frontend==<pin>`
2. Copy `custom_components/betterstack_uptime` to `$S/config/custom_components/` and change only `API_BASE_URL` to `http://127.0.0.1:18765/api/v2`.
3. Write `$S/config/configuration.yaml` with `homeassistant:`, `http: {server_host: 127.0.0.1, server_port: 18123}`, `api:`, `config:`, `onboarding:`, `diagnostics:`. Do not use `default_config:`.
4. Start the fake API with `python -I fake_betterstack.py 18765` (in this folder). The accepted token is `good-token`. Switch modes with `POST /admin {"heartbeats": "ok"|"403"|"500"|"gone"}`. Every heartbeats request is logged with its mode, so you can wait for polls with `grep -c 'mode 403'`.
5. Start Home Assistant with `PYTHONPATH=$S/extra hass -c $S/config --skip-pip`. Wait until `GET /api/onboarding` returns 200.
6. Get a token:
   - `POST /api/onboarding/users` with `client_id`, `name`, `username`, `password` and `language`.
   - Exchange the `auth_code` at `POST /auth/token` with `grant_type=authorization_code`.

## Drive

- **Add the integration:** `POST /api/config/config_entries/flow {"handler":"betterstack_uptime"}`, then post `{"api_token":"good-token","poll_interval":15}` to that flow.
- **Inspect:** `python -I snapshot.py <token-file>` prints each entity's unique ID, state, device class, device and attributes.
- **Diagnostics:** `GET /api/diagnostics/config_entry/<entry_id>`.
- **Restart:** `POST /api/services/homeassistant/stop`, then start Home Assistant again.

## Gotchas

- Errors at startup for `camera`, `conversation` or `ffmpeg` (missing modules) are harmless.
- Access tokens expire after 30 minutes. Get a new one through `/auth/token` with the refresh token, or onboard again in a fresh config.
- `pkill -f` patterns can match your own shell. Stop Home Assistant through its stop service instead.
