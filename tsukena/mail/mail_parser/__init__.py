from collections.abc import Callable
from dataclasses import dataclass
from email.utils import parseaddr

from ...model.enum.source import Source
from ...model.mail_message_model import MailMessage
from ...model.parsed_payment_model import ParsedPayment
from . import jcb_card
from .errors import UnparsableMailError
from .usage import Usage

__all__ = ["UnparsableMailError", "parse", "payment_methods"]


@dataclass(frozen=True)
class _Registration:
    payment_method: str
    parse_body: Callable[[str], list[Usage]]


# 送り主のメールアドレス（小文字）→ 解析器と支払い手段（→ docs/design.md 4.1）。
# ここに書いた支払い手段は、config.toml に締め日のルールが無ければならない
_REGISTRY: dict[str, _Registration] = {
    "mail@qa.jcb.co.jp": _Registration("JCBカード", jcb_card.parse_body),
}


def payment_methods() -> set[str]:
    """登録表にある支払い手段。起動時に、締め日のルールが揃っているかの照合に使う"""
    return {r.payment_method for r in _REGISTRY.values()}


def parse(mail: MailMessage) -> list[ParsedPayment]:
    """利用通知メールから、支払いの一覧を取り出す（→ docs/design.md 4.1）。

    - 送り主のメールアドレスで解析器を選ぶ。登録表に無い送り主なら UnparsableMailError を投げる
    - 支払いが1件も取り出せなければ UnparsableMailError を投げる。
      記録が残らないまま、次の周期で何度も解析し直さないため
    - 重複排除キーは gmail:{message_id}:{連番}。連番は本文に出てくる順に 0 から振る
    """
    address = parseaddr(mail.sender)[1].lower()
    registration = _REGISTRY.get(address)
    if registration is None:
        raise UnparsableMailError("登録されていない送り主です")

    usages = registration.parse_body(mail.body)
    if not usages:
        raise UnparsableMailError("支払いが見つかりません")

    return [
        ParsedPayment(
            occurred_date=u.occurred_date,
            occurred_time=u.occurred_time,
            amount=u.amount,
            merchant=u.merchant,
            payment_method=registration.payment_method,
            source=Source.GMAIL,
            source_ref=f"{Source.GMAIL}:{mail.message_id}:{i}",
        )
        for i, u in enumerate(usages)
    ]
