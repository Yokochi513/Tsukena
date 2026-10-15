import sqlite3


def upsert_merchant_rule(
    conn: sqlite3.Connection, merchant_key: str, category_id: int
) -> None:
    # 同じ照合キーのルールがあれば上書きする（最後に選んだものが勝つ）。commit は呼び出す側が行う
    conn.execute(
        """
        INSERT INTO merchant_rules (merchant_key, category_id) VALUES (?, ?)
        ON CONFLICT (merchant_key) DO UPDATE SET category_id = excluded.category_id
        """,
        (merchant_key, category_id),
    )
