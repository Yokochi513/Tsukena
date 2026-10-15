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
