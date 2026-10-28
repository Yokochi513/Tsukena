import sqlite3
from pathlib import Path

SQL_PATH = Path(__file__).resolve().parents[2] / "sql" / "create_tables.sql"

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
    columns = _columns(conn, "settings")
    if "full_import_done" not in columns:
        # 既に動いている DB でも、次の取り込みで一度だけ全期間を問い合わせる
        with conn:
            conn.execute(
                "ALTER TABLE settings ADD COLUMN full_import_done INTEGER NOT NULL"
                " DEFAULT 0 CHECK (full_import_done IN (0, 1))"
            )
    if "memo" not in _columns(conn, "transactions"):
        with conn:
            conn.execute(
                "ALTER TABLE transactions ADD COLUMN memo TEXT NOT NULL DEFAULT ''"
            )
    if "payment_plan" not in _columns(conn, "transactions"):
        # 既にある記録はすべて1回払いにする。ALTER TABLE では表の CHECK（plan_count との組み合わせ）は足せない
        with conn:
            conn.execute(
                "ALTER TABLE transactions ADD COLUMN payment_plan TEXT NOT NULL DEFAULT 'lump'"
                " CHECK (payment_plan IN ('lump', 'skip', 'installment', 'revolving'))"
            )
            conn.execute(
                "ALTER TABLE transactions ADD COLUMN plan_count INTEGER"
                " CHECK (plan_count IS NULL OR plan_count >= 1)"
            )
    _create_missing_tables(conn, {"charges", "revolving_fees"})


def _create_missing_tables(conn: sqlite3.Connection, names: set[str]) -> None:
    """create_tables.sql の文のうち、names のテーブル（と、そのインデックス）でまだ無いものだけを作る"""
    existing = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    missing = names - existing
    if not missing:
        return
    schema = (SQL_PATH).read_text(encoding="utf-8")
    with conn:
        for statement in _statements(schema):
            target = _statement_table(statement)
            if target in missing:
                conn.execute(statement)


def _statements(schema: str) -> list[str]:
    # コメントの行を落としてから ; で区切る。create_tables.sql の文字列の中に ; は無い
    lines = [line.split("--", 1)[0] for line in schema.splitlines()]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def _statement_table(statement: str) -> str | None:
    words = statement.split()
    if words[:2] == ["CREATE", "TABLE"]:
        return words[2]
    if words[:2] == ["CREATE", "INDEX"] and "ON" in words:
        return words[words.index("ON") + 1]
    return None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
