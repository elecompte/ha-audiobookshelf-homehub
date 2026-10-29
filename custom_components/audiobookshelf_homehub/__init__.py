"""Audiobookshelf Home Hub bridge integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from aiohttp import ClientError, ClientTimeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor","media_player"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    url = entry.data["url"].rstrip("/")
    session = async_get_clientsession(hass)

    async def fetch():
        try:
            async with session.get(
                f"{url}/api/current", timeout=ClientTimeout(total=12)
            ) as response:
                response.raise_for_status()
                payload = await response.json()
                if not isinstance(payload, dict) or "available" not in payload:
                    raise UpdateFailed("Unexpected bridge response")
                return payload
        except (ClientError, TimeoutError, ValueError) as exc:
            raise UpdateFailed(f"Bridge unavailable: {exc}") from exc

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_{entry.entry_id}",
        update_method=fetch,
        update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok
