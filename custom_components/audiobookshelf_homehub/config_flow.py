"""Configuration UI for Audiobookshelf Home Hub."""
from __future__ import annotations

import voluptuous as vol
from aiohttp import ClientError, ClientTimeout
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_URL, DOMAIN


class AudiobookshelfHomeHubConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            url = user_input["url"].strip().rstrip("/")
            if not url.startswith(("http://", "https://")):
                errors["base"] = "invalid_url"
            else:
                await self.async_set_unique_id(url)
                self._abort_if_unique_id_configured()
                try:
                    session = async_get_clientsession(self.hass)
                    async with session.get(f"{url}/health", timeout=ClientTimeout(total=8)) as response:
                        response.raise_for_status()
                        payload = await response.json()
                        if not payload.get("ok"):
                            errors["base"] = "cannot_connect"
                except (ClientError, TimeoutError, ValueError):
                    errors["base"] = "cannot_connect"
                if not errors:
                    return self.async_create_entry(title="Audiobookshelf Home Hub", data={"url": url})
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("url", default=DEFAULT_URL): str}),
            errors=errors,
        )
