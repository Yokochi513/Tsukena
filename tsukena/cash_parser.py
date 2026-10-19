import re
from dataclasses import dataclass

# 全角の英数字・記号（！〜～）を半角に変えるための対応表
_FULLWIDTH_TO_HALFWIDTH = {code: code - 0xFEE0 for code in range(0xFF01, 0xFF5F)}
_AMOUNT_PATTERN = re.compile(r"[0-9]+")


@dataclass(frozen=True)
class CashEntry:
    memo: str
    amount: int


def parse_cash(text: str) -> CashEntry | None:
    """Discord のメッセージ本文を、メモと金額に分解する（→ docs/design.md 10.1）。

    最後の空白区切り（全角の空白を含む）の部分を金額、それより前をメモとして扱う。
    金額はカンマ・末尾の「円」・全角数字を受け付ける。メモは表示用に生の文字列のまま返す。
    金額が無い、数字でない、0円以下のときは None を返す。
    """
    parts = text.split()
    if not parts:
        return None

    amount_text = parts[-1].translate(_FULLWIDTH_TO_HALFWIDTH).replace(",", "")
    amount_text = amount_text.removesuffix("円")
    if not _AMOUNT_PATTERN.fullmatch(amount_text):
        return None
    amount = int(amount_text)
    if amount < 1:
        return None

    # メモの中の空白は残す。最後の部分（金額）より前を、前後の空白だけ除いて取り出す
    memo = text[: text.rstrip().rfind(parts[-1])].strip()
    return CashEntry(memo=memo, amount=amount)
