import sqlite3
from pathlib import Path

import pytest

from tsukena.model.enum.status import Status
from tsukena.model.transaction_model import TransactionUpdate
from tsukena.repositories.transaction_repository import fetch_transaction
from tsukena.services.transaction_service import modify_transaction

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"


@pytest.fixture
def conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript((SQL_DIR / "create_tables.sql").read_text(encoding="utf-8"))
    for name in ["sample/01_categories.sql", "sample/04_transactions.sql"]:
        conn.executescript((SQL_DIR / name).read_text(encoding="utf-8"))
    return conn


def _pending_id(conn: sqlite3.Connection) -> int:
    return conn.execute(
        "SELECT id FROM transactions WHERE status = 'pending' LIMIT 1"
    ).fetchone()[0]


def test_メモだけを書くと_メモだけが変わる(conn):
    transaction_id = _pending_id(conn)
    before = fetch_transaction(conn, transaction_id)

    modify_transaction(conn, transaction_id, TransactionUpdate(memo="USB ケーブル"))

    after = fetch_transaction(conn, transaction_id)
    assert after.memo == "USB ケーブル"
    # メモは分類に使わないため、確認待ちのまま残り、分類ルールも作らない
    assert after.status == Status.PENDING
    assert after.merchant_key == before.merchant_key
    assert conn.execute("SELECT count(*) FROM merchant_rules").fetchone()[0] == 0


def test_メモを空文字にすると消せる(conn):
    transaction_id = _pending_id(conn)
    modify_transaction(conn, transaction_id, TransactionUpdate(memo="USB ケーブル"))

    modify_transaction(conn, transaction_id, TransactionUpdate(memo=""))

    assert fetch_transaction(conn, transaction_id).memo == ""
