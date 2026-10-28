import datetime
import sqlite3

from ..model.charge_model import Charge
from ..model.enum.payment_plan import PaymentPlan
from ..payment_plan import RevolvingItem


def fetch_charges(
    conn: sqlite3.Connection, transaction_ids: list[int]
) -> dict[int, tuple[Charge, ...]]:
    """支出ごとの引き落とし（回の順）。1回払いの支出は charges に行を持たないので、結果にも入らない"""
    if not transaction_ids:
        return {}
    placeholders = ", ".join("?" * len(transaction_ids))
    rows = conn.execute(
        f"""
        SELECT * FROM charges
        WHERE transaction_id IN ({placeholders})
        ORDER BY transaction_id, seq
        """,
        transaction_ids,
    ).fetchall()
    result: dict[int, list[Charge]] = {}
    for r in rows:
        result.setdefault(r["transaction_id"], []).append(
            Charge(
                seq=r["seq"],
                paid_date=datetime.date.fromisoformat(r["paid_date"]),
                principal=r["principal"],
                fee=r["fee"],
                fee_edited=bool(r["fee_edited"]),
            )
        )
    return {tid: tuple(c) for tid, c in result.items()}


def replace_charges(
    conn: sqlite3.Connection, transaction_id: int, charges: tuple[Charge, ...]
) -> None:
    # 支払い方法の変更と同じ単位で確定させたいため、commit は呼び出す側が行う
    conn.execute("DELETE FROM charges WHERE transaction_id = ?", (transaction_id,))
    conn.executemany(
        """
        INSERT INTO charges (transaction_id, seq, paid_date, principal, fee, fee_edited)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                transaction_id,
                c.seq,
                c.paid_date.isoformat(),
                c.principal,
                c.fee,
                int(c.fee_edited),
            )
            for c in charges
        ],
    )


def fetch_revolving_items(
    conn: sqlite3.Connection, payment_method: str
) -> list[RevolvingItem]:
    rows = conn.execute(
        "SELECT id, amount, paid_date FROM transactions WHERE payment_plan = ? AND payment_method = ?",
        (PaymentPlan.REVOLVING.value, payment_method),
    ).fetchall()
    return [
        RevolvingItem(
            transaction_id=r["id"],
            amount=r["amount"],
            paid_date=datetime.date.fromisoformat(r["paid_date"]),
        )
        for r in rows
    ]


def fetch_revolving_fees(
    conn: sqlite3.Connection, payment_method: str
) -> dict[str, int]:
    """手で直したリボの手数料（YYYY-MM → 円）"""
    rows = conn.execute(
        "SELECT month, fee FROM revolving_fees WHERE payment_method = ?",
        (payment_method,),
    ).fetchall()
    return {r["month"]: r["fee"] for r in rows}


def upsert_revolving_fee(
    conn: sqlite3.Connection, payment_method: str, month: str, fee: int
) -> None:
    conn.execute(
        """
        INSERT INTO revolving_fees (payment_method, month, fee) VALUES (?, ?, ?)
        ON CONFLICT (payment_method, month) DO UPDATE SET fee = excluded.fee
        """,
        (payment_method, month, fee),
    )


def delete_revolving_fee(
    conn: sqlite3.Connection, payment_method: str, month: str
) -> None:
    conn.execute(
        "DELETE FROM revolving_fees WHERE payment_method = ? AND month = ?",
        (payment_method, month),
    )


def delete_revolving_fees(conn: sqlite3.Connection, payment_method: str) -> None:
    conn.execute(
        "DELETE FROM revolving_fees WHERE payment_method = ?", (payment_method,)
    )
