"""Response hardening without trusting forwarding headers or changing authorization."""
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SecurityResponseMiddleware:
    def __init__(self, app: ASGIApp, environment: str):
        self.app = app
        self.environment = environment

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def hardened(message: Message) -> None:
            if message["type"] == "http.response.start":
                policy = {
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY",
                    b"referrer-policy": b"no-referrer",
                    b"permissions-policy": b"camera=(), microphone=(), geolocation=()",
                }
                if scope.get("path", "").startswith("/api/"):
                    policy[b"cache-control"] = b"no-store"
                # HTTPS is determined by the ASGI server's validated connection scope,
                # never by a caller-supplied X-Forwarded-Proto value here.
                if self.environment != "local" and scope.get("scheme") == "https":
                    policy[b"strict-transport-security"] = b"max-age=31536000"
                headers = [(name, value) for name, value in message.get("headers", []) if name.lower() not in policy]
                message = {**message, "headers": headers + list(policy.items())}
            await send(message)

        await self.app(scope, receive, hardened)
