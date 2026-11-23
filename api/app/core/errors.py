"""Errors meant to be shown to non-technical users (PO decision 19/11/2026).

``detail`` is a plain-language Spanish message that says what happened and what to do next; ``code`` is a stable
identifier the web app can use to choose how to display it. The HTTP status stays for clients and logs, but the UI
should show the message, never the status number.
"""

from fastapi import HTTPException


class UserFacingError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, headers: dict[str, str] | None = None) -> None:
        super().__init__(status_code, message, headers=headers)
        self.code = code
