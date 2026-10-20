import sqlite3
from pathlib import Path

# 書き込みが重なったときに、ロックが外れるのを待つ時間（ミリ秒）
BUSY_TIMEOUT_MS = 5000


def connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.is_file():
        raise FileNotFoundError(f"Database file not found: {db_path}")
    # FastAPI は依存関数とエンドポイントを別スレッドで実行することがあるため、スレッドチェックを外す。
    # 接続はリクエストごとに作り、同時に複数スレッドから使うことはない。
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # API と bot の2つのプロセスから書き込むため（→ ADR-0006）。
    # WAL にすると読み取りが書き込みを待たない。WAL の設定はファイルに残るが、毎回指定しても害はない
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """既にある DB を、今のテーブルの定義（sql/create_tables.sql）に合わせる。API の起動時に呼ぶ。

    足りない列だけを足す。何度呼んでも同じ結果になる。
    """
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(settings)")}
    if "full_import_done" not in columns:
        # 既に動いている DB でも、次の取り込みで一度だけ全期間を問い合わせる
        with conn:
            conn.execute(
                "ALTER TABLE settings ADD COLUMN full_import_done INTEGER NOT NULL"
                " DEFAULT 0 CHECK (full_import_done IN (0, 1))"
            )
