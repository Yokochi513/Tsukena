import os
import tomllib
from pathlib import Path

from .model.api_tokens import ApiTokens

CONFIG_PATH = Path(__file__).resolve().parent / "config.toml"


def load_db_path() -> Path:
    with CONFIG_PATH.open("rb") as f:
        config = tomllib.load(f)
    return (CONFIG_PATH.parent / config["database"]["path"]).resolve()


def load_cors_origins() -> list[str]:
    """ブラウザから API を呼んでよいオリジン（Web 版のアプリの置き場所）を返す。"""
    with CONFIG_PATH.open("rb") as f:
        config = tomllib.load(f)
    return config["cors"]["origins"]


def load_api_token() -> ApiTokens:
    tokens = ApiTokens(
        app=os.environ["TSUKENA_APP_API_TOKEN"], bot=os.environ["TSUKENA_BOT_API_TOKEN"]
    )
    if tokens.app == tokens.bot:
        raise ValueError("アプリ用とbot用のトークンに同じ値が設定されています")
    return tokens
