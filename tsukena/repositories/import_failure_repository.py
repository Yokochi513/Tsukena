import datetime
import sqlite3

from ..model.import_failure_model import ImportFailure


def insert_import_failure(conn: sqlite3.Connection, failure: ImportFailure) -> None:
    # 取り込みの他の書き込みと同じ単位で確定させたいため、commit は呼び出す側が行う
    conn.execute(
        """
        INSERT INTO import_failures (message_id, sender, subject, reason, failed_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            failure.message_id,
            failure.sender,
            failure.subject,
            failure.reason,
            failure.failed_at.isoformat(),
        ),
    )


def import_failure_exists(conn: sqlite3.Connection, message_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM import_failures WHERE message_id = ?", (message_id,)
    ).fetchone()
    return row is not None


def fetch_import_failures(conn: sqlite3.Connection) -> list[ImportFailure]:
    rows = conn.execute(
        "SELECT * FROM import_failures ORDER BY failed_at DESC, message_id"
    ).fetchall()
    return [_row_to_import_failure(r) for r in rows]


def _row_to_import_failure(row: sqlite3.Row) -> ImportFailure:
    return ImportFailure(
        message_id=row["message_id"],
        sender=row["sender"],
        subject=row["subject"],
        reason=row["reason"],
        failed_at=datetime.datetime.fromisoformat(row["failed_at"]),
    )
