import datetime
import sqlite3

from ..model.expense_model import Expense


def _row_to_expense(row: sqlite3.Row) -> Expense:
    t = row["occurred_time"]
    return Expense(
        id=row["id"],
        occurred_date=datetime.date.fromisoformat(row["occurred_date"]),
        occurred_time=datetime.time.fromisoformat(t) if t is not None else None,
        merchant=row["merchant"],
        payment_method=row["payment_method"],
        amount=row["amount"],
    )


def list_expenses(conn: sqlite3.Connection) -> list[Expense]:
    rows = conn.execute("SELECT * FROM expenses").fetchall()
    return [_row_to_expense(r) for r in rows]
