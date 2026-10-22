import sqlite3

from ..model.category_model import Category, CategoryInput


class DuplicateCategoryError(Exception):
    """名前か絵文字が、既にあるカテゴリと同じ"""


def insert_category(conn: sqlite3.Connection, category: CategoryInput) -> Category:
    try:
        with conn:
            # 表示順を省略したときは、今ある最大値 + 1（末尾）にする（→ docs/api_list.md 2.4）
            cur = conn.execute(
                "INSERT INTO categories (name, emoji, sort_order) VALUES (?, ?,"
                " COALESCE(?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM categories)))",
                (category.name, category.emoji, category.sort_order),
            )
    except sqlite3.IntegrityError:
        # 空文字は API の入口で弾くため、ここで残る制約違反は名前か絵文字の重複
        raise DuplicateCategoryError from None

    inserted = fetch_category(conn, cur.lastrowid or 0)
    assert inserted is not None
    return inserted


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
        sort_order=(
            update.sort_order if update.sort_order is not None else current.sort_order
        ),
    )

    try:
        with conn:
            conn.execute(
                "UPDATE categories SET name = ?, emoji = ?, sort_order = ? WHERE id = ?",
                (updated.name, updated.emoji, updated.sort_order, category_id),
            )
    except sqlite3.IntegrityError:
        raise DuplicateCategoryError from None
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
