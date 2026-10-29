# Audiobookshelf Home Hub

HACS-installable Home Assistant custom integration for a **private local** Audiobookshelf bridge.

## Status: v0.1.0 foundation

- Configuration via Settings → Devices & services → Add integration → Audiobookshelf Home Hub.
- Tests the bridge `/health` endpoint.
- Polls `/api/current` every 15 seconds and exposes a current-audiobook sensor.
- Keeps bridge calls server-side; no bridge URL is placed in dashboard cards.

**Not yet implemented:** audio streaming, authenticated media proxy, playback sessions, media_player entity, and native player card. Do not remove the existing standalone bridge or the current working dashboard until these are implemented.

## Install via HACS

1. Push this repository to GitHub.
2. In HACS, add a **Custom repository** with type **Integration** and the GitHub repository URL.
3. Download Audiobookshelf Home Hub from HACS and restart Home Assistant.
4. Add the integration in Devices & services, setting the bridge URL to `http://10.0.0.10:18765`.

The bridge must be reachable **from the Home Assistant container**, not necessarily from the browser.

## Development / releases

Source of truth: `/dockervol/2-Repos/ha-audiobookshelf-homehub` on docker1. Push commits and version tags from this working tree. Update `manifest.json` version and tag releases for HACS updates.

## Security plan for playback

The next milestone must use Home Assistant authentication for commands and signed, short-lived stream URLs for browser audio. HA fetches the audio from the local bridge. Streaming must support HTTP Range and cancellation, and must not expose Audiobookshelf credentials or a public unauthenticated bridge. Do not proxy the current unauthenticated bridge directly to the internet.
