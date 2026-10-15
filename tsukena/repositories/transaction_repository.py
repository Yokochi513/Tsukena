import datetime
import sqlite3

from ..model.enum.source import Source
from ..model.enum.status import Status
from ..model.transaction_model import Transaction


def fetch_transactions(
    conn: sqlite3.Connection,
    month: str | None = None,
    status: Status | None = None,
) -> list[Transaction]:
    conditions: list[str] = []
    params: list[str] = []
    if month is not None:
        # month は YYYY-MM。日付は YYYY-MM-DD の文字列なので、月初〜31日の範囲で比べれば月の判定になり、インデックスも使える
        conditions.append("paid_date BETWEEN ? AND ?")
        params += [f"{month}-01", f"{month}-31"]
    if status is not None:
        conditions.append("status = ?")
        params.append(status.value)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = conn.execute(
        f"""
        SELECT * FROM transactions
        {where}
        ORDER BY occurred_date DESC,
                 occurred_time IS NULL,
                 occurred_time DESC,
                 id DESC
        """,
        params,
    ).fetchall()
    return [_row_to_transaction(r) for r in rows]


def _row_to_transaction(row: sqlite3.Row) -> Transaction:
    t = row["occurred_time"]
    return Transaction(
        id=row["id"],
        occurred_date=datetime.date.fromisoformat(row["occurred_date"]),
        occurred_time=datetime.time.fromisoformat(t) if t is not None else None,
        paid_date=datetime.date.fromisoformat(row["paid_date"]),
        amount=row["amount"],
        merchant=row["merchant"],
        merchant_key=row["merchant_key"],
        category_id=row["category_id"],
        status=Status(row["status"]),
        payment_method=row["payment_method"],
        source=Source(row["source"]),
        source_ref=row["source_ref"],
        created_at=datetime.datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.datetime.fromisoformat(row["updated_at"]),
    )
