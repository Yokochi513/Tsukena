from contextlib import closing

from .config import load_db_path
from .repositories.database import connect
from .repositories.expense_repository import list_expenses


def main() -> None:
    with closing(connect(load_db_path())) as conn:
        for expense in list_expenses(conn):
            print(expense)


if __name__ == "__main__":
    main()
