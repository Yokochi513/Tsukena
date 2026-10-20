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
    )
