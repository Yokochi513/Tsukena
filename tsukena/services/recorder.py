import datetime
import sqlite3

from ..config import load_payment_rules
from ..model.enum.record_outcome import RecordOutcome
from ..model.enum.status import Status
from ..model.parsed_payment_model import ParsedPayment
from ..model.record_model import RecordResult
from ..model.transaction_model import TransactionInput
from ..normalize import normalize
from ..paid_date import calculate_paid_date
from ..repositories.category_repository import fetch_category
from ..repositories.merchant_rule_repository import fetch_rule_category_id
from ..repositories.transaction_repository import (
    deleted_ref_exists,
    insert_transaction,
    source_ref_exists,
)

JST = datetime.timezone(datetime.timedelta(hours=9), "JST")


class UnknownPaymentMethodError(Exception):
    pass


def record_payment(conn: sqlite3.Connection, payment: ParsedPayment) -> RecordResult:
    """支払い1件を記録する。入口（Gmail / Discord）によらず同じ規則で記録する（→ docs/design.md 3）。

    - 同じ重複排除キーの記録が既にあれば DUPLICATE、過去に削除されていれば DELETED を返し、記録しない
    - 分類ルールに照合キーが完全一致すれば確定、無ければ（店名・メモが空のときを含む）確認待ちにする
    - 支払日は、支払い手段の締め日のルールから計算する
    - 支払い手段のルールが設定ファイルに無ければ UnknownPaymentMethodError を投げ、記録しない
    - commit は呼び出す側が行う。メール1通分の支払いをまとめて確定させるため
    """
    # 黙って利用日で埋めないよう、ルールの無い支払い手段は記録しない（→ docs/design.md 7.1）
    rule = load_payment_rules().get(payment.payment_method)
    if rule is None:
        raise UnknownPaymentMethodError(payment.payment_method)

    if source_ref_exists(conn, payment.source_ref):
        return RecordResult(outcome=RecordOutcome.DUPLICATE)
    if deleted_ref_exists(conn, payment.source_ref):
        return RecordResult(outcome=RecordOutcome.DELETED)

    merchant_key = normalize(payment.merchant)
    category_id = (
        fetch_rule_category_id(conn, merchant_key) if merchant_key != "" else None
    )
    new = TransactionInput(
        occurred_date=payment.occurred_date,
        occurred_time=payment.occurred_time,
        paid_date=calculate_paid_date(payment.occurred_date, rule),
        amount=payment.amount,
        merchant=payment.merchant,
        merchant_key=merchant_key,
        category_id=category_id,
        status=Status.CONFIRMED if category_id is not None else Status.PENDING,
        payment_method=payment.payment_method,
        source=payment.source,
        source_ref=payment.source_ref,
    )
    transaction = insert_transaction(conn, new, datetime.datetime.now(JST))

    category = fetch_category(conn, category_id) if category_id is not None else None
    return RecordResult(
        outcome=RecordOutcome.RECORDED, transaction=transaction, category=category
    )
