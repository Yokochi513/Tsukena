import asyncio
import logging
import os

from dotenv import load_dotenv

from .api_client import ApiClient
from .discord_bot import create_bot

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"


async def run() -> None:
    # bot から API へは同じ機械の中で呼ぶ（→ docs/design.md 11）。別の機械に置くときだけ環境変数で変える
    base_url = os.environ.get("TSUKENA_API_BASE_URL", DEFAULT_API_BASE_URL)
    async with ApiClient(base_url, os.environ["TSUKENA_BOT_API_TOKEN"]) as api:
        client = create_bot(api)
        async with client:
            await client.start(os.environ["DISCORD_TOKEN"])


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    # ApiClient の接続はイベントループの中で作る必要があるため、client.run() ではなく asyncio.run() で動かす
    asyncio.run(run())


if __name__ == "__main__":
    main()
