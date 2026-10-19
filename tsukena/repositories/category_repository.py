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


def update_category(
    conn: sqlite3.Connection, category_id: int, update: CategoryInput
) -> Category | None:
    row = conn.execute(
        "SELECT * FROM categories WHERE id = ?", (category_id,)
    ).fetchone()
    if row is None:
        return None
    current = _row_to_category(row)

    updated = Category(
        id=current.id,
        name=update.name,
        emoji=update.emoji,
        sort_order=update.sort_order,
    )

    conn.execute(
        "UPDATE categories SET name = ?, emoji = ?, sort_order = ? WHERE id = ?",
        (updated.name, updated.emoji, updated.sort_order, category_id),
    )
    conn.commit()
    return updated


def fetch_categories(conn: sqlite3.Connection) -> list[Category]:
    # アプリの一覧と bot のリアクションの並びをそろえるため、表示順で並べる（→ docs/module/discord_bot_design.md）
    rows = conn.execute("SELECT * FROM categories ORDER BY sort_order, id").fetchall()
    return [_row_to_category(r) for r in rows]


def fetch_category(conn: sqlite3.Connection, category_id: int) -> Category | None:
    row = conn.execute(
        "SELECT * FROM categories WHERE id = ?", (category_id,)
    ).fetchone()
    return _row_to_category(row) if row is not None else None


def _row_to_category(row: sqlite3.Row) -> Category:
    return Category(
        id=row["id"],
        name=row["name"],
        emoji=row["emoji"],
        sort_order=row["sort_order"],
    )


def category_exists(conn: sqlite3.Connection, category_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM categories WHERE id = ?", (category_id,)
    ).fetchone()
    return row is not None
