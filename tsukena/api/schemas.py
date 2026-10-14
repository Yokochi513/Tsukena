import datetime

from pydantic import BaseModel

from ..model.expense_model import Expense


class ExpenseOut(BaseModel):
    id: int
    occurred_date: datetime.date
    occurred_time: datetime.time | None
    merchant: str
    payment_method: str
    amount: float

    @classmethod
    def from_model(cls, e: Expense) -> "ExpenseOut":
        return cls(
            id=e.id,
            occurred_date=e.occurred_date,
            occurred_time=e.occurred_time,
            merchant=e.merchant,
            payment_method=e.payment_method,
            amount=e.amount,
        )
