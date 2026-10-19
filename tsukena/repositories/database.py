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
