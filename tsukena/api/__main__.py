import uvicorn
from dotenv import load_dotenv

from ..config import load_api_token, load_cors_origins, load_db_path
from .app import create_app


def main() -> None:
    load_dotenv()
    app = create_app(load_db_path(), load_api_token(), load_cors_origins())
    # 外からは Cloudflare Tunnel を通してだけ届かせるため、同じ機械の中でだけ待ち受ける（→ ADR-0009）
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
