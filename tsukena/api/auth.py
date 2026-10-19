import secrets
from collections.abc import Callable
from enum import Enum

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..model.api_tokens import ApiTokens

# Header で受けると、Swagger UI は Authorization ヘッダーを送らない（OpenAPI の仕様で無視される）。
# 認証の仕組みとして宣言し、Swagger UI の Authorize ボタンから送れるようにする。
# トークンが無いときの応答を自分で決めるため、auto_error は切る
_bearer = HTTPBearer(auto_error=False)


class Caller(Enum):
    BOT = "bot"
    APP = "app"


def get_caller(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),  # noqa: B008
) -> Caller:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing token")
    token = credentials.credentials

    tokens: ApiTokens = request.app.state.api_tokens

    if secrets.compare_digest(token, tokens.bot):
        return Caller.BOT
    if secrets.compare_digest(token, tokens.app):
        return Caller.APP
    raise HTTPException(status_code=401, detail="Invalid token")


def allow(*callers: Caller) -> Callable[[Caller], None]:
    def check(caller: Caller = Depends(get_caller)) -> None:  # noqa: B008
        if caller not in callers:
            raise HTTPException(status_code=403, detail="Not allowed")

    return check
