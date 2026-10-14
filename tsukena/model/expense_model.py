import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class Expense:
    Id: int
    occurred_date: datetime.date
    occurred_time: datetime.time | None
    merchant: str
    payment_method: str
    amount: float
