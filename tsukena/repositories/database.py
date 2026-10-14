import sqlite3
import tomllib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.toml"

with CONFIG_PATH.open("rb") as f:
    config = tomllib.load(f)

db_path = (CONFIG_PATH.parent / config["database"]["path"]).resolve()

if not db_path.is_file():
    raise FileNotFoundError(f"Database file not found: {db_path}")


with sqlite3.connect(db_path) as conn:
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM expenses").fetchall()

for row in rows:
    print(dict(row))
