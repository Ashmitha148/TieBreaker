import uuid
import contextvars
from starlette.types import ASGIApp, Receive, Scope, Send

_request_id_var = contextvars.ContextVar("request_id", default=None)


class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        request_id = headers.get(b"x-request-id", b"").decode()
        if not request_id:
            request_id = str(uuid.uuid4())
        _request_id_var.set(request_id)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append([b"x-request-id", request_id.encode()])
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


def get_request_id() -> str:
    return _request_id_var.get() or ""