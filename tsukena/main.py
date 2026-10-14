from .config import load_db_path
from .repositories.database import connect


def main() -> None:
    conn = connect(load_db_path())
    
