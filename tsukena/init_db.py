"""本番の DB を作る。`python -m tsukena.init_db` で実行する。

テーブルを作り、カテゴリと設定の初期値（README「カテゴリ（初期値）」と同じ）だけを入れる。
支出・収入などのサンプルデータは入れない。DB が既にあるときは、上書きせずに止める。
"""

import sqlite3
import sys
from pathlib import Path

from .config import load_db_path

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
INITIAL_DATA = ["sample/01_categories.sql", "sample/02_settings.sql"]


def main() -> None:
    db_path = load_db_path()
    if db_path.exists():
        sys.exit(f"DB が既にあります。上書きしないので、作り直すなら先に移してください: {db_path}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            schema = (SQL_DIR / "create_tables.sql").read_text(encoding="utf-8")
            conn.executescript(schema)
            for name in INITIAL_DATA:
                conn.executescript((SQL_DIR / name).read_text(encoding="utf-8"))
    finally:
        conn.close()
    print(f"DB を作りました: {db_path}")


if __name__ == "__main__":
    main()
