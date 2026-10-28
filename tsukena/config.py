import os
import tomllib
from pathlib import Path
from typing import Any

from .model.api_tokens import ApiTokens
from .model.enum.payment_timing import PaymentTiming
from .model.payment_rule_model import PaymentRule

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


def load_google_redirect_uri() -> str | None:
    """Gmail 連携で、Google が同意のあとに戻してくる先の URL を返す。設定が無ければ None。

    サーバーごとに違い、自分のドメインを公開のリポジトリに載せないため、環境変数で渡す。
    """
    return os.environ.get("TSUKENA_GOOGLE_REDIRECT_URI") or None


def load_payment_rules() -> dict[str, PaymentRule]:
    """支払い手段ごとの締め日のルールを、支払い手段の名前をキーにして返す（→ docs/design.md 7.1）。

    ルールの書き方が誤っていれば ValueError を投げる。誤ったルールで支払日を計算しないため。
    """
    with CONFIG_PATH.open("rb") as f:
        config = tomllib.load(f)
    return {
        name: _to_payment_rule(name, values)
        for name, values in config["payment_methods"].items()
    }


def _to_payment_rule(name: str, values: dict[str, Any]) -> PaymentRule:
    timing = PaymentTiming(values["timing"])
    rule = PaymentRule(
        payment_method=name,
        timing=timing,
        closing_day=values.get("closing_day"),
        withdrawal_day=values.get("withdrawal_day"),
        withdrawal_month_offset=values.get("withdrawal_month_offset"),
        fee_rate=values.get("fee_rate"),
        revolving_principal=values.get("revolving_principal"),
    )
    card_values = (rule.closing_day, rule.withdrawal_day, rule.withdrawal_month_offset)
    plan_values = (rule.fee_rate, rule.revolving_principal)
    if timing == PaymentTiming.IMMEDIATE:
        if any(v is not None for v in card_values + plan_values):
            raise ValueError(f"{name}: 即時の支払い手段に締め日・引き落とし日・手数料は書けません")
        return rule

    if any(v is None for v in card_values):
        raise ValueError(
            f"{name}: closing_day・withdrawal_day・withdrawal_month_offset をすべて書いてください"
        )
    if not 1 <= values["closing_day"] <= 31 or not 1 <= values["withdrawal_day"] <= 31:
        raise ValueError(f"{name}: 締め日・引き落とし日は 1〜31 で書いてください")
    if values["withdrawal_month_offset"] < 1:
        raise ValueError(f"{name}: withdrawal_month_offset は 1 以上で書いてください")
    if rule.fee_rate is not None and not 0 < rule.fee_rate < 100:
        raise ValueError(f"{name}: fee_rate は 0 より大きく 100 より小さい年率（%）で書いてください")
    if rule.revolving_principal is not None:
        if rule.fee_rate is None:
            raise ValueError(f"{name}: revolving_principal を書くときは fee_rate も書いてください")
        if rule.revolving_principal < 1:
            raise ValueError(f"{name}: revolving_principal は 1 以上で書いてください")
    return rule


def load_api_token() -> ApiTokens:
    tokens = ApiTokens(
        app=os.environ["TSUKENA_APP_API_TOKEN"], bot=os.environ["TSUKENA_BOT_API_TOKEN"]
    )
    if tokens.app == tokens.bot:
        raise ValueError("アプリ用とbot用のトークンに同じ値が設定されています")
    return tokens
