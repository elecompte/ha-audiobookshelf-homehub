"""Read-only Audiobookshelf current-book media player.

This entity deliberately exposes no playback controls: the current bridge's
browser-local playback session is not a server-owned HA playback session.
"""
from __future__ import annotations

from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerEntityFeature, MediaPlayerState, MediaType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([AudiobookMediaPlayer(hass.data[DOMAIN][entry.entry_id], entry)])


class AudiobookMediaPlayer(CoordinatorEntity, MediaPlayerEntity):
    _attr_has_entity_name = True
    _attr_name = "Audiobook"
    _attr_icon = "mdi:book-play"
    _attr_supported_features = MediaPlayerEntityFeature(0)

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_media_player"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Audiobookshelf Home Hub",
            "manufacturer": "Community",
            "model": "Local bridge",
        }

    @property
    def state(self):
        data = self.coordinator.data or {}
        # /api/current does not indicate whether a browser is playing audio.
        return MediaPlayerState.IDLE if data.get("available") else MediaPlayerState.OFF

    @property
    def media_title(self):
        data = self.coordinator.data or {}
        return data.get("title") if data.get("available") else None

    @property
    def media_artist(self):
        data = self.coordinator.data or {}
        return data.get("author") if data.get("available") else None

    @property
    def media_content_type(self):
        return MediaType.MUSIC

    @property
    def media_duration(self):
        data = self.coordinator.data or {}
        return data.get("duration") if data.get("available") else None

    @property
    def media_position(self):
        data = self.coordinator.data or {}
        return data.get("position") if data.get("available") else None

    @property
    def media_position_updated_at(self):
        # Position is a saved-book position, not an actively advancing clock.
        return None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {"book_id": data.get("book_id"), "progress": data.get("progress"), "playback_implemented": False}
