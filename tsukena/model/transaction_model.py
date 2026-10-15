import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class Transaction:
    id: int
    occurred_date: datetime.date
    occurred_time: datetime.time | None
    paid_date: datetime.date
    amount: int
    merchant: str
    merchant_key: str
    category_id: int
    status: str
    payment_method: str
    source: str
    source_ref: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
