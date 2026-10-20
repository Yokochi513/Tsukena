from dataclasses import dataclass

from .enum.payment_timing import PaymentTiming


@dataclass(frozen=True)
class PaymentRule:
    payment_method: str
    timing: PaymentTiming
    closing_day: int | None = None  # 31 は月末を表す。即時なら None
    withdrawal_day: int | None = None  # 31 は月末を表す。即時なら None
    withdrawal_month_offset: int | None = None  # 即時なら None
