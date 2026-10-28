from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..model.api_tokens import ApiTokens
from .oauth_state import OAuthStateStore
from .routers import (
    budget,
    cash_records,
    categories,
    import_failures,
    incomes,
    index,
    oauth_google,
    payment_plans,
    summary,
    transactions,
)


def create_app(
    db_path: Path,
    api_tokens: ApiTokens,
    cors_origins: list[str] | None = None,
    google_redirect_uri: str | None = None,
) -> FastAPI:
    """google_redirect_uri が無ければ、Gmail 連携のエンドポイントは 503 を返す"""
    app = FastAPI(title="Tsukena API")
    # エンドポイントは routers/ にリソースごとに置き、ここで受け取った値は app.state から読む
    app.state.db_path = db_path
    app.state.api_tokens = api_tokens
    app.state.google_redirect_uri = google_redirect_uri
    app.state.oauth_states = OAuthStateStore()

    # Flutter Web の開発サーバーはポートが毎回変わるため、ローカルのオリジンをポート問わず許可する
    app.add_middleware(
        CORSMiddleware,
        # 本番の Web 版（GitHub Pages）は API と別のオリジンなので、設定に書いたオリジンを許可する（→ ADR-0010）
        allow_origins=cors_origins or [],
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        # Authorization はブラウザが既定では許さないヘッダーなので、明示しないとプリフライトで断られる
        allow_headers=["Authorization", "Content-Type"],
    )

    for module in (
        index,
        summary,
        transactions,
        payment_plans,
        incomes,
        categories,
        budget,
        cash_records,
        import_failures,
        oauth_google,
    ):
        app.include_router(module.router)

    return app
