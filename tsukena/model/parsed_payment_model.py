import datetime
from dataclasses import dataclass

from .enum.source import Source


@dataclass(frozen=True)
class ParsedPayment:
    occurred_date: datetime.date
    occurred_time: datetime.time | None
    amount: int
    merchant: str
    payment_method: str
    source: Source
    source_ref: str
