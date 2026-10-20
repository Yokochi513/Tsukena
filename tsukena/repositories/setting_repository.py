import sqlite3

from ..model.setting import Setting


def fetch_setting(conn: sqlite3.Connection) -> Setting:
    # settings は常に1行だけ持つ（id = 1）。DB を作るときに入れておく
    row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    if row is None:
        raise LookupError("settings に行がありません")
    return Setting(
        id=row["id"],
        monthly_budget=row["monthly_budget"],
        gmail_label=row["gmail_label"],
        full_import_done=bool(row["full_import_done"]),
    )


def mark_full_import_done(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute("UPDATE settings SET full_import_done = 1 WHERE id = 1")
