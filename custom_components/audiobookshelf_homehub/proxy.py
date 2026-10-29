"""Authenticated HA API and signed audio streaming for Audiobookshelf Home Hub.

The bridge remains private. HA issues short-lived signed URLs to the browser.
"""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import re
from urllib.parse import quote

from aiohttp import ClientError, ClientTimeout, web
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.http.auth import async_sign_path
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PREFIX = "/api/audiobookshelf_homehub"


def _entry(hass, entry_id):
    state = hass.data.get(DOMAIN, {}).get(entry_id)
    if not state:
        raise web.HTTPNotFound()
    return state


def _signed(hass, path):
    # Home Assistant's signed-path authentication works for media elements,
    # which cannot attach Authorization headers to their HTTP Range requests.
    return async_sign_path(hass, path, timedelta(seconds=600))


class PlayerApiView(HomeAssistantView):
    url = PREFIX + "/{entry_id}/{action}"
    name = "api:audiobookshelf_homehub:player"
    requires_auth = True

    async def get(self, request, entry_id, action):
        if action != "current":
            raise web.HTTPNotFound()
        state = _entry(request.app["hass"], entry_id)
        data = dict(state["coordinator"].data or {})
        book_id = data.get("book_id")
        if book_id and isinstance(book_id, str) and all(c.isalnum() or c in "-_" for c in book_id):
            data["cover_url"] = _signed(request.app["hass"], f"{PREFIX}/{entry_id}/cover/{book_id}")
        return web.json_response(data, headers={"Cache-Control": "no-store"})

    async def post(self, request, entry_id, action):
        if action not in ("start", "sync", "close", "refresh"):
            raise web.HTTPNotFound()
        hass = request.app["hass"]
        state = _entry(hass, entry_id)
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("Expected JSON object")
        except (ValueError, UnicodeDecodeError):
            raise web.HTTPBadRequest(text="Invalid JSON")
        if request.content_length and request.content_length > 8192:
            raise web.HTTPRequestEntityTooLarge(max_size=8192, actual_size=request.content_length)
        if action == "refresh":
            handle = body.get("handle")
            if not isinstance(handle, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", handle):
                raise web.HTTPBadRequest(text="Invalid handle")
            if handle not in state.setdefault("audio_handles", set()):
                raise web.HTTPForbidden(text="Unknown audio handle")
            return web.json_response({"url": _signed(hass, f"{PREFIX}/{entry_id}/audio/{handle}")}, headers={"Cache-Control": "no-store"})
        session = async_get_clientsession(hass)
        path = "/api/player/" + action
        try:
            async with session.post(state["url"] + path, json=body, timeout=ClientTimeout(total=30)) as upstream:
                if upstream.status >= 400:
                    raise web.HTTPBadGateway(text=f"Bridge returned {upstream.status}")
                result = await upstream.json()
        except (ClientError, asyncio.TimeoutError, ValueError) as exc:
            _LOGGER.warning("Audiobook bridge request failed: %s", exc)
            raise web.HTTPBadGateway(text="Bridge request failed") from exc
        if action == "start":
            # Never expose the private bridge URLs. Only issue signed HA paths.
            tracks = result.get("tracks")
            if not isinstance(tracks, list):
                raise web.HTTPBadGateway(text="Invalid bridge tracks")
            for track in tracks:
                original = track.get("url", "")
                if not isinstance(original, str) or not original.startswith("/api/player/audio/"):
                    raise web.HTTPBadGateway(text="Unexpected bridge audio URL")
                handle = original.rsplit("/", 1)[-1]
                if not handle or not all(c.isalnum() or c in "-_" for c in handle):
                    raise web.HTTPBadGateway(text="Invalid audio handle")
                state.setdefault("audio_handles", set()).add(handle)
                track["url"] = _signed(hass, f"{PREFIX}/{entry_id}/audio/{handle}")
        else:
            await state["coordinator"].async_request_refresh()
        return web.json_response(result, headers={"Cache-Control": "no-store"})


class PlayerAudioView(HomeAssistantView):
    url = PREFIX + "/{entry_id}/audio/{handle}"
    name = "api:audiobookshelf_homehub:audio"
    requires_auth = True

    async def get(self, request, entry_id, handle):
        hass = request.app["hass"]
        state = _entry(hass, entry_id)
        if not handle or not all(c.isalnum() or c in "-_" for c in handle):
            raise web.HTTPBadRequest()
        session = async_get_clientsession(hass)
        headers = {}
        if request.headers.get("Range"):
            headers["Range"] = request.headers["Range"]
        try:
            upstream = await session.get(
                state["url"] + "/api/player/audio/" + quote(handle, safe=""),
                headers=headers, timeout=ClientTimeout(total=None, sock_connect=15, sock_read=60),
            )
        except (ClientError, asyncio.TimeoutError) as exc:
            raise web.HTTPBadGateway(text="Audio bridge unavailable") from exc
        try:
            if upstream.status not in (200, 206):
                raise web.HTTPBadGateway(text=f"Audio bridge returned {upstream.status}")
            outgoing = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}
            for key in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"):
                if key in upstream.headers:
                    outgoing[key] = upstream.headers[key]
            response = web.StreamResponse(status=upstream.status, headers=outgoing)
            await response.prepare(request)
            async for chunk in upstream.content.iter_chunked(65536):
                await response.write(chunk)
            await response.write_eof()
            return response
        except (ConnectionResetError, asyncio.CancelledError):
            return response
        finally:
            upstream.close()


class PlayerCoverView(HomeAssistantView):
    url = PREFIX + "/{entry_id}/cover/{book_id}"
    name = "api:audiobookshelf_homehub:cover"
    requires_auth = True

    async def get(self, request, entry_id, book_id):
        hass = request.app["hass"]
        state = _entry(hass, entry_id)
        if not book_id or not all(c.isalnum() or c in "-_" for c in book_id):
            raise web.HTTPBadRequest()
        session = async_get_clientsession(hass)
        try:
            async with session.get(state["url"] + "/cover/" + quote(book_id, safe=""), timeout=ClientTimeout(total=20)) as upstream:
                if upstream.status != 200:
                    raise web.HTTPBadGateway(text="Cover unavailable")
                if upstream.content_length and upstream.content_length > 8 * 1024 * 1024:
                    raise web.HTTPRequestEntityTooLarge(max_size=8 * 1024 * 1024, actual_size=upstream.content_length)
                data = await upstream.content.read(8 * 1024 * 1024 + 1)
                if len(data) > 8 * 1024 * 1024:
                    raise web.HTTPRequestEntityTooLarge(max_size=8 * 1024 * 1024, actual_size=len(data))
                mime = upstream.headers.get("Content-Type", "image/jpeg")
                if not mime.startswith("image/"):
                    raise web.HTTPBadGateway(text="Invalid cover MIME type")
                return web.Response(body=data, content_type=mime.split(";", 1)[0], headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
        except (ClientError, asyncio.TimeoutError) as exc:
            raise web.HTTPBadGateway(text="Cover bridge unavailable") from exc


def register_views(hass):
    hass.http.register_view(PlayerApiView())
    hass.http.register_view(PlayerAudioView())
    hass.http.register_view(PlayerCoverView())
