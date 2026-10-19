import secrets
from collections.abc import Callable
from enum import Enum

from fastapi import Header, HTTPException, Request

from ..model.api_tokens import ApiTokens


class Caller(Enum):
    BOT = "bot"
    APP = "app"


def get_caller(request: Request, authorization: str | None = Header(None)) -> Caller:
    if authorization is None:
        raise HTTPException(status_code=401, detail="Missing token")
    scheme, _, token = authorization.partition(" ")
    if scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Missing token")

    tokens: ApiTokens = request.app.state.api_tokens

    if secrets.compare_digest(token, tokens.bot):
        return Caller.BOT
    if secrets.compare_digest(token, tokens.app):
        return Caller.APP
    raise HTTPException(status_code=401, detail="Invalid token")


def allow(*callers: Caller) -> Callable[[Request, str | None], None]:
    def check(request: Request, authorization: str | None = Header(None)) -> None:
        if get_caller(request, authorization) not in callers:
            raise HTTPException(status_code=403, detail="Not allowed")

    return check
