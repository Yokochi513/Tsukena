from dataclasses import dataclass

from .category_model import Category
from .enum.record_outcome import RecordOutcome
from .transaction_model import Transaction


# TODO: budget モジュールができたら、予算の状態（BudgetStatus）を持たせる（→ docs/api_list.md 2.8）
@dataclass(frozen=True)
class RecordResult:
    outcome: RecordOutcome
    transaction: Transaction | None = None  # 記録しなかったときは None
    category: Category | None = None  # 記録しなかったとき、カテゴリが未設定のときは None
