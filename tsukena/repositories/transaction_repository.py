import dataclasses
import datetime
import sqlite3

from ..model.enum.payment_plan import PaymentPlan
from ..model.enum.source import Source
from ..model.enum.status import Status
from ..model.transaction_model import Transaction, TransactionInput
from ..normalize import normalize
from .charge_repository import fetch_charges


def fetch_transactions(
    conn: sqlite3.Connection,
    month: str | None = None,
    status: Status | None = None,
    source_ref: str | None = None,
    q: str | None = None,
) -> list[Transaction]:
    conditions: list[str] = []
    params: list[str] = []
    if month is not None:
        # month は YYYY-MM。日付は YYYY-MM-DD の文字列なので、月初〜31日の範囲で比べれば月の判定になり、インデックスも使える。
        # 1回払いは支払日で、ほかの支払い方法はその月に引き落としがあるかで決める（→ docs/adr/0011）
        conditions.append(
            """(
                (payment_plan = 'lump' AND paid_date BETWEEN ? AND ?)
                OR id IN (SELECT transaction_id FROM charges WHERE paid_date BETWEEN ? AND ?)
            )"""
        )
        params += [f"{month}-01", f"{month}-31"] * 2
    if status is not None:
        conditions.append("status = ?")
        params.append(status.value)
    if source_ref is not None:
        # bot がリアクションの付いた返事から記録を探すときに使う。一意なので0件か1件になる
        conditions.append("source_ref = ?")
        params.append(source_ref)
    if q is not None and (key := normalize(q)) != "":
        # 店名は分類ルールと同じ正規化をしたキー（merchant_key）で比べ、表記の揺れ（全角・大文字・空白）を吸収する。
        # メモは正規化したキーを持たないので、照合のときに同じ規則で正規化する。
        # LIKE だと検索語の % や _ が特別な意味を持つため、instr で部分一致を見る
        conn.create_function("normalize", 1, normalize, deterministic=True)
        conditions.append(
            "(instr(merchant_key, ?) > 0 OR instr(normalize(memo), ?) > 0)"
        )
        params += [key, key]

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
    return _with_charges(conn, [_row_to_transaction(r) for r in rows])


def fetch_transaction(
    conn: sqlite3.Connection, transaction_id: int
) -> Transaction | None:
    row = conn.execute(
        "SELECT * FROM transactions WHERE id = ?", (transaction_id,)
    ).fetchone()
    if row is None:
        return None
    return _with_charges(conn, [_row_to_transaction(row)])[0]


def insert_transaction(
    conn: sqlite3.Connection, t: TransactionInput, now: datetime.datetime
) -> Transaction:
    # 重複の確認と同じ単位で確定させたいため、commit は呼び出す側が行う
    cur = conn.execute(
        """
        INSERT INTO transactions (
            occurred_date, occurred_time, paid_date, amount, merchant, merchant_key,
            memo, category_id, status, payment_method, source, source_ref,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            t.occurred_date.isoformat(),
            t.occurred_time.strftime("%H:%M") if t.occurred_time is not None else None,
            t.paid_date.isoformat(),
            t.amount,
            t.merchant,
            t.merchant_key,
            t.memo,
            t.category_id,
            t.status.value,
            t.payment_method,
            t.source.value,
            t.source_ref,
            now.isoformat(),
            now.isoformat(),
        ),
    )
    return Transaction(id=cur.lastrowid, created_at=now, updated_at=now, **vars(t))


def source_ref_exists(conn: sqlite3.Connection, source_ref: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM transactions WHERE source_ref = ?", (source_ref,)
    ).fetchone()
    return row is not None


def deleted_ref_exists(conn: sqlite3.Connection, source_ref: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM deleted_refs WHERE source_ref = ?", (source_ref,)
    ).fetchone()
    return row is not None


def gmail_message_recorded(conn: sqlite3.Connection, message_id: str) -> bool:
    """メール1通から作った記録が1件でもあるか。重複排除キーは gmail:{message_id}:{連番}"""
    prefix = _gmail_ref_prefix(message_id)
    row = conn.execute(
        "SELECT 1 FROM transactions WHERE substr(source_ref, 1, ?) = ?",
        (len(prefix), prefix),
    ).fetchone()
    return row is not None


def gmail_message_deleted(conn: sqlite3.Connection, message_id: str) -> bool:
    """メール1通から作った記録を、1件でも削除したことがあるか"""
    prefix = _gmail_ref_prefix(message_id)
    row = conn.execute(
        "SELECT 1 FROM deleted_refs WHERE substr(source_ref, 1, ?) = ?",
        (len(prefix), prefix),
    ).fetchone()
    return row is not None


def _gmail_ref_prefix(message_id: str) -> str:
    # LIKE は _ と % を特別に扱い、英字の大文字・小文字も区別しないため、先頭の部分を完全一致で比べる
    return f"{Source.GMAIL}:{message_id}:"


def update_transaction(conn: sqlite3.Connection, t: Transaction) -> None:
    # 分類ルールの学習と同じ単位で確定させたいため、commit は呼び出す側が行う
    conn.execute(
        """
        UPDATE transactions
        SET occurred_date = ?, paid_date = ?, amount = ?, merchant = ?,
            merchant_key = ?, memo = ?, category_id = ?, status = ?,
            payment_plan = ?, plan_count = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            t.occurred_date.isoformat(),
            t.paid_date.isoformat(),
            t.amount,
            t.merchant,
            t.merchant_key,
            t.memo,
            t.category_id,
            t.status.value,
            t.payment_plan.value,
            t.plan_count,
            t.updated_at.isoformat(),
            t.id,
        ),
    )


def remove_transaction(conn: sqlite3.Connection, transaction_id: int) -> bool:
    # 重複排除キーを残し、同じメッセージやメールから記録が復活しないようにする（→ docs/api_list.md 2.2）。
    # リボ払いの支出を消したときの、残りのリボの引き落としの計算し直しは呼び出す側が行う
    with conn:
        conn.execute("DELETE FROM charges WHERE transaction_id = ?", (transaction_id,))
        conn.execute(
            """
            INSERT OR IGNORE INTO deleted_refs (source_ref)
            SELECT source_ref FROM transactions WHERE id = ?
            """,
            (transaction_id,),
        )
        cur = conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    return cur.rowcount > 0


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
        memo=row["memo"],
        category_id=row["category_id"],
        status=Status(row["status"]),
        payment_method=row["payment_method"],
        source=Source(row["source"]),
        source_ref=row["source_ref"],
        created_at=datetime.datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.datetime.fromisoformat(row["updated_at"]),
        payment_plan=PaymentPlan(row["payment_plan"]),
        plan_count=row["plan_count"],
    )


def _with_charges(
    conn: sqlite3.Connection, transactions: list[Transaction]
) -> list[Transaction]:
    ids = [t.id for t in transactions if t.payment_plan != PaymentPlan.LUMP]
    charges = fetch_charges(conn, ids)
    return [
        dataclasses.replace(t, charges=charges[t.id]) if t.id in charges else t
        for t in transactions
    ]
