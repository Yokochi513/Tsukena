import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class Usage:
    """送り主ごとの解析器が本文から取り出す、支払い1件分の値。

    支払い手段と重複排除キーは送り主とメールの ID から決まるため、parse が付け足す。
    """

    occurred_date: datetime.date
    occurred_time: datetime.time | None  # 本文に無ければ None
    amount: int
    merchant: str  # 生の文字列のまま。無ければ空文字
