"""Read-only current audiobook sensor."""
from __future__ import annotations
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([CurrentAudiobook(hass.data[DOMAIN][entry.entry_id]["coordinator"], entry)])

class CurrentAudiobook(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Current audiobook"
    _attr_icon = "mdi:book-open-page-variant"
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_current_audiobook"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": "Audiobookshelf Home Hub", "manufacturer": "Community", "model": "Local bridge"}
    @property
    def native_value(self):
        data = self.coordinator.data or {}
        return data.get("title", "No book in progress") if data.get("available") else "No book in progress"
    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {k: data.get(k) for k in ("available", "author", "book_id", "position", "duration", "progress", "last_updated", "cover_url")}
