"""Read-only media representation of the current Audiobookshelf book.

The browser is the actual audio renderer. Do not claim playback or expose
transport commands until a session-aware browser-to-HA channel is implemented.
"""
from __future__ import annotations

from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerState, MediaType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([AudiobookshelfBook(hass.data[DOMAIN][entry.entry_id]["coordinator"], entry)])


class AudiobookshelfBook(CoordinatorEntity, MediaPlayerEntity):
    """Expose audiobook metadata without misrepresenting browser playback state."""

    _attr_has_entity_name = True
    _attr_name = "Audiobook"
    _attr_icon = "mdi:book-play"
    _attr_supported_features = 0

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_audiobook_player"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Audiobookshelf Home Hub",
            "manufacturer": "Community",
            "model": "Local bridge",
        }

    @property
    def state(self) -> MediaPlayerState:
        # There is no playback telemetry from the standalone browser player.
        # IDLE is a deliberate, truthful state, not a claim of pause/play.
        return MediaPlayerState.IDLE if (self.coordinator.data or {}).get("available") else MediaPlayerState.OFF

    @property
    def media_content_type(self) -> MediaType | None:
        return MediaType.MUSIC if (self.coordinator.data or {}).get("available") else None

    @property
    def media_content_id(self) -> str | None:
        return (self.coordinator.data or {}).get("book_id")

    @property
    def media_title(self) -> str | None:
        return (self.coordinator.data or {}).get("title")

    @property
    def media_artist(self) -> str | None:
        return (self.coordinator.data or {}).get("author")

    @property
    def media_duration(self) -> int | None:
        duration = (self.coordinator.data or {}).get("duration")
        return round(float(duration)) if duration is not None else None

    @property
    def media_position(self) -> float | None:
        position = (self.coordinator.data or {}).get("position")
        return float(position) if position is not None else None

    @property
    def media_position_updated_at(self):
        # A saved position is not a continuously advancing playback position.
        return None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        return {
            "progress_percent": data.get("progress"),
            "book_id": data.get("book_id"),
            "last_updated": data.get("last_updated"),
            "playback_control_available": False,
        }
