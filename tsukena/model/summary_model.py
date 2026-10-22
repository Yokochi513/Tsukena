from dataclasses import dataclass

from .category_model import Category


@dataclass(frozen=True)
class CategoryTotal:
    category: Category | None  # カテゴリが未設定（確認待ち）の記録の合計なら None
    amount: int


@dataclass(frozen=True)
class MonthlySummary:
    month: str  # YYYY-MM
    income_total: int
    total: int
    balance: int  # 収入合計 - 支出合計。負の数がありうる
    budget: int
    remaining: int  # 予算 - 支出合計。予算を超えていれば負の数
    by_category: tuple[CategoryTotal, ...]
