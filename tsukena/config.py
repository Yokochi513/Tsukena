from pathlib import Path

import tomllib

CONFIG_PATH = Path(__file__).resolve().parent / "config.toml"


def load_db_path() -> Path:
    with CONFIG_PATH.open("rb") as f:
        config = tomllib.load(f)
    return (CONFIG_PATH.parent / config["database"]["path"]).resolve()
