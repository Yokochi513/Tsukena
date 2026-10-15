import dataclasses
import datetime
import sqlite3

from ..model.enum.status import Status
from ..model.transaction_model import Transaction, TransactionUpdate
from ..normalize import normalize
from ..repositories.category_repository import category_exists
from ..repositories.merchant_rule_repository import upsert_merchant_rule
from ..repositories.transaction_repository import (
    fetch_transaction,
    update_transaction,
)

JST = datetime.timezone(datetime.timedelta(hours=9), "JST")


class TransactionNotFoundError(Exception):
    pass


class CategoryNotFoundError(Exception):
    pass


class InvalidPaidDateError(Exception):
    pass


def modify_transaction(
    conn: sqlite3.Connection, transaction_id: int, update: TransactionUpdate
) -> Transaction:
    """記録を修正する。送られた項目（None でない項目）だけを変える。

    - category_id を送ると確定にし、照合キーの分類ルールを作成または上書きする（照合キーが空なら作らない）
    - merchant を送ると照合キーを作り直す。カテゴリと状態は変えない
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
