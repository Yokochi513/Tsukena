import sqlite3

from ..model.category_model import Category


def fetch_categories(conn: sqlite3.Connection) -> list[Category]:
    rows = conn.execute("SELECT * FROM categories").fetchall()
    return [_row_to_category(r) for r in rows]


def _row_to_category(row: sqlite3.Row) -> Category:
    return Category(
        id=row["id"],
        name=row["name"],
        emoji=row["emoji"],
        sort_order=row["sort_order"],
    )
