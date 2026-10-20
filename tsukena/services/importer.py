import datetime
import sqlite3

from .. import notifier, summary
from ..mail import gmail_client, mail_parser
from ..model.import_failure_model import ImportFailure
from ..repositories import import_failure_repository, transaction_repository
from . import recorder
from .recorder import JST

# 毎回この日数分を問い合わせ、取り込み済みのメールを除く。
# 履歴 ID を追うより、取りこぼしからの復帰が単純になる（→ docs/design.md 4.1）
LOOKBACK_DAYS = 7


def import_mails(conn: sqlite3.Connection, label: str) -> None:
    """Gmail のラベル付きメールを取り込む（→ docs/design.md 4.1）。

    - 直近7日分を毎回問い合わせ、取り込み済み・削除済み・失敗記録済みのメールを除く
    - 解析できたメールは、1通分の支払いをまとめて1つのトランザクションで記録する。
      途中で失敗すれば1通分すべてを取り消し、次の周期でやり直す
    - 解析できなかったメールは import_failures に残し、持ち主に通知する
    - GmailError / GmailAuthError はそのまま投げる。次の周期でやり直すのは scheduler の役目
    """
    query = f"label:{label} newer_than:{LOOKBACK_DAYS}d"
    for message_id in gmail_client.list_message_ids(query):
        if _processed(conn, message_id):
            continue
        mail = gmail_client.get_message(message_id)
        try:
            payments = mail_parser.parse(mail)
        except mail_parser.UnparsableMailError as error:
            failure = ImportFailure(
                message_id=mail.message_id,
                sender=mail.sender,
                subject=mail.subject,
                reason=error.reason,
                failed_at=datetime.datetime.now(JST),
            )
            with conn:
                import_failure_repository.insert_import_failure(conn, failure)
            notifier.send_dm(summary.format_import_failure(failure))
            continue
        with conn:
            for payment in payments:
                recorder.record_payment(conn, payment)
        # TODO: budget モジュールができたら、予算の閾値を超えたときに通知する


def _processed(conn: sqlite3.Connection, message_id: str) -> bool:
    """このメールを既に扱ったか。記録済み・削除済み・失敗記録済みのどれかなら扱い済みとする"""
    return (
        transaction_repository.gmail_message_recorded(conn, message_id)
        or transaction_repository.gmail_message_deleted(conn, message_id)
        or import_failure_repository.import_failure_exists(conn, message_id)
    )
