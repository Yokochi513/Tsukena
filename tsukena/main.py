import uvicorn

from .api.app import create_app
from .config import load_db_path


def main() -> None:
    app = create_app(load_db_path())
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
