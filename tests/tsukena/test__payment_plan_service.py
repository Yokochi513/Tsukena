import sqlite3
from pathlib import Path

import pytest

from tsukena.model.enum.payment_plan import PaymentPlan
from tsukena.model.transaction_model import TransactionUpdate
from tsukena.repositories.database import migrate
from tsukena.repositories.summary_repository import fetch_monthly_summary
from tsukena.repositories.transaction_repository import (
    fetch_transaction,
    fetch_transactions,
)
from tsukena.services.payment_plan_service import (
    FeeNotEditableError,
    InvalidPlanCountError,
    PlanNotAvailableError,
    change_payment_plan,
    fetch_revolving,
    set_charge_fee,
    set_revolving_fee,
)
from tsukena.services.transaction_service import delete_transaction, modify_transaction

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"


@pytest.fixture
def conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript((SQL_DIR / "create_tables.sql").read_text(encoding="utf-8"))
    for name in ["sample/01_categories.sql", "sample/02_settings.sql"]:
        conn.executescript((SQL_DIR / name).read_text(encoding="utf-8"))
    return conn


def _add_jcb(
    conn: sqlite3.Connection,
    amount: int,
    paid_date: str = "2026-11-10",
    category_id: int = 2,
) -> int:
    """JCB で 10/20 に使い、11/10 に1回払いで引き落とす支出を足す"""
    cur = conn.execute(
        """
        INSERT INTO transactions
            (occurred_date, paid_date, amount, merchant, merchant_key, category_id, status,
             payment_method, source, source_ref, created_at, updated_at)
        VALUES ('2026-10-20', ?, ?, '家電', '家電', ?, 'confirmed', 'JCBカード', 'gmail', ?,
                '2026-10-20T10:00:00+09:00', '2026-10-20T10:00:00+09:00')
        """,
        (paid_date, amount, category_id, f"gmail:test{conn.total_changes}:0"),
    )
    conn.commit()
    return cur.lastrowid


def test_分割払いにすると_月の支出はその月の引き落とし額になる(conn):
    tid = _add_jcb(conn, 100000)

    t = change_payment_plan(conn, tid, PaymentPlan.INSTALLMENT, 10)

    assert t.payment_plan == PaymentPlan.INSTALLMENT
    assert len(t.charges) == 10
    assert fetch_monthly_summary(conn, "2026-11").total == 10625
    assert fetch_monthly_summary(conn, "2026-12").total == 10843
    # 手数料も元の支出のカテゴリに入る
    assert fetch_monthly_summary(conn, "2026-12").by_category[0].category.id == 2
    # 引き落としのある月の明細に出る
    assert [x.id for x in fetch_transactions(conn, month="2027-08")] == [tid]
    assert fetch_transactions(conn, month="2027-09") == []


def test_1回払いに戻すと_支払日に金額の全部を数える(conn):
    tid = _add_jcb(conn, 100000)
    change_payment_plan(conn, tid, PaymentPlan.INSTALLMENT, 10)

    t = change_payment_plan(conn, tid, PaymentPlan.LUMP)

    assert t.charges == ()
    assert t.plan_count is None
    assert fetch_monthly_summary(conn, "2026-11").total == 100000
    assert fetch_monthly_summary(conn, "2026-12").total == 0
    assert conn.execute("SELECT count(*) FROM charges").fetchone()[0] == 0


def test_スキップ払いにすると_送った月に手数料込みで数える(conn):
    tid = _add_jcb(conn, 10000)

    change_payment_plan(conn, tid, PaymentPlan.SKIP, 3)

    assert fetch_monthly_summary(conn, "2026-11").total == 0
    assert fetch_monthly_summary(conn, "2027-02").total == 10450


def test_回数が無いか範囲の外なら_InvalidPlanCountErrorを投げる(conn):
    tid = _add_jcb(conn, 10000)
    with pytest.raises(InvalidPlanCountError):
        change_payment_plan(conn, tid, PaymentPlan.INSTALLMENT)
    with pytest.raises(InvalidPlanCountError):
        change_payment_plan(conn, tid, PaymentPlan.SKIP, 7)
    assert fetch_transaction(conn, tid).payment_plan == PaymentPlan.LUMP


def test_手数料率の無い支払い手段は_支払い方法を変えられない(conn):
    tid = _add_jcb(conn, 10000)
    conn.execute("UPDATE transactions SET payment_method = '現金' WHERE id = ?", (tid,))
    with pytest.raises(PlanNotAvailableError):
        change_payment_plan(conn, tid, PaymentPlan.INSTALLMENT, 3)


def test_分割払いの手数料を直すと_その回の額が変わり_戻せる(conn):
    tid = _add_jcb(conn, 100000)
    change_payment_plan(conn, tid, PaymentPlan.INSTALLMENT, 10)

    t = set_charge_fee(conn, tid, 1, 1300)
    assert (t.charges[0].fee, t.charges[0].fee_edited) == (1300, True)
    assert fetch_monthly_summary(conn, "2026-11").total == 9343 + 1300

    t = set_charge_fee(conn, tid, 1, None)
    assert (t.charges[0].amount, t.charges[0].fee_edited) == (10625, False)


def test_リボ払いは_同じカードのリボをまとめて計算する(conn):
    first = _add_jcb(conn, 70000)
    change_payment_plan(conn, first, PaymentPlan.REVOLVING)
    assert fetch_monthly_summary(conn, "2026-11").total == 10897

    second = _add_jcb(conn, 30000, category_id=1)
    change_payment_plan(conn, second, PaymentPlan.REVOLVING)

    months = fetch_revolving(conn, "JCBカード")
    assert months[0].principal == 10000
    assert months[-1].balance == 0
    assert sum(m.principal for m in months) == 100000
    # 月の集計は、リボ全体の弁済金と一致する
    for m in months:
        assert fetch_monthly_summary(conn, m.month).total == m.principal + m.fee


def test_リボの手数料を月で直すと_集計に入る(conn):
    tid = _add_jcb(conn, 70000)
    change_payment_plan(conn, tid, PaymentPlan.REVOLVING)

    months = set_revolving_fee(conn, "JCBカード", "2026-11", 900)

    assert (months[0].fee, months[0].fee_edited) == (900, True)
    assert fetch_monthly_summary(conn, "2026-11").total == 10900
    with pytest.raises(FeeNotEditableError):
        set_charge_fee(conn, tid, 1, 0)


def test_リボの支出を消すと_残りのリボを計算し直す(conn):
    first = _add_jcb(conn, 5000)
    second = _add_jcb(conn, 30000)
    change_payment_plan(conn, first, PaymentPlan.REVOLVING)
    change_payment_plan(conn, second, PaymentPlan.REVOLVING)

    assert delete_transaction(conn, first)

    months = fetch_revolving(conn, "JCBカード")
    assert sum(m.principal for m in months) == 30000
    assert (
        fetch_monthly_summary(conn, "2026-11").total
        == months[0].principal + months[0].fee
    )


def test_金額を直すと_引き落としの予定を作り直す(conn):
    tid = _add_jcb(conn, 100000)
    change_payment_plan(conn, tid, PaymentPlan.INSTALLMENT, 10)
    set_charge_fee(conn, tid, 1, 0)

    t = modify_transaction(conn, tid, TransactionUpdate(amount=50000))

    assert sum(c.principal for c in t.charges) == 50000
    assert not any(c.fee_edited for c in t.charges)


def test_メモだけを直しても_手で直した手数料は残る(conn):
    tid = _add_jcb(conn, 100000)
    change_payment_plan(conn, tid, PaymentPlan.INSTALLMENT, 10)
    set_charge_fee(conn, tid, 1, 0)

    t = modify_transaction(conn, tid, TransactionUpdate(memo="冷蔵庫"))

    assert t.charges[0].fee_edited


def test_支払い方法の列が無いDBに_列と表を足す():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE settings (id INTEGER PRIMARY KEY, full_import_done INTEGER);
        CREATE TABLE transactions (id INTEGER PRIMARY KEY, memo TEXT);
        INSERT INTO transactions (id, memo) VALUES (1, '');
        """
    )

    migrate(conn)
    migrate(conn)  # 2度呼んでも同じ

    row = conn.execute("SELECT payment_plan, plan_count FROM transactions").fetchone()
    assert (row["payment_plan"], row["plan_count"]) == ("lump", None)
    tables = {
        r[0]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert {"charges", "revolving_fees"} <= tables


def test_リボの支出が無くなると_直した手数料も消す(conn):
    tid = _add_jcb(conn, 70000)
    change_payment_plan(conn, tid, PaymentPlan.REVOLVING)
    set_revolving_fee(conn, "JCBカード", "2026-11", 900)

    change_payment_plan(conn, tid, PaymentPlan.LUMP)

    assert conn.execute("SELECT count(*) FROM revolving_fees").fetchone()[0] == 0
