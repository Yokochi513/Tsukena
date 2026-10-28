"""支出の支払い方法（1回払い・スキップ・分割・リボ払い）を変え、引き落としの予定を保つ（→ docs/adr/0011）"""

import dataclasses
import datetime
import sqlite3

from ..config import load_payment_rules
from ..model.charge_model import Charge, RevolvingMonth
from ..model.enum.payment_plan import PaymentPlan
from ..model.enum.payment_timing import PaymentTiming
from ..model.payment_rule_model import PaymentRule
from ..model.transaction_model import Transaction
from ..payment_plan import installment_charges, revolving_schedule, skip_charges
from ..repositories.charge_repository import (
    delete_revolving_fee,
    delete_revolving_fees,
    fetch_revolving_fees,
    fetch_revolving_items,
    replace_charges,
    upsert_revolving_fee,
)
from ..repositories.transaction_repository import fetch_transaction, update_transaction
from .recorder import JST


class TransactionNotFoundError(Exception):
    pass


class PlanNotAvailableError(Exception):
    """支払い手段のルールに、その支払い方法に要る値（手数料率・リボの元金）が無い"""


class InvalidPlanCountError(Exception):
    """スキップの月数・分割の回数が、選べる範囲に無い"""


class ChargeNotFoundError(Exception):
    pass


class FeeNotEditableError(Exception):
    """リボ払いの手数料は支出ごとではなく、支払い手段と月で直す"""


def change_payment_plan(
    conn: sqlite3.Connection,
    transaction_id: int,
    plan: PaymentPlan,
    count: int | None = None,
) -> Transaction:
    """支出の支払い方法を変え、引き落としの予定を作り直す。

    - count はスキップなら繰り延べる月数、分割なら回数。1回払いとリボ払いでは使わない
    - 手で直した手数料は、作り直すと消える
    - リボ払いにした・やめたときは、同じ支払い手段のリボ払いの引き落としを全部計算し直す
    """
    current = fetch_transaction(conn, transaction_id)
    if current is None:
        raise TransactionNotFoundError
    if plan in (PaymentPlan.SKIP, PaymentPlan.INSTALLMENT):
        if count is None:
            raise InvalidPlanCountError
    else:
        count = None

    updated = dataclasses.replace(
        current,
        payment_plan=plan,
        plan_count=count,
        updated_at=datetime.datetime.now(JST),
    )
    charges = _scheduled_charges(updated, _rule_for(updated))

    with conn:
        update_transaction(conn, updated)
        replace_charges(conn, transaction_id, charges)
        if PaymentPlan.REVOLVING in (current.payment_plan, plan):
            _rebuild_revolving(conn, _rule_for_method(current.payment_method))
    result = fetch_transaction(conn, transaction_id)
    assert result is not None
    return result


def rebuild_charges(
    conn: sqlite3.Connection, before: Transaction, after: Transaction
) -> None:
    """金額か支払日を直した支出の、引き落としの予定を作り直す。commit は呼び出す側が行う"""
    if after.payment_plan == PaymentPlan.LUMP:
        return
    if (before.amount, before.paid_date) == (after.amount, after.paid_date):
        return
    if after.payment_plan == PaymentPlan.REVOLVING:
        _rebuild_revolving(conn, _rule_for(after))
    else:
        replace_charges(conn, after.id, _scheduled_charges(after, _rule_for(after)))


def rebuild_revolving_after_delete(
    conn: sqlite3.Connection, deleted: Transaction
) -> None:
    """リボ払いの支出を消したあと、残りのリボ払いの引き落としを計算し直す"""
    if deleted.payment_plan != PaymentPlan.REVOLVING:
        return
    with conn:
        _rebuild_revolving(conn, _rule_for_method(deleted.payment_method))


def set_charge_fee(
    conn: sqlite3.Connection, transaction_id: int, seq: int, fee: int | None
) -> Transaction:
    """スキップ・分割払いの1回分の手数料を、実際の引き落としに合わせて直す。fee が None なら計算した額に戻す"""
    current = fetch_transaction(conn, transaction_id)
    if current is None:
        raise TransactionNotFoundError
    if current.payment_plan == PaymentPlan.REVOLVING:
        raise FeeNotEditableError
    target = next((c for c in current.charges if c.seq == seq), None)
    if target is None:
        raise ChargeNotFoundError

    if fee is None:
        computed = _scheduled_charges(current, _rule_for(current))
        replaced = next(c for c in computed if c.seq == seq)
    else:
        replaced = dataclasses.replace(target, fee=fee, fee_edited=True)
    charges = tuple(replaced if c.seq == seq else c for c in current.charges)

    with conn:
        replace_charges(conn, transaction_id, charges)
    result = fetch_transaction(conn, transaction_id)
    assert result is not None
    return result


def fetch_revolving(
    conn: sqlite3.Connection, payment_method: str
) -> list[RevolvingMonth]:
    """支払い手段のリボ払いの、月ごとの引き落とし（元金・手数料・残高）"""
    rule = _rule_for_method(payment_method)
    if rule.revolving_principal is None:
        raise PlanNotAvailableError
    _, months = revolving_schedule(
        fetch_revolving_items(conn, payment_method),
        rule,
        fetch_revolving_fees(conn, payment_method),
    )
    return months


def set_revolving_fee(
    conn: sqlite3.Connection, payment_method: str, month: str, fee: int | None
) -> list[RevolvingMonth]:
    """リボ払いのある月の手数料（リボ全体の額）を直す。fee が None なら計算した額に戻す"""
    rule = _rule_for_method(payment_method)
    if rule.revolving_principal is None:
        raise PlanNotAvailableError
    with conn:
        if fee is None:
            delete_revolving_fee(conn, payment_method, month)
        else:
            upsert_revolving_fee(conn, payment_method, month, fee)
        return _rebuild_revolving(conn, rule)


def _scheduled_charges(t: Transaction, rule: PaymentRule) -> tuple[Charge, ...]:
    """1回払い・リボ払いは支出ごとの予定を持たないので空を返す（リボは _rebuild_revolving が作る）"""
    try:
        if t.payment_plan == PaymentPlan.SKIP:
            assert t.plan_count is not None
            return skip_charges(t.amount, t.paid_date, t.plan_count, rule)
        if t.payment_plan == PaymentPlan.INSTALLMENT:
            assert t.plan_count is not None
            return installment_charges(t.amount, t.paid_date, t.plan_count, rule)
    except ValueError:
        raise InvalidPlanCountError from None
    return ()


def _rebuild_revolving(
    conn: sqlite3.Connection, rule: PaymentRule
) -> list[RevolvingMonth]:
    """支払い手段のリボ払いの支出を全部まとめて計算し直し、支出ごとの引き落としを置き換える"""
    method = rule.payment_method
    items = fetch_revolving_items(conn, method)
    if not items:
        # 直した手数料が、あとで新しくリボにした支出の月に当たらないよう消しておく
        delete_revolving_fees(conn, method)
        return []
    by_transaction, months = revolving_schedule(
        items, rule, fetch_revolving_fees(conn, method)
    )
    for transaction_id, charges in by_transaction.items():
        replace_charges(conn, transaction_id, charges)
    return months


def _rule_for(t: Transaction) -> PaymentRule:
    rule = _rule_for_method(t.payment_method)
    if t.payment_plan == PaymentPlan.LUMP:
        return rule
    if rule.timing != PaymentTiming.CARD or rule.fee_rate is None:
        raise PlanNotAvailableError
    if t.payment_plan == PaymentPlan.REVOLVING and rule.revolving_principal is None:
        raise PlanNotAvailableError
    return rule


def _rule_for_method(payment_method: str) -> PaymentRule:
    rule = load_payment_rules().get(payment_method)
    if rule is None:
        raise PlanNotAvailableError
    return rule
