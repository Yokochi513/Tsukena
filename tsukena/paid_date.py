import calendar
import datetime

from .model.enum.payment_timing import PaymentTiming
from .model.payment_rule_model import PaymentRule


def calculate_paid_date(
    occurred_date: datetime.date, rule: PaymentRule
) -> datetime.date:
    """利用日と支払い手段の締め日のルールから、支払日を計算する（→ docs/design.md 7.1）。

    - 即時なら利用日と同じ日
    - カードなら、利用日を含む締め期間の締め日の月から、何か月後かの引き落とし日。
      締め期間は「前の締め日の翌日〜締め日」とする
    - 締め日・引き落とし日がその月に無い日（2月30日など）のときは、その月の末日とする
    - 土日祝による繰り延べはしない（→ 残課題 R-10）
    """
    if rule.timing == PaymentTiming.IMMEDIATE:
        return occurred_date

    assert rule.closing_day is not None
    assert rule.withdrawal_day is not None
    assert rule.withdrawal_month_offset is not None

    year, month = occurred_date.year, occurred_date.month
    if occurred_date.day > _day_in_month(year, month, rule.closing_day):
        # その月の締め日より後の利用は、翌月の締めになる
        year, month = _add_months(year, month, 1)

    year, month = _add_months(year, month, rule.withdrawal_month_offset)
    return datetime.date(year, month, _day_in_month(year, month, rule.withdrawal_day))


def _day_in_month(year: int, month: int, day: int) -> int:
    """その月に無い日は、その月の末日に読み替える"""
    return min(day, calendar.monthrange(year, month)[1])


def _add_months(year: int, month: int, months: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + months
    return index // 12, index % 12 + 1
