import datetime

from tsukena.model.import_failure_model import ImportFailure
from tsukena.summary import format_import_failure

FAILED_AT = datetime.datetime(
    2026, 10, 21, 9, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=9))
)


def test_取り込めないメールの通知に送り主_件名_理由と取り込み直す手順を書く():
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
        "理由: ご利用金額を読めません: -500円\n"
        "このメールの形に、解析がまだ対応していない可能性があります。"
        "解析を直してから、アプリの設定の「取り込めなかったメール」で「取り込み直す」を押してください"
        "（メールが届いてから7日以内に限ります）"
    )


def test_件名が無ければ件名なしと書く():
    failure = ImportFailure("abc123", "someone@example.com", "", "理由", FAILED_AT)
    assert "件名: （件名なし）\n" in format_import_failure(failure)
