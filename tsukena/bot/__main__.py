import logging
import os

from dotenv import load_dotenv

from .discord_bot import create_bot


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    # TODO: REST API の URL と bot 用のトークンから ApiClient を作って渡す（→ ADR-0007）
    client = create_bot()
    # ログは basicConfig で設定済みのため、discord.py に独自のハンドラーを足させない
    client.run(os.environ["DISCORD_TOKEN"], log_handler=None)


if __name__ == "__main__":
    main()
