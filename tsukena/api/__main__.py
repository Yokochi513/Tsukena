import uvicorn

from ..config import load_api_token, load_db_path
from .app import create_app


def main() -> None:
    app = create_app(load_db_path(), load_api_token())
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
