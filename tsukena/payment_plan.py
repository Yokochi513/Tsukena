"""スキップ・分割・リボ払いの、回ごとの引き落としを計算する（→ docs/adr/0011）。

式は JCB の案内に合わせる。日割りの日数や休日による繰り延べで、実際の引き落とし額と数円〜数十円ずれることがある。
ずれた回は、アプリで手数料を直す。
"""

import calendar
import datetime
from collections import deque
from dataclasses import dataclass
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from .model.charge_model import Charge, RevolvingMonth
from .model.payment_rule_model import PaymentRule
from .paid_date import add_months, closing_date_for, withdrawal_date

SKIP_MONTHS = range(1, 7)  # 1回払いの支払い月の 1〜6 か月後まで送れる
INSTALLMENT_COUNTS = range(3, 61)  # あとから分割で選べる回数


@dataclass(frozen=True)
class RevolvingItem:
    """リボ払いにした支出1件。paid_date（1回払いだったときの支払日）の月から払い始める"""

    transaction_id: int
    amount: int
    paid_date: datetime.date


def skip_charges(
    amount: int, paid_date: datetime.date, months: int, rule: PaymentRule
) -> tuple[Charge, ...]:
    """支払い月を months か月先に送り、その月の引き落とし日に元金と手数料を1回で払う。

    手数料 = 金額 × 月利 × 送った月数（小数点以下は切り捨て）
    """
    if months not in SKIP_MONTHS:
        raise ValueError(
            f"スキップ払いで送れるのは {SKIP_MONTHS.start}〜{SKIP_MONTHS.stop - 1} か月です"
        )
    year, month = add_months(paid_date, months)
    fee = _floor(amount * _monthly_rate(rule) * months)
    return (
        Charge(
            seq=1,
            paid_date=withdrawal_date(year, month, rule),
            principal=amount,
            fee=fee,
        ),
    )


def installment_charges(
    amount: int, paid_date: datetime.date, count: int, rule: PaymentRule
) -> tuple[Charge, ...]:
    """count 回に分けて、paid_date の月から毎月の引き落とし日に払う。

    - 毎回の支払額は (金額 + 金額 × 割賦係数) ÷ 回数（切り捨て）。割賦係数は月利の元利均等から求め、% で小数第2位に丸める
    - 各回の手数料はその時点の残りの元金 × 月利。初回だけは締め日の翌日から引き落とし日までの日割りにする
    - 最終回で残りの元金を払い切る
    """
    if count not in INSTALLMENT_COUNTS:
        raise ValueError(
            f"分割払いの回数は {INSTALLMENT_COUNTS.start}〜{INSTALLMENT_COUNTS.stop - 1} 回です"
        )
    rate = _monthly_rate(rule)
    coefficient = (count * rate / (1 - (1 + rate) ** -count) - 1) * 100
    coefficient = coefficient.quantize(Decimal("0.01"), ROUND_HALF_UP)
    payment = (amount + _floor(amount * coefficient / 100)) // count

    first_days = max((paid_date - closing_date_for(paid_date, rule)).days, 0)
    balance = amount
    charges: list[Charge] = []
    for seq in range(1, count + 1):
        monthly_fee = _floor(balance * rate)
        if seq == count:
            principal, fee = balance, monthly_fee
        else:
            principal = min(payment - monthly_fee, balance)
            fee = (
                _floor(
                    balance * _annual_rate(rule) * first_days / _days_in_year(paid_date)
                )
                if seq == 1
                else monthly_fee
            )
        year, month = add_months(paid_date, seq - 1)
        charges.append(
            Charge(
                seq=seq,
                # 初回は記録の支払日のまま（アプリで直していればその日）にする
                paid_date=paid_date if seq == 1 else withdrawal_date(year, month, rule),
                principal=principal,
                fee=fee,
            )
        )
        balance -= principal
    return tuple(charges)


def revolving_schedule(
    items: list[RevolvingItem], rule: PaymentRule, fee_overrides: dict[str, int]
) -> tuple[dict[int, tuple[Charge, ...]], list[RevolvingMonth]]:
    """1つの支払い手段のリボ払いの支出をまとめて、残高が無くなるまで毎月の引き落としを計算する。

    JCB の定額コースに合わせる。
    - 毎月の元金は設定の額（残高がそれより少なければ残高の全部）。古い支出から順に充てる
    - 毎月の手数料 = 残高 × 年率 × 日数 ÷ 365（うるう年は 366。切り捨て）。日数は、払い始めの月は締め日の翌日から、
      以降は前の引き落とし日の翌日から、その月の引き落とし日まで
    - fee_overrides（YYYY-MM → 円）にある月は、計算した手数料の代わりにその額を使う
    - 手数料は、支出ごとの残高と日数に比例して振り分ける（月の集計で、元の支出のカテゴリに入れるため）

    返すのは、支出ごとの引き落とし（transaction_id → 回の並び）と、月ごとの合計
    """
    assert rule.revolving_principal is not None
    pending = deque(sorted(items, key=lambda i: (i.paid_date, i.transaction_id)))
    balances: dict[int, int] = {}  # 入れた順（古い支出から）に並ぶ
    accrued_until: dict[int, datetime.date] = {}  # 手数料をどの日まで数えたか
    charges: dict[int, list[Charge]] = {i.transaction_id: [] for i in items}
    months: list[RevolvingMonth] = []
    if not pending:
        return {}, months

    year, month = pending[0].paid_date.year, pending[0].paid_date.month
    while pending or balances:
        paid = withdrawal_date(year, month, rule)
        while pending and _year_month(pending[0].paid_date) == (year, month):
            item = pending.popleft()
            balances[item.transaction_id] = item.amount
            accrued_until[item.transaction_id] = closing_date_for(paid, rule)

        if balances:
            key = f"{year:04d}-{month:02d}"
            exact = {
                tid: Decimal(balance)
                * _annual_rate(rule)
                * max((paid - accrued_until[tid]).days, 0)
                / _days_in_year(paid)
                for tid, balance in balances.items()
            }
            fee = fee_overrides.get(key, _floor(sum(exact.values())))
            fees = _apportion(fee, exact)

            principal = min(rule.revolving_principal, sum(balances.values()))
            rest = principal
            for tid in list(balances):
                paid_principal = min(rest, balances[tid])
                rest -= paid_principal
                if paid_principal > 0 or fees[tid] > 0:
                    charges[tid].append(
                        Charge(
                            seq=len(charges[tid]) + 1,
                            paid_date=paid,
                            principal=paid_principal,
                            fee=fees[tid],
                        )
                    )
                balances[tid] -= paid_principal
                accrued_until[tid] = paid
                if balances[tid] == 0:
                    del balances[tid]
            months.append(
                RevolvingMonth(
                    month=key,
                    paid_date=paid,
                    principal=principal,
                    fee=fee,
                    fee_edited=key in fee_overrides,
                    balance=sum(balances.values()),
                )
            )
        year, month = add_months(datetime.date(year, month, 1), 1)

    return {tid: tuple(c) for tid, c in charges.items()}, months


def _apportion(total: int, weights: dict[int, Decimal]) -> dict[int, int]:
    """total を weights に比例して整数で振り分ける。端数は小数部の大きい順に1円ずつ足す"""
    weight_sum = sum(weights.values())
    if weight_sum == 0:
        # 手で直した手数料だけがあり、計算では手数料が出ない月。古い支出にまとめて載せる
        first = next(iter(weights))
        return {tid: (total if tid == first else 0) for tid in weights}
    shares = {tid: Decimal(total) * w / weight_sum for tid, w in weights.items()}
    result = {tid: _floor(s) for tid, s in shares.items()}
    left = total - sum(result.values())
    for tid in sorted(shares, key=lambda t: shares[t] - result[t], reverse=True)[:left]:
        result[tid] += 1
    return result


def _year_month(date: datetime.date) -> tuple[int, int]:
    return date.year, date.month


def _annual_rate(rule: PaymentRule) -> Decimal:
    assert rule.fee_rate is not None
    # float の誤差を持ち込まないよう、設定に書いた文字どおりの値にする
    return Decimal(str(rule.fee_rate)) / 100


def _monthly_rate(rule: PaymentRule) -> Decimal:
    return _annual_rate(rule) / 12


def _days_in_year(date: datetime.date) -> int:
    return 366 if calendar.isleap(date.year) else 365


def _floor(value: Decimal | int) -> int:
    return int(Decimal(value).to_integral_value(ROUND_FLOOR))
