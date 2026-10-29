"""Serve and register the Audiobookshelf Home Hub card."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
CARD_URL = "/audiobookshelf_homehub/audiobookshelf-homehub-player.js"
CARD_PATH = Path(__file__).parent / "audiobookshelf-homehub-player.js"


async def register_frontend(hass: HomeAssistant, version: str) -> None:
    """Expose the card and register a versioned Lovelace resource in storage mode."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_PATH), False)]
    )
    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        _LOGGER.warning("Lovelace unavailable; card served but not registered")
        return
    if getattr(lovelace, "mode", None) != "storage":
        _LOGGER.warning("Lovelace resource mode is YAML; add %s as a module manually", CARD_URL)
        return
    resources = lovelace.resources
    # On startup Lovelace resources may not yet have been loaded.
    if not resources.loaded:
        await resources.async_load()
    desired = f"{CARD_URL}?v={version}"
    existing = [
        item for item in resources.async_items()
        if item.get("url", "").split("?", 1)[0] == CARD_URL
    ]
    if existing:
        if existing[0]["url"] != desired:
            await resources.async_update_item(
                existing[0]["id"], {"res_type": "module", "url": desired}
            )
    else:
        await resources.async_create_item({"res_type": "module", "url": desired})
    _LOGGER.info("Audiobookshelf Home Hub card resource registered: %s", desired)
