import sqlite3

from ..model.category_model import Category, CategoryInput


def insert_category(conn: sqlite3.Connection, category: CategoryInput) -> Category:
    cur = conn.execute(
        "INSERT INTO categories (name, emoji, sort_order) VALUES (?, ?, ?)",
        (category.name, category.emoji, category.sort_order),
    )
    conn.commit()

    return Category(
        id=cur.lastrowid,
        name=category.name,
        emoji=category.emoji,
        sort_order=category.sort_order,
    )


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
