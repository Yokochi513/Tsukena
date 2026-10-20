import asyncio
import logging

import uvicorn
from dotenv import load_dotenv

from ..config import (
    load_api_token,
    load_cors_origins,
    load_db_path,
    load_google_redirect_uri,
    load_payment_rules,
)
from ..mail import mail_parser
from ..repositories.database import connect, migrate
from ..scheduler import create_scheduler
from ..services.transaction_service import CASH_PAYMENT_METHOD
from .app import create_app


async def run() -> None:
    db_path = load_db_path()
    # 既にある DB に、新しく足した列を足してから動かす
    conn = connect(db_path)
    try:
        migrate(conn)
    finally:
        conn.close()
    app = create_app(
        db_path, load_api_token(), load_cors_origins(), load_google_redirect_uri()
    )
    # 外からは Cloudflare Tunnel を通してだけ届かせるため、同じ機械の中でだけ待ち受ける（→ ADR-0009）
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=18000))

    # 定期実行は REST API と同じイベントループで動かす（→ docs/design.md 3）
    scheduler = create_scheduler(db_path)
    scheduler.start()
    try:
        await server.serve()
    finally:
        scheduler.shutdown(wait=False)


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    # 書き方の誤りや、ルールの無い支払い手段があれば起動しない（→ docs/design.md 7.1）
    missing = (mail_parser.payment_methods() | {CASH_PAYMENT_METHOD}) - set(
        load_payment_rules()
    )
    if missing:
        raise ValueError(f"支払い手段のルールがありません: {', '.join(sorted(missing))}")
    asyncio.run(run())


if __name__ == "__main__":
    main()
