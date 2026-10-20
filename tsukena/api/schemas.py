import datetime

from pydantic import AwareDatetime, BaseModel, Field, field_serializer, field_validator

from ..model.category_model import Category, CategoryInput
from ..model.enum.record_outcome import RecordOutcome
from ..model.enum.source import Source
from ..model.enum.status import Status
from ..model.import_failure_model import ImportFailure
from ..model.income_model import Income, IncomeInput
from ..model.record_model import RecordResult
from ..model.transaction_model import Transaction, TransactionUpdate


class TransactionOut(BaseModel):
    # merchant_key と source_ref はサーバーの内部でだけ使うため返さない
    id: int
    occurred_date: datetime.date
    occurred_time: datetime.time | None
    paid_date: datetime.date
    amount: int
    merchant: str
    memo: str
    category_id: int | None
    status: Status
    payment_method: str
    source: Source
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @field_serializer("occurred_time")
    def _serialize_occurred_time(self, t: datetime.time | None) -> str | None:
        # time をそのまま返すと "12:30:00" になるため、API の約束どおり HH:MM にする
        return t.strftime("%H:%M") if t is not None else None

    @classmethod
    def from_model(cls, t: Transaction) -> "TransactionOut":
        return cls(
            id=t.id,
            occurred_date=t.occurred_date,
            occurred_time=t.occurred_time,
            paid_date=t.paid_date,
            amount=t.amount,
            merchant=t.merchant,
            memo=t.memo,
            category_id=t.category_id,
            status=t.status,
            payment_method=t.payment_method,
            source=t.source,
            created_at=t.created_at,
            updated_at=t.updated_at,
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


class TransactionUpdateIn(BaseModel):
    # すべて省略可。送らなかった項目は変えない
    occurred_date: datetime.date | None = None
    paid_date: datetime.date | None = None
    amount: int | None = Field(None, ge=1)
    merchant: str | None = None
    memo: str | None = None
    category_id: int | None = None

    @field_validator("category_id")
    @classmethod
    def _reject_null_category(cls, v: int | None) -> int | None:
        # 省略したときは呼ばれず、null を明示したときだけ呼ばれる。確定の記録を確認待ちに戻す経路は持たない
        if v is None:
            raise ValueError("category_id に null は指定できません")
        return v

    def to_model(self) -> TransactionUpdate:
        return TransactionUpdate(
            occurred_date=self.occurred_date,
            paid_date=self.paid_date,
            amount=self.amount,
            merchant=self.merchant,
            memo=self.memo,
            category_id=self.category_id,
        )


class CashRecordIn(BaseModel):
    text: str  # 加工せずに受け取る。分解はサーバーが行う
    message_id: str = Field(pattern=r"^[0-9]+$")
    sent_at: AwareDatetime  # タイムゾーンが無ければ 422 にする


class RecordResultOut(BaseModel):
    outcome: RecordOutcome
    transaction: TransactionOut | None
    category: CategoryOut | None
    # TODO: budget モジュールができたら、予算の状態を返す（→ docs/api_list.md 2.8）
    budget: None = None

    @classmethod
    def from_model(cls, r: RecordResult) -> "RecordResultOut":
        return cls(
            outcome=r.outcome,
            transaction=TransactionOut.from_model(r.transaction)
            if r.transaction is not None
            else None,
            category=CategoryOut.from_model(r.category)
            if r.category is not None
            else None,
        )


class GoogleAuthStartOut(BaseModel):
    authorization_url: str


class ImportFailureOut(BaseModel):
    # 本文は持たないので返さない（→ docs/api_list.md 2.6）
    message_id: str
    sender: str
    subject: str
    reason: str
    failed_at: datetime.datetime

    @classmethod
    def from_model(cls, f: ImportFailure) -> "ImportFailureOut":
        return cls(
            message_id=f.message_id,
            sender=f.sender,
            subject=f.subject,
            reason=f.reason,
            failed_at=f.failed_at,
        )


class ImportRetryOut(BaseModel):
    recorded: int  # 取り込み直して新しく記録した支払いの件数
