import sqlite3
from pathlib import Path

import pytest

from tsukena.model.category_model import CategoryInput
from tsukena.repositories.category_repository import (
    DuplicateCategoryError,
    fetch_categories,
    insert_category,
    update_category,
)

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"


@pytest.fixture
def conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript((SQL_DIR / "create_tables.sql").read_text(encoding="utf-8"))
    conn.executescript(
        (SQL_DIR / "sample/01_categories.sql").read_text(encoding="utf-8")
    )
    return conn


def test_表示順を省略して追加すると_末尾に入る(conn):
    last = max(c.sort_order for c in fetch_categories(conn))

    category = insert_category(conn, CategoryInput(name="ペット", emoji="🐶"))

    assert category.sort_order == last + 1
    assert fetch_categories(conn)[-1] == category


def test_カテゴリが無いときに表示順を省略して追加すると_1になる(conn):
    conn.execute("DELETE FROM categories")

    category = insert_category(conn, CategoryInput(name="ペット", emoji="🐶"))

    assert category.sort_order == 1


def test_表示順を指定して追加すると_その表示順で入る(conn):
    category = insert_category(
        conn, CategoryInput(name="ペット", emoji="🐶", sort_order=3)
    )

    assert category.sort_order == 3


@pytest.mark.parametrize(
    "category",
    [
        CategoryInput(name="食費", emoji="🐶"),
        CategoryInput(name="ペット", emoji="🍚"),
    ],
)
def test_名前か絵文字が既にあるカテゴリと同じなら_追加できない(conn, category):
    count = len(fetch_categories(conn))

    with pytest.raises(DuplicateCategoryError):
        insert_category(conn, category)

    assert len(fetch_categories(conn)) == count


def test_表示順を省略して変更すると_表示順は変わらない(conn):
    before = fetch_categories(conn)[0]

    after = update_category(conn, before.id, CategoryInput(name="ごはん", emoji="🍙"))

    assert after is not None
    assert after.sort_order == before.sort_order
    assert after.name == "ごはん"
