import datetime

import pytest

from tsukena.model.enum.payment_timing import PaymentTiming
from tsukena.model.payment_rule_model import PaymentRule
from tsukena.payment_plan import (
    RevolvingItem,
    installment_charges,
    revolving_schedule,
    skip_charges,
)

# JCB: 15日締め・翌月10日払い、実質年率 18.00%、リボの元金は月1万円
JCB = PaymentRule(
    payment_method="JCBカード",
    timing=PaymentTiming.CARD,
    closing_day=15,
    withdrawal_day=10,
    withdrawal_month_offset=1,
    fee_rate=18.0,
    revolving_principal=10000,
)


def test_分割払いは_JCBの計算例と同じ額になる():
    # JCB の案内の例: 10万円を10回。初回は10/16〜11/10の日割り、最終回で端数を調整する
    charges = installment_charges(100000, datetime.date(2026, 11, 10), 10, JCB)

    assert [c.amount for c in charges] == [10625] + [10843] * 8 + [10842]
    assert sum(c.principal for c in charges) == 100000
    assert [c.paid_date for c in charges[:3]] == [
        datetime.date(2026, 11, 10),
        datetime.date(2026, 12, 10),
        datetime.date(2027, 1, 10),
    ]


@pytest.mark.parametrize("count", [2, 61])
def test_分割払いの回数が範囲の外なら_ValueErrorを投げる(count):
    with pytest.raises(ValueError):
        installment_charges(10000, datetime.date(2026, 11, 10), count, JCB)


def test_スキップ払いは_送った月の引き落とし日に元金と手数料を1回で払う():
    # JCB の案内の例: 1万円を3か月送ると、手数料は 10,000 × 1.5% × 3 = 450円
    (charge,) = skip_charges(10000, datetime.date(2026, 8, 10), 3, JCB)

    assert charge.paid_date == datetime.date(2026, 11, 10)
    assert (charge.principal, charge.fee) == (10000, 450)


@pytest.mark.parametrize("months", [0, 7])
def test_スキップ払いで送れる月数の外なら_ValueErrorを投げる(months):
    with pytest.raises(ValueError):
        skip_charges(10000, datetime.date(2026, 8, 10), months, JCB)


def test_リボ払いの初回は_JCBの計算例と同じ額になる():
    # JCB の案内の例: 残高7万円、10/16〜11/10の26日で、手数料は 70,000 × 18% × 26 ÷ 365 = 897円
    _, months = revolving_schedule(
        [RevolvingItem(1, 70000, datetime.date(2026, 11, 10))], JCB, {}
    )

    assert (months[0].principal, months[0].fee) == (10000, 897)
    assert months[0].balance == 60000
    assert len(months) == 7
    assert months[-1].balance == 0


def test_リボ払いの元金は古い支出から充て_手数料は支出ごとに振り分ける():
    items = [
        RevolvingItem(2, 15000, datetime.date(2026, 11, 10)),
        RevolvingItem(1, 8000, datetime.date(2026, 11, 10)),
    ]
    by_transaction, months = revolving_schedule(items, JCB, {})

    first = months[0]
    assert first.principal == 10000
    # 同じ支払日なら id の小さい支出から充てる
    assert by_transaction[1][0].principal == 8000
    assert by_transaction[2][0].principal == 2000
    # 支出ごとの引き落としを足すと、月の合計と一致する
    for m in months:
        assert m.fee == sum(
            c.fee
            for cs in by_transaction.values()
            for c in cs
            if c.paid_date == m.paid_date
        )


def test_リボ払いの手数料を直した月は_その額を使う():
    _, months = revolving_schedule(
        [RevolvingItem(1, 70000, datetime.date(2026, 11, 10))], JCB, {"2026-11": 900}
    )

    assert (months[0].fee, months[0].fee_edited) == (900, True)
    assert months[1].fee_edited is False


def test_リボ払いの支出が無ければ_引き落としも無い():
    assert revolving_schedule([], JCB, {}) == ({}, [])
