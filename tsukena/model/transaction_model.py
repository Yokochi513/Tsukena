import datetime
from dataclasses import dataclass

from .charge_model import Charge
from .enum.payment_plan import PaymentPlan
from .enum.source import Source
from .enum.status import Status


@dataclass(frozen=True)
class Transaction:
    id: int
    occurred_date: datetime.date
    occurred_time: datetime.time | None
    paid_date: datetime.date
    amount: int
    merchant: str
    merchant_key: str
    memo: str
    category_id: int | None
    status: Status
    payment_method: str
    source: Source
    source_ref: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    # 1回払い以外では、paid_date は1回払いだったときの支払日で、引き落としの予定（charges）の起点になる（→ docs/adr/0011）
    payment_plan: PaymentPlan = PaymentPlan.LUMP
    plan_count: int | None = None  # skip なら繰り延べる月数、installment なら回数
    charges: tuple[Charge, ...] = ()  # 1回払いでは空

    def effective_charges(self) -> tuple[Charge, ...]:
        """実際の引き落としの予定。1回払いなら、支払日に金額の全部を1回で引き落とす"""
        if self.payment_plan == PaymentPlan.LUMP:
            return (
                Charge(seq=1, paid_date=self.paid_date, principal=self.amount, fee=0),
            )
        return self.charges


@dataclass(frozen=True)
class TransactionInput:
    occurred_date: datetime.date
    occurred_time: datetime.time | None
    paid_date: datetime.date
    amount: int
    merchant: str
    merchant_key: str
    memo: str
    category_id: int | None
    status: Status
    payment_method: str
    source: Source
    source_ref: str


@dataclass(frozen=True)
class TransactionUpdate:
    # None は「変えない」を表す。カテゴリを未設定に戻す指示は表せない
    occurred_date: datetime.date | None = None
    paid_date: datetime.date | None = None
    amount: int | None = None
    merchant: str | None = None
    memo: str | None = None
    category_id: int | None = None
