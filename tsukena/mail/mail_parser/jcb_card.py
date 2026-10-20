import datetime
import re

from .errors import UnparsableMailError
from .usage import Usage

# 全角の英数字・記号（！〜～）を半角に変えるための対応表。日付と金額にだけ使い、店名には使わない
_FULLWIDTH_TO_HALFWIDTH = {code: code - 0xFEE0 for code in range(0xFF01, 0xFF5F)}

# JCB の利用通知メールには2つの形がある。
# - まとめての通知: 1件ごとに「◆ご利用1」「◆ご利用2」…の見出しが付き、日付は【ご利用日】（時刻なし）
# - 利用のたびの通知: 見出しが無く1件だけで、日付は【ご利用日時(日本時間)】（時刻あり）
_BLOCK_HEADING = re.compile(r"◆ご利用[0-9０-９]+")
_DATE = re.compile(
    r"【ご利用日(?:時[(（]日本時間[)）])?】[ \t　]*(\S+)(?:[ \t　]+([0-9０-９]{1,2}[:：][0-9０-９]{2}))?"
)
_AMOUNT = re.compile(r"【ご利用金額】[ \t　]*(\S+)")
_MERCHANT = re.compile(r"【ご利用先】[ \t　]*(.*)")


def parse_body(body: str) -> list[Usage]:
    """JCB カードの利用通知メールの本文から、支払いを取り出す。

    - 「◆ご利用N」の見出しがあれば、見出しごとに1件として読む。無ければ本文全体を1件として読む
    - 各件の、ご利用日（またはご利用日時）・ご利用金額・ご利用先を読む。時刻が無ければ None にする
    - 日付・金額が読めない支払いが1件でもあれば UnparsableMailError を投げる。
      一部だけを記録して、残りを黙って捨てないため
    """
    blocks = _BLOCK_HEADING.split(body)[1:]
    if not blocks and _AMOUNT.search(body):
        blocks = [body]
    return [_parse_block(block) for block in blocks]


def _parse_block(block: str) -> Usage:
    date_match = _DATE.search(block)
    amount_match = _AMOUNT.search(block)
    if date_match is None:
        raise UnparsableMailError("ご利用日が見つかりません")
    if amount_match is None:
        raise UnparsableMailError("ご利用金額が見つかりません")
    merchant_match = _MERCHANT.search(block)

    time_text = date_match.group(2)
    return Usage(
        occurred_date=_to_date(date_match.group(1)),
        occurred_time=_to_time(time_text) if time_text else None,
        amount=_to_amount(amount_match.group(1)),
        merchant=merchant_match.group(1).strip() if merchant_match else "",
    )


def _to_date(text: str) -> datetime.date:
    try:
        return datetime.datetime.strptime(
            text.translate(_FULLWIDTH_TO_HALFWIDTH), "%Y/%m/%d"
        ).date()
    except ValueError as error:
        raise UnparsableMailError(f"ご利用日を読めません: {text}") from error


def _to_time(text: str) -> datetime.time:
    try:
        return datetime.datetime.strptime(
            text.translate(_FULLWIDTH_TO_HALFWIDTH), "%H:%M"
        ).time()
    except ValueError as error:
        raise UnparsableMailError(f"ご利用時刻を読めません: {text}") from error


def _to_amount(text: str) -> int:
    digits = text.translate(_FULLWIDTH_TO_HALFWIDTH).replace(",", "").removesuffix("円")
    if not digits.isdecimal() or int(digits) < 1:
        # 取り消しなどで金額がマイナスのときも、記録せずに知らせる
        raise UnparsableMailError(f"ご利用金額を読めません: {text}")
    return int(digits)
