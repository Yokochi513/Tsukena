import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class Income:
    id: int
    received_date: datetime.date
    amount: int
    memo: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


@dataclass(frozen=True)
class IncomeInput:
    received_date: datetime.date
    amount: int
    memo: str
