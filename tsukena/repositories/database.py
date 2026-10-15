import sqlite3
from pathlib import Path


def connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.is_file():
        raise FileNotFoundError(f"Database file not found: {db_path}")
    # FastAPI は依存関数とエンドポイントを別スレッドで実行することがあるため、スレッドチェックを外す。
    # 接続はリクエストごとに作り、同時に複数スレッドから使うことはない。
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
