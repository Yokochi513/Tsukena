import datetime

from tsukena.model.import_failure_model import ImportFailure
from tsukena.summary import format_import_failure

FAILED_AT = datetime.datetime(
    2026, 10, 21, 9, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=9))
)


def test_取り込めないメールの通知に送り主と件名を書く():
    failure = ImportFailure(
        message_id="abc123",
        sender="JCB Webmaster <mail@qa.jcb.co.jp>",
        subject="カードご利用のお知らせ",
        reason="ご利用金額を読めません: -500円",
        failed_at=FAILED_AT,
    )
    assert format_import_failure(failure) == (
        "📭 取り込めないメールがありました\n"
        "送り主: JCB Webmaster <mail@qa.jcb.co.jp>\n"
        "件名: カードご利用のお知らせ\n"
        "アプリの設定から「取り込めなかったメール」を確認してください"
    )


def test_件名が無ければ件名なしと書く():
    failure = ImportFailure("abc123", "someone@example.com", "", "理由", FAILED_AT)
    assert "件名: （件名なし）\n" in format_import_failure(failure)
