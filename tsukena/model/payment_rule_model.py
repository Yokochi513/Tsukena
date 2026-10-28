from dataclasses import dataclass

from .enum.payment_timing import PaymentTiming


@dataclass(frozen=True)
class PaymentRule:
    payment_method: str
    timing: PaymentTiming
    closing_day: int | None = None  # 31 は月末を表す。即時なら None
    withdrawal_day: int | None = None  # 31 は月末を表す。即時なら None
    withdrawal_month_offset: int | None = None  # 即時なら None
    # スキップ・分割・リボ払いの手数料の実質年率（%）。書いていないカードでは支払い方法を変えられない
    fee_rate: float | None = None
    # リボ払いの毎月の元金（定額コース）。書いていないカードではリボにできない
    revolving_principal: int | None = None
