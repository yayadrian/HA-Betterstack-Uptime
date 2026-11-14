"""Tests for Better Stack Uptime config flow."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.betterstack_uptime.config_flow import _token_unique_id
from custom_components.betterstack_uptime.const import (
    API_TOKEN_URL,
    CONF_API_TOKEN,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
)

from .conftest import MOCK_MONITORS, TEST_API_TOKEN, mock_api_page


def _mock_response(status: int = 200):
    """Create a mock aiohttp response."""
    resp = MagicMock()
    resp.status = status
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=status
        )
    return resp


def _patch_session(response):
    """Patch async_get_clientsession to return a mock session yielding response."""
    session = MagicMock()

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=response)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.get = MagicMock(return_value=ctx)

    return patch(
        "custom_components.betterstack_uptime.config_flow.async_get_clientsession",
        return_value=session,
    )


async def test_user_flow_success(hass: HomeAssistant) -> None:
    """Test successful config flow creates entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["description_placeholders"] == {"token_url": API_TOKEN_URL}

    with _patch_session(_mock_response(200)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: TEST_API_TOKEN, CONF_POLL_INTERVAL: 120},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Better Stack Uptime"
    assert result["data"] == {CONF_API_TOKEN: TEST_API_TOKEN}
    assert result["options"] == {CONF_POLL_INTERVAL: 120}


async def test_user_flow_default_poll_interval(hass: HomeAssistant) -> None:
    """Test config flow uses default poll interval when not specified."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with _patch_session(_mock_response(200)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: TEST_API_TOKEN},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL}


async def test_user_flow_invalid_auth_401(hass: HomeAssistant) -> None:
    """Test 401 shows invalid_auth error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    resp = _mock_response(401)
    # 401 is checked by status code, not raise_for_status
    resp.raise_for_status = MagicMock()

    with _patch_session(resp):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: TEST_API_TOKEN},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_invalid_auth_403(hass: HomeAssistant) -> None:
    """Test 403 shows invalid_auth error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    resp = _mock_response(403)
    resp.raise_for_status = MagicMock()

    with _patch_session(resp):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: TEST_API_TOKEN},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    """Test connection error shows cannot_connect."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    session = MagicMock()
    session.get = MagicMock(side_effect=aiohttp.ClientError("Connection refused"))

    with patch(
        "custom_components.betterstack_uptime.config_flow.async_get_clientsession",
        return_value=session,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: TEST_API_TOKEN},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_server_error(hass: HomeAssistant) -> None:
    """Test server error (e.g. 500) shows server_error, not cannot_connect."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with _patch_session(_mock_response(500)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: TEST_API_TOKEN},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "server_error"}


async def test_user_flow_unexpected_error(hass: HomeAssistant) -> None:
    """Test unexpected exception shows unknown error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.betterstack_uptime.config_flow.async_get_clientsession",
        side_effect=RuntimeError("boom"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: TEST_API_TOKEN},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_user_flow_duplicate_entry(hass: HomeAssistant) -> None:
    """Test duplicate token aborts with already_configured."""
    # Create first entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with _patch_session(_mock_response(200)):
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: TEST_API_TOKEN},
        )

    # Attempt second entry with same token
    result2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with _patch_session(_mock_response(200)):
        result2 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {CONF_API_TOKEN: TEST_API_TOKEN},
        )

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant, mock_config_entry) -> None:
    """Test options flow allows updating the poll interval."""
    page = mock_api_page(MOCK_MONITORS)

    resp = AsyncMock()
    resp.status = 200
    resp.raise_for_status = MagicMock()
    resp.json = AsyncMock(return_value=page)

    session = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.get = MagicMock(return_value=ctx)

    with patch(
        "custom_components.betterstack_uptime.coordinator.async_get_clientsession",
        return_value=session,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_POLL_INTERVAL: 300},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_POLL_INTERVAL: 300}
    assert mock_config_entry.options[CONF_POLL_INTERVAL] == 300
    assert mock_config_entry.runtime_data.update_interval == timedelta(seconds=300)


NEW_API_TOKEN = "new_api_token_0987654321"


async def test_reauth_flow_success(hass: HomeAssistant, mock_config_entry) -> None:
    """Test reauth replaces the token and unique ID on the existing entry."""
    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with (
        _patch_session(_mock_response(200)),
        patch(
            "custom_components.betterstack_uptime.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: NEW_API_TOKEN},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_API_TOKEN] == NEW_API_TOKEN
    assert (
        mock_config_entry.unique_id
        == _token_unique_id(NEW_API_TOKEN)
    )
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_reauth_flow_loaded_entry(
    hass: HomeAssistant, mock_config_entry, caplog: pytest.LogCaptureFixture
) -> None:
    """Test reauth of a loaded entry reloads it with the new token."""
    page = mock_api_page(MOCK_MONITORS)

    resp = AsyncMock()
    resp.status = 200
    resp.raise_for_status = MagicMock()
    resp.json = AsyncMock(return_value=page)

    session = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.get = MagicMock(return_value=ctx)

    with patch(
        "custom_components.betterstack_uptime.coordinator.async_get_clientsession",
        return_value=session,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        old_coordinator = mock_config_entry.runtime_data

        result = await mock_config_entry.start_reauth_flow(hass)
        with _patch_session(_mock_response(200)):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_API_TOKEN: NEW_API_TOKEN},
            )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data is not old_coordinator
    assert (
        session.get.call_args.kwargs["headers"]["Authorization"]
        == f"Bearer {NEW_API_TOKEN}"
    )
    assert "update listener" not in caplog.text


async def test_reauth_flow_invalid_auth(hass: HomeAssistant, mock_config_entry) -> None:
    """Test reauth shows an error for a rejected token and can recover."""
    result = await mock_config_entry.start_reauth_flow(hass)

    resp = _mock_response(401)
    resp.raise_for_status = MagicMock()
    with _patch_session(resp):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: NEW_API_TOKEN},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "invalid_auth"}
    assert mock_config_entry.data[CONF_API_TOKEN] == TEST_API_TOKEN

    with (
        _patch_session(_mock_response(200)),
        patch(
            "custom_components.betterstack_uptime.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: NEW_API_TOKEN},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


async def test_reauth_flow_token_used_by_other_entry(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test reauth aborts when the new token belongs to another entry."""
    other_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_TOKEN: NEW_API_TOKEN},
        unique_id=_token_unique_id(NEW_API_TOKEN),
    )
    other_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reauth_flow(hass)

    with _patch_session(_mock_response(200)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: NEW_API_TOKEN},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config_entry.data[CONF_API_TOKEN] == TEST_API_TOKEN
