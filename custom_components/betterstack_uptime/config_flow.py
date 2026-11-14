"""Config flow for Better Stack Uptime."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_TOKEN,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MAX_POLL_INTERVAL,
    MIN_POLL_INTERVAL,
    API_BASE_URL,
    API_TOKEN_URL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_TOKEN): str,
        vol.Optional(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_POLL_INTERVAL, max=MAX_POLL_INTERVAL)
        ),
    }
)

STEP_REAUTH_DATA_SCHEMA = vol.Schema({vol.Required(CONF_API_TOKEN): str})


def _token_unique_id(token: str) -> str:
    """Return the config entry unique ID for a token.

    A hash of the token is used to avoid exposing the token itself.
    """
    return hashlib.sha256(token.encode()).hexdigest()[:16]


class BetterStackUptimeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Better Stack Uptime."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> BetterStackUptimeOptionsFlow:
        """Return the options flow handler."""
        return BetterStackUptimeOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_API_TOKEN]
            errors = await self._async_validate_token(token)

            if not errors:
                await self.async_set_unique_id(_token_unique_id(token))
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title="Better Stack Uptime",
                    data={CONF_API_TOKEN: token},
                    options={CONF_POLL_INTERVAL: user_input.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={"token_url": API_TOKEN_URL},
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a rejected API token."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new API token and update the existing entry."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            token = user_input[CONF_API_TOKEN]
            errors = await self._async_validate_token(token)

            if not errors:
                # The unique ID is derived from the token, so a new token means a
                # new unique ID. Update the entry being reauthenticated rather than
                # matching on unique ID, but never take over another entry's ID.
                unique_id = _token_unique_id(token)
                existing = self.hass.config_entries.async_entry_for_domain_unique_id(
                    DOMAIN, unique_id
                )
                if existing is not None and existing.entry_id != reauth_entry.entry_id:
                    return self.async_abort(reason="already_configured")

                return self.async_update_reload_and_abort(
                    reauth_entry,
                    unique_id=unique_id,
                    data_updates={CONF_API_TOKEN: token},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "name": reauth_entry.title,
                "token_url": API_TOKEN_URL,
            },
        )

    async def _async_validate_token(self, token: str) -> dict[str, str]:
        """Check a token against the Better Stack API and return any form errors."""
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(
                f"{API_BASE_URL}/monitors",
                headers={"Authorization": f"Bearer {token}"},
            ) as resp:
                if resp.status in (401, 403):
                    return {"base": "invalid_auth"}
                if not (200 <= resp.status < 300):
                    return {"base": "server_error"}
        except aiohttp.ClientError:
            return {"base": "cannot_connect"}
        except Exception:
            _LOGGER.exception("Unexpected error validating API token")
            return {"base": "unknown"}
        return {}


class BetterStackUptimeOptionsFlow(OptionsFlowWithReload):
    """Handle options for Better Stack Uptime.

    Changing the poll interval reloads the entry, which rebuilds the coordinator.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_POLL_INTERVAL, default=current_interval): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_POLL_INTERVAL, max=MAX_POLL_INTERVAL),
                    ),
                }
            ),
        )
