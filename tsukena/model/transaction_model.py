import datetime
from dataclasses import dataclass

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
    category_id: int | None
    status: Status
    payment_method: str
    source: Source
    source_ref: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


@dataclass(frozen=True)
class TransactionInput:
    occurred_date: datetime.date
    occurred_time: datetime.time | None
    paid_date: datetime.date
    amount: int
    merchant: str
    merchant_key: str
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
    category_id: int | None = None
