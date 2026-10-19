import logging

import discord

logger = logging.getLogger(__name__)


# TODO: api_client ができたら、引数に ApiClient を受け取る（→ docs/module/discord_bot_design.md）
def create_bot() -> discord.Client:
    # DM の本文は Message Content Intent が無くても読めるため、特権インテントは要求しない（→ ADR-0008）
    intents = discord.Intents.none()
    intents.dm_messages = True
    intents.dm_reactions = True
    client = discord.Client(intents=intents)
    owner_id = 0  # setup_hook で、アプリの持ち主の ID に置き換える

    async def setup_hook() -> None:
        nonlocal owner_id
        info = await client.application_info()
        owner_id = info.owner.id

    client.setup_hook = setup_hook

    @client.event
    async def on_ready() -> None:
        logger.info("Discordに接続しました: %s（持ち主の ID: %s）", client.user, owner_id)

    @client.event
    async def on_message(message: discord.Message) -> None:
        await handle_message(message, owner_id)

    # キャッシュに無い（再起動より前の）返事へのリアクションも受け取るため raw の方を使う
    @client.event
    async def on_raw_reaction_add(payload: discord.RawReactionActionEvent) -> None:
        await handle_reaction(client, payload, owner_id)

    return client


async def handle_message(message: discord.Message, owner_id: int) -> None:
    guild_id = message.guild.id if message.guild is not None else None
    if not _is_owner_dm(message.author.id, guild_id, owner_id):
        return
    # TODO: api.fetch_categories() → api.record_cash() → _reply_recorded
    await message.reply(f"受け取りました: {message.content}")


async def handle_reaction(
    client: discord.Client,
    payload: discord.RawReactionActionEvent,
    owner_id: int,
) -> None:
    pass  # TODO: カテゴリの変更


def _is_owner_dm(user_id: int, guild_id: int | None, owner_id: int) -> bool:
    return user_id == owner_id and guild_id is None
