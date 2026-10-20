import datetime
import sqlite3

from .. import notifier, summary
from ..mail import gmail_client, mail_parser
from ..model.enum.record_outcome import RecordOutcome
from ..model.import_failure_model import ImportFailure
from ..model.mail_message_model import MailMessage
from ..model.parsed_payment_model import ParsedPayment
from ..model.setting import Setting
from ..repositories import (
    import_failure_repository,
    setting_repository,
    transaction_repository,
)
from . import recorder
from .recorder import JST

# 毎回この日数分を問い合わせ、取り込み済みのメールを除く。
# 履歴 ID を追うより、取りこぼしからの復帰が単純になる（→ docs/design.md 4.1）
LOOKBACK_DAYS = 7


class ImportFailureNotFoundError(Exception):
    pass


def import_mails(conn: sqlite3.Connection, setting: Setting) -> None:
    """Gmail のラベル付きメールを取り込む（→ docs/design.md 4.1）。

    - 直近7日分を毎回問い合わせ、取り込み済み・削除済み・失敗記録済みのメールを除く
    - 全期間の取り込みをまだ済ませていなければ、期間を区切らずに一度だけ問い合わせる。
      このときは1通ごとの通知を送らず、終わった後に結果を1回だけ知らせる
    - 解析できたメールは、1通分の支払いをまとめて1つのトランザクションで記録する。
      途中で失敗すれば1通分すべてを取り消し、次の周期でやり直す
    - 解析できなかったメールは import_failures に残し、持ち主に通知する
    - GmailError / GmailAuthError はそのまま投げる。次の周期でやり直すのは scheduler の役目。
      全期間の取り込みが途中で止まったときも、済んだ印を付けないので、次の周期で全期間からやり直す
    """
    full = not setting.full_import_done
    query = f"label:{setting.gmail_label}"
    if not full:
        query += f" newer_than:{LOOKBACK_DAYS}d"

    recorded = 0
    failures: list[ImportFailure] = []
    for message_id in gmail_client.list_message_ids(query):
        if _processed(conn, message_id):
            continue
        mail = gmail_client.get_message(message_id)
        try:
            payments = mail_parser.parse(mail)
        except mail_parser.UnparsableMailError as error:
            failure = _failure(mail, error.reason)
            with conn:
                import_failure_repository.insert_import_failure(conn, failure)
            if full:
                failures.append(failure)
            else:
                notifier.send_dm(summary.format_import_failure(failure))
            continue
        with conn:
            recorded += _record(conn, payments)
        # TODO: budget モジュールができたら、予算の閾値を超えたときに通知する

    if full:
        setting_repository.mark_full_import_done(conn)
        notifier.send_dm(summary.format_full_import_result(recorded, failures))


def retry_failed_mail(conn: sqlite3.Connection, message_id: str) -> int:
    """取り込めなかったメールを、その場で取り込み直す（→ docs/api_list.md 2.6）。記録した件数を返す。

    - メールを ID で取り直すので、届いてからの日数によらず取り込み直せる
    - 失敗の記録を消すことと支払いの記録を、1つのトランザクションで行う。
      同じ時刻に動いた定期の取り込みが、同じメールを二重に記録しないため
    - まだ解析できなければ、失敗の理由と日時を新しくして UnparsableMailError を投げる。通知は送らない
      （アプリの操作の結果として、その場で返すため）
    - 失敗の記録が無ければ ImportFailureNotFoundError を投げる
    """
    if not import_failure_repository.import_failure_exists(conn, message_id):
        raise ImportFailureNotFoundError
    mail = gmail_client.get_message(message_id)
    try:
        payments = mail_parser.parse(mail)
    except mail_parser.UnparsableMailError as error:
        with conn:
            import_failure_repository.remove_import_failure(conn, message_id)
            import_failure_repository.insert_import_failure(
                conn, _failure(mail, error.reason)
            )
        raise
    with conn:
        import_failure_repository.remove_import_failure(conn, message_id)
        return _record(conn, payments)


def _record(conn: sqlite3.Connection, payments: list[ParsedPayment]) -> int:
    """支払いを記録し、新しく記録した件数を返す。commit は呼び出す側が行う"""
    results = [recorder.record_payment(conn, payment) for payment in payments]
    return sum(1 for r in results if r.outcome is RecordOutcome.RECORDED)


def _failure(mail: MailMessage, reason: str) -> ImportFailure:
    return ImportFailure(
        message_id=mail.message_id,
        sender=mail.sender,
        subject=mail.subject,
        reason=reason,
        failed_at=datetime.datetime.now(JST),
    )


def _processed(conn: sqlite3.Connection, message_id: str) -> bool:
    """このメールを既に扱ったか。記録済み・削除済み・失敗記録済みのどれかなら扱い済みとする"""
    return (
        transaction_repository.gmail_message_recorded(conn, message_id)
        or transaction_repository.gmail_message_deleted(conn, message_id)
        or import_failure_repository.import_failure_exists(conn, message_id)
    )
