import datetime

from pydantic import BaseModel, Field

from ..model.category_model import Category, CategoryInput
from ..model.expense_model import Expense
from ..model.income_model import Income, IncomeInput


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


class IncomeIn(BaseModel):
    received_date: datetime.date
    amount: int = Field(ge=1)
    memo: str = ""

    def to_model(self) -> IncomeInput:
        return IncomeInput(
            received_date=self.received_date, amount=self.amount, memo=self.memo
        )


class IncomeOut(BaseModel):
    id: int
    received_date: datetime.date
    amount: int
    memo: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @classmethod
    def from_model(cls, i: Income) -> "IncomeOut":
        return cls(
            id=i.id,
            received_date=i.received_date,
            amount=i.amount,
            memo=i.memo,
            created_at=i.created_at,
            updated_at=i.updated_at,
        )


class CategoryIn(BaseModel):
    name: str
    emoji: str
    sort_order: int

    def to_model(self) -> CategoryInput:
        return CategoryInput(
            name=self.name,
            emoji=self.emoji,
            sort_order=self.sort_order,
        )


class CategoryOut(BaseModel):
    id: int
    name: str
    emoji: str
    sort_order: int

    @classmethod
    def from_model(cls, i: Category) -> "CategoryOut":
        return cls(
            id=i.id,
            name=i.name,
            emoji=i.emoji,
            sort_order=i.sort_order,
        )
