"""Server-side Zoom transport; no credentials or provider response bodies in errors."""
from typing import Literal

import httpx

from app.core.config import Settings

AuthenticationMode = Literal["open", "authenticated", "institutional"]


class ZoomError(RuntimeError):
    pass


def meeting_settings(mode: AuthenticationMode, profile_id: str | None = None) -> dict:
    if mode == "open":
        return {"meeting_authentication": False}
    if mode == "authenticated":
        return {"meeting_authentication": True}
    if mode == "institutional" and profile_id and profile_id.strip():
        return {"meeting_authentication": True, "authentication_option": profile_id}
    raise ValueError("Unsupported authentication mode or missing institutional profile")


class ZoomClient:
    def __init__(self, config: Settings, transport: httpx.Client):
        self.config = config
        self.transport = transport

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            response = self.transport.request(method, url, timeout=15, follow_redirects=False, **kwargs)
        except httpx.HTTPError:
            raise ZoomError("Zoom request failed; outcome may be unknown") from None
        if not 200 <= response.status_code < 300:
            raise ZoomError(f"Zoom rejected request ({response.status_code})")
        return response

    def _token(self) -> str:
        c = self.config
        if not c.zoom_enabled or not all((c.zoom_account_id, c.zoom_client_id, c.zoom_client_secret)):
            raise ZoomError("Zoom integration unavailable")
        response = self._request(
            "POST", "https://zoom.us/oauth/token",
            data={"grant_type": "account_credentials", "account_id": c.zoom_account_id.get_secret_value()},
            auth=(c.zoom_client_id.get_secret_value(), c.zoom_client_secret.get_secret_value()),
        )
        try:
            token = response.json()["access_token"]
            if not isinstance(token, str) or not token:
                raise ValueError()
            return token
        except (ValueError, KeyError, TypeError):
            raise ZoomError("Invalid Zoom token response") from None

    def _api(self, method: str, path: str, **kwargs) -> httpx.Response:
        return self._request(method, "https://api.zoom.us/v2" + path,
                             headers={"Authorization": "Bearer " + self._token()}, **kwargs)

    def create_meeting(self, topic: str, start_time: str, duration: int,
                       mode: AuthenticationMode, profile_id: str | None = None) -> dict:
        response = self._api("POST", "/users/me/meetings", json={
            "topic": topic, "type": 2, "start_time": start_time, "duration": duration,
            "settings": {**meeting_settings(mode, profile_id), "join_before_host": False},
        })
        try:
            data = response.json()
            return {"id": str(data["id"]), "join_url": data["join_url"]}
        except (ValueError, KeyError, TypeError):
            raise ZoomError("Invalid meeting response; reconcile before retrying") from None

    def update_authentication(self, meeting_id: str, mode: AuthenticationMode,
                              profile_id: str | None = None) -> None:
        if not meeting_id.isascii() or not meeting_id.isdecimal():
            raise ValueError("Invalid meeting ID")
        self._api("PATCH", "/meetings/" + meeting_id,
                  json={"settings": meeting_settings(mode, profile_id)})
