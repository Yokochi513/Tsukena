import asyncio
import datetime
import logging
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from . import notifier
from .mail.gmail_client import GmailAuthError, GmailError
from .repositories.database import connect
from .repositories.setting_repository import fetch_setting
from .services.importer import import_mails

logger = logging.getLogger(__name__)

IMPORT_INTERVAL_MINUTES = 5
GMAIL_AUTH_ALERT = (
    "⚠️ Gmail との連携が切れているため、メールを取り込めません\n"
    "アプリの設定から Gmail 連携をやり直してください"
)

# 連携が切れている間、同じ通知を5分ごとに送らないための印。取り込みに成功したら戻す
_auth_alert_sent = False


def create_scheduler(db_path: Path) -> AsyncIOScheduler:
    """取り込み・週のまとめ・月のまとめを決まった時刻に起動する定期実行を組み立てる（→ docs/design.md 4）。

    起動（start）は呼び出す側が、動いているイベントループの中で行う。
    """
    tz = ZoneInfo("Asia/Tokyo")
    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(
        run_import,
        "interval",
        minutes=IMPORT_INTERVAL_MINUTES,
        args=[db_path],
        id="import_mails",
        # 再起動の後に5分待たず、すぐ1回取り込む
        next_run_time=datetime.datetime.now(tz),
        # 前の取り込みが終わる前に次の時刻が来ても、重ねて動かさない
        max_instances=1,
        coalesce=True,
    )
    # TODO: reporter ができたら、週のまとめ（毎週日曜 21:00）と月のまとめ（毎月1日 9:00）を登録する
    return scheduler


async def run_import(db_path: Path) -> None:
    """取り込みを1回動かす。例外が起きてもプロセスは止めず、次の周期でやり直す（→ docs/design.md 11）"""
    global _auth_alert_sent
    try:
        # Gmail と DB の呼び出しは同期で待つため、イベントループ（REST API）を止めないよう別スレッドで動かす
        await asyncio.to_thread(_import_once, db_path)
    # Gmail の失敗は起こり得るものなので、5分ごとにトレースバックを残さず1行で記録する
    except GmailAuthError as error:
        logger.warning("Gmail との連携が切れているため、取り込めませんでした: %s", error)
        if not _auth_alert_sent:
            _auth_alert_sent = _notify(GMAIL_AUTH_ALERT)
        return
    except GmailError as error:
        logger.warning("Gmail からメールを取れませんでした。次の周期でやり直します: %s", error)
        return
    except Exception:
        logger.exception("取り込みに失敗しました。次の周期でやり直します")
        return
    _auth_alert_sent = False


def _import_once(db_path: Path) -> None:
    conn = connect(db_path)
    try:
        import_mails(conn, fetch_setting(conn).gmail_label)
    finally:
        conn.close()


def _notify(text: str) -> bool:
    """通知を送り、送れたかを返す。送れなくても取り込みの周期は止めない"""
    try:
        notifier.send_dm(text)
    except notifier.NotifyError:
        logger.exception("通知を送れませんでした")
        return False
    return True
