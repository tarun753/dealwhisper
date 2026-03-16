from __future__ import annotations

from fastapi import HTTPException, Request, WebSocket, status

from .config import Settings


def _extract_bearer_token(header_value: str | None) -> str | None:
    if not header_value:
        return None
    scheme, _, token = header_value.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _resolve_token(header_value: str | None, query_value: str | None) -> str | None:
    return query_value or _extract_bearer_token(header_value)


def authorize_request(request: Request, settings: Settings) -> None:
    if not settings.backend_shared_secret:
        return

    token = _resolve_token(
        request.headers.get("authorization"),
        request.query_params.get("token"),
    )
    if token != settings.backend_shared_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized.")


async def authorize_websocket(websocket: WebSocket, settings: Settings) -> bool:
    if not settings.backend_shared_secret:
        return True

    token = _resolve_token(
        websocket.headers.get("authorization"),
        websocket.query_params.get("token"),
    )
    if token == settings.backend_shared_secret:
        return True

    await websocket.send_json({"type": "session.error", "message": "Unauthorized."})
    await websocket.close(code=1008)
    return False
