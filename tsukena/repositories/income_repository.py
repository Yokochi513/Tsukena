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


def update_income(
    conn: sqlite3.Connection, income_id: int, update: IncomeInput
) -> Income | None:
    row = conn.execute("SELECT * FROM incomes WHERE id = ?", (income_id,)).fetchone()
    if row is None:
        return None
    current = _row_to_income(row)

    now = datetime.datetime.now(JST)
    updated = Income(
        id=current.id,
        received_date=update.received_date
        if update.received_date is not None
        else current.received_date,
        amount=update.amount if update.amount is not None else current.amount,
        memo=update.memo if update.memo is not None else current.memo,
        created_at=current.created_at,
        updated_at=now,
    )

    conn.execute(
        "UPDATE incomes SET received_date = ?, amount = ?, memo = ?, updated_at = ? WHERE id = ?",
        (
            updated.received_date.isoformat(),
            updated.amount,
            updated.memo,
            now.isoformat(),
            income_id,
        ),
    )
    conn.commit()
    return updated


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
