import datetime
import sqlite3
from pathlib import Path

import pytest

from tsukena import notifier
from tsukena.mail import gmail_client, mail_parser
from tsukena.mail.gmail_client import GmailError
from tsukena.model.import_failure_model import ImportFailure
from tsukena.model.mail_message_model import MailMessage
from tsukena.repositories import import_failure_repository
from tsukena.repositories.database import migrate
from tsukena.repositories.setting_repository import fetch_setting
from tsukena.services import importer

from .test__jcb_card import SAMPLE_REALTIME

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"
JCB = "JCB Webmaster <mail@qa.jcb.co.jp>"
GOOD = MailMessage("good1", JCB, "ご利用のお知らせ", SAMPLE_REALTIME)
BAD = MailMessage("bad1", JCB, "お知らせ", "キャンペーンのご案内です。")


@pytest.fixture
def conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript((SQL_DIR / "create_tables.sql").read_text(encoding="utf-8"))
    for name in ["sample/01_categories.sql", "sample/02_settings.sql"]:
        conn.executescript((SQL_DIR / name).read_text(encoding="utf-8"))
    return conn


@pytest.fixture
def gmail(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Gmail と Discord を差し替える。queries に問い合わせ、sent に送った通知がたまる"""
    state: dict = {"mails": {}, "queries": [], "sent": [], "error": None}

    def list_message_ids(query: str) -> list[str]:
        state["queries"].append(query)
        return list(state["mails"])

    def get_message(message_id: str) -> MailMessage:
        if state["error"] is not None:
            raise state["error"]
        return state["mails"][message_id]

    monkeypatch.setattr(gmail_client, "list_message_ids", list_message_ids)
    monkeypatch.setattr(gmail_client, "get_message", get_message)
    monkeypatch.setattr(notifier, "send_dm", state["sent"].append)
    return state


def _gmail_records(conn: sqlite3.Connection) -> int:
    return conn.execute(
        "SELECT count(*) FROM transactions WHERE source = 'gmail'"
    ).fetchone()[0]


def test_初回は期間を区切らずに問い合わせ_結果を1回だけ知らせる(conn, gmail):
    gmail["mails"] = {"good1": GOOD, "bad1": BAD}

    importer.import_mails(conn, fetch_setting(conn))

    assert gmail["queries"] == ["label:Tsukena"]
    assert _gmail_records(conn) == 1
    assert import_failure_repository.import_failure_exists(conn, "bad1")
    # 取り込めなかったメールの通知は1通ごとに送らず、結果の1通にまとめる
    assert len(gmail["sent"]) == 1
    assert gmail["sent"][0].startswith("📬 これまでのメールの取り込みが終わりました（1件を記録）")
    assert "1通" in gmail["sent"][0]
    assert fetch_setting(conn).full_import_done


def test_2回目からは直近7日分だけを問い合わせ_1通ごとに知らせる(conn, gmail):
    importer.import_mails(conn, fetch_setting(conn))
    gmail["sent"].clear()
    gmail["mails"] = {"bad1": BAD}

    importer.import_mails(conn, fetch_setting(conn))

    assert gmail["queries"][-1] == "label:Tsukena newer_than:7d"
    assert len(gmail["sent"]) == 1
    assert gmail["sent"][0].startswith("📭 取り込めないメールがありました")


def test_全期間の取り込みが途中で止まれば_次の周期でまた全期間を問い合わせる(conn, gmail):
    gmail["mails"] = {"good1": GOOD}
    gmail["error"] = GmailError("一時的な失敗")

    with pytest.raises(GmailError):
        importer.import_mails(conn, fetch_setting(conn))

    assert not fetch_setting(conn).full_import_done
    assert gmail["sent"] == []


def test_取り込み直すと_その場で記録して失敗の記録を消す(conn, gmail):
    _add_failure(conn, "good1")
    gmail["mails"] = {"good1": GOOD}

    assert importer.retry_failed_mail(conn, "good1") == 1

    assert _gmail_records(conn) == 1
    assert not import_failure_repository.import_failure_exists(conn, "good1")
    assert gmail["sent"] == []


def test_取り込み直してもまだ解析できなければ_理由を新しくして失敗を残す(conn, gmail):
    _add_failure(conn, "bad1", reason="古い理由")
    gmail["mails"] = {"bad1": BAD}

    with pytest.raises(mail_parser.UnparsableMailError) as e:
        importer.retry_failed_mail(conn, "bad1")

    assert e.value.reason == "支払いが見つかりません"
    [failure] = import_failure_repository.fetch_import_failures(conn)
    assert failure.reason == "支払いが見つかりません"
    assert gmail["sent"] == []


def test_失敗の記録が無いメールは取り込み直せない(conn, gmail):
    with pytest.raises(importer.ImportFailureNotFoundError):
        importer.retry_failed_mail(conn, "unknown")


def test_古いDBに全期間の取り込みとメモの列を足す():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE settings (id INTEGER PRIMARY KEY, monthly_budget INTEGER, gmail_label TEXT)"
    )
    conn.execute("INSERT INTO settings VALUES (1, 80000, 'Tsukena')")
    conn.execute("CREATE TABLE transactions (id INTEGER PRIMARY KEY, amount INTEGER)")
    conn.execute("INSERT INTO transactions VALUES (1, 500)")

    migrate(conn)
    migrate(conn)  # 2回目は何もしない

    assert not fetch_setting(conn).full_import_done
    assert conn.execute("SELECT memo FROM transactions").fetchone()[0] == ""


def _add_failure(conn: sqlite3.Connection, message_id: str, reason: str = "理由") -> None:
    failed_at = datetime.datetime(2026, 10, 19, tzinfo=datetime.UTC)
    with conn:
        import_failure_repository.insert_import_failure(
            conn, ImportFailure(message_id, JCB, "件名", reason, failed_at)
        )
