import sqlite3

from ..model.category_model import Category
from ..model.summary_model import CategoryTotal, MonthlySummary
from .setting_repository import fetch_setting


def fetch_monthly_summary(conn: sqlite3.Connection, month: str) -> MonthlySummary:
    """month（YYYY-MM）の集計。支出は支払日、収入は入金日で月を決める（→ docs/adr/0004）"""
    # 日付は YYYY-MM-DD の文字列なので、月初〜31日の範囲で比べれば月の判定になり、インデックスも使える
    first, last = f"{month}-01", f"{month}-31"

    # 確認待ちの記録は、カテゴリが付いていても未分類の1件にまとめる（→ docs/module/model_design.md の CategoryTotal）
    rows = conn.execute(
        """
        SELECT c.id, c.name, c.emoji, c.sort_order, SUM(t.amount) AS amount
        FROM transactions t
        LEFT JOIN categories c
          ON t.status = 'confirmed' AND c.id = t.category_id
        WHERE t.paid_date BETWEEN ? AND ?
        GROUP BY c.id
        ORDER BY c.id IS NULL, amount DESC, c.sort_order
        """,
        (first, last),
    ).fetchall()
    by_category = tuple(
        CategoryTotal(
            category=(
                Category(
                    id=r["id"],
                    name=r["name"],
                    emoji=r["emoji"],
                    sort_order=r["sort_order"],
                )
                if r["id"] is not None
                else None
            ),
            amount=r["amount"],
        )
        for r in rows
    )

    income_total = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM incomes WHERE received_date BETWEEN ? AND ?",
        (first, last),
    ).fetchone()[0]
    total = sum(c.amount for c in by_category)
    budget = fetch_setting(conn).monthly_budget
    return MonthlySummary(
        month=month,
        income_total=income_total,
        total=total,
        balance=income_total - total,
        budget=budget,
        remaining=budget - total,
        by_category=by_category,
    )
