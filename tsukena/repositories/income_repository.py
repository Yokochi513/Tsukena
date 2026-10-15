import datetime
import sqlite3

from ..model.income_model import Income, IncomeInput

JST = datetime.timezone(datetime.timedelta(hours=9), "JST")


def insert_income(conn: sqlite3.Connection, income: IncomeInput) -> Income:
    now = datetime.datetime.now(JST)
    cur = conn.execute(
        "INSERT INTO incomes (received_date, amount, memo, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (
            income.received_date.isoformat(),
            income.amount,
            income.memo,
            now.isoformat(),
            now.isoformat(),
        ),
    )
    conn.commit()

    assert cur.lastrowid is not None
    return Income(
        id=cur.lastrowid,
        received_date=income.received_date,
        amount=income.amount,
        memo=income.memo,
        created_at=now,
        updated_at=now,
    )


def fetch_incomes(conn: sqlite3.Connection) -> list[Income]:
    rows = conn.execute("SELECT * FROM incomes").fetchall()
    return [_row_to_income(r) for r in rows]


def _row_to_income(row: sqlite3.Row) -> Income:
    return Income(
        id=row["id"],
        received_date=datetime.date.fromisoformat(row["received_date"]),
        amount=row["amount"],
        memo=row["memo"],
        created_at=datetime.datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.datetime.fromisoformat(row["updated_at"]),
    )
