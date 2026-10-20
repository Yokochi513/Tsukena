import dataclasses
import datetime
import sqlite3

from ..cash_parser import parse_cash
from ..model.enum.record_outcome import RecordOutcome
from ..model.enum.source import Source
from ..model.enum.status import Status
from ..model.parsed_payment_model import ParsedPayment
from ..model.record_model import RecordResult
from ..model.transaction_model import Transaction, TransactionUpdate
from ..normalize import normalize
from ..repositories.category_repository import category_exists
from ..repositories.merchant_rule_repository import upsert_merchant_rule
from ..repositories.transaction_repository import (
    fetch_transaction,
    source_ref_exists,
    update_transaction,
)
from .recorder import JST, record_payment

CASH_PAYMENT_METHOD = "現金"


class TransactionNotFoundError(Exception):
    pass


class CategoryNotFoundError(Exception):
    pass


class InvalidPaidDateError(Exception):
    pass


class UnparsableMessageError(Exception):
    pass


def modify_transaction(
    conn: sqlite3.Connection, transaction_id: int, update: TransactionUpdate
) -> Transaction:
    """記録を修正する。送られた項目（None でない項目）だけを変える。

    - category_id を送ると確定にし、照合キーの分類ルールを作成または上書きする（照合キーが空なら作らない）
    - merchant を送ると照合キーを作り直す。カテゴリと状態は変えない
    - memo は分類に使わないため、送っても照合キー・カテゴリ・状態は変えない
    - occurred_date だけを送ったときの支払日の計算し直しは、支払い手段のルールがまだ無いため行わない
    """
    current = fetch_transaction(conn, transaction_id)
    if current is None:
        raise TransactionNotFoundError
    if update == TransactionUpdate():
        return current

    if update.category_id is not None and not category_exists(conn, update.category_id):
        raise CategoryNotFoundError

    occurred_date = update.occurred_date or current.occurred_date
    paid_date = update.paid_date or current.paid_date
    if paid_date < occurred_date:
        raise InvalidPaidDateError

    merchant = update.merchant if update.merchant is not None else current.merchant
    merchant_key = (
        normalize(merchant) if update.merchant is not None else current.merchant_key
    )

    updated = dataclasses.replace(
        current,
        occurred_date=occurred_date,
        paid_date=paid_date,
        amount=update.amount if update.amount is not None else current.amount,
        merchant=merchant,
        merchant_key=merchant_key,
        memo=update.memo if update.memo is not None else current.memo,
        category_id=update.category_id
        if update.category_id is not None
        else current.category_id,
        status=Status.CONFIRMED if update.category_id is not None else current.status,
        updated_at=datetime.datetime.now(JST),
    )

    # 記録の修正とルールの学習は、片方だけが残らないよう1つのトランザクションで行う
    with conn:
        update_transaction(conn, updated)
        if update.category_id is not None and merchant_key != "":
            upsert_merchant_rule(conn, merchant_key, update.category_id)
    return updated


def record_cash(
    conn: sqlite3.Connection, text: str, message_id: str, sent_at: datetime.datetime
) -> RecordResult:
    """Discord のメッセージから現金の記録を作る（→ docs/api_list.md 2.8）。

    - 本文を分解できなければ UnparsableMessageError を投げ、記録しない
    - 利用日と時刻は送信時刻を JST に変換した日付と時刻（秒は切り捨て）
    - 重複・削除済みの判定、分類、保存は記録（recorder）が行う
    """
    entry = parse_cash(text)
    if entry is None:
        raise UnparsableMessageError

    occurred_at = sent_at.astimezone(JST)
    payment = ParsedPayment(
        occurred_date=occurred_at.date(),
        occurred_time=occurred_at.time().replace(second=0, microsecond=0),
        amount=entry.amount,
        merchant=entry.memo,
        payment_method=CASH_PAYMENT_METHOD,
        source=Source.DISCORD,
        source_ref=f"{Source.DISCORD}:{message_id}",
    )

    try:
        with conn:
            return record_payment(conn, payment)
    except sqlite3.IntegrityError:
        # 確認してから保存するまでの間に、同じメッセージが記録された（bot の再送など）
        if source_ref_exists(conn, payment.source_ref):
            return RecordResult(outcome=RecordOutcome.DUPLICATE)
        raise
