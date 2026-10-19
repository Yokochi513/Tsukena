import logging

import discord

from ..model.category_model import Category
from ..model.enum.record_outcome import RecordOutcome
from ..model.enum.source import Source
from ..model.record_model import RecordResult
from ..summary import format_cash_reply
from .api_client import ApiClient

logger = logging.getLogger(__name__)

# Discord の1メッセージに付けられるリアクションの上限（→ docs/design.md 残課題 R-8）
MAX_REACTIONS = 20
HELP_REPLY = (
    "記録できませんでした。「メモ 金額」の形で送ってください。\n"
    "例: `ランチ 800` / `800`（メモ無し）"
)
RECORD_ERROR_REPLY = "記録できませんでした。時間をおいて送り直してください"
CATEGORY_ERROR_REPLY = "カテゴリを変更できませんでした。アプリから直してください"


def create_bot(api: ApiClient) -> discord.Client:
    # DM の本文は Message Content Intent が無くても読めるため、特権インテントは要求しない（→ ADR-0008）
    intents = discord.Intents.none()
    intents.dm_messages = True
    intents.dm_reactions = True
    client = discord.Client(intents=intents)
    owner_id = 0  # setup_hook で、アプリの持ち主の ID に置き換える

    async def setup_hook() -> None:
        # 取れなかったときは例外をそのまま返し、起動を止める。持ち主が分からないと、どの操作にも反応できない
        nonlocal owner_id
        info = await client.application_info()
        owner_id = info.owner.id

    client.setup_hook = setup_hook

    @client.event
    async def on_ready() -> None:
        logger.info(
            "Discordに接続しました: %s（持ち主の ID: %s）", client.user, owner_id
        )

    @client.event
    async def on_message(message: discord.Message) -> None:
        await handle_message(message, owner_id, api)

    # キャッシュに無い（再起動より前の）返事へのリアクションも受け取るため raw の方を使う
    @client.event
    async def on_raw_reaction_add(payload: discord.RawReactionActionEvent) -> None:
        await handle_reaction(client, payload, owner_id, api)

    return client


async def handle_message(
    message: discord.Message, owner_id: int, api: ApiClient
) -> None:
    guild_id = message.guild.id if message.guild is not None else None
    if not _is_owner_dm(message.author.id, guild_id, owner_id):
        return

    try:
        # 一覧の取得に失敗したとき、まだ記録していない状態で終えるため、記録より先に取る
        categories = await api.fetch_categories()
        # 送信時刻は、受け取った時刻ではなく Discord が付けた時刻を送る。受け取りが日付をまたいでも送った日の記録にする
        result = await api.record_cash(message.content, message.id, message.created_at)
        if result is None:
            await message.reply(HELP_REPLY)
            return
        if result.outcome is not RecordOutcome.RECORDED:
            # 2通目の返事を送ると、同じ記録にどちらのリアクションで直すべきか分からなくなる
            logger.info(
                "記録しなかったメッセージ: %s（%s）", message.id, result.outcome
            )
            return
        await _reply_recorded(message, result, categories)
    except Exception:
        # Discord のライブラリは受け口の例外をログに出すだけなので、記録が抜けたことを返事で知らせる
        logger.exception("メッセージを記録できませんでした: %s", message.id)
        try:
            await message.reply(RECORD_ERROR_REPLY)
        except Exception:
            logger.exception("記録できなかったことを返事できませんでした")


def _is_owner_dm(user_id: int, guild_id: int | None, owner_id: int) -> bool:
    return user_id == owner_id and guild_id is None


async def _reply_recorded(
    message: discord.Message, result: RecordResult, categories: list[Category]
) -> None:
    # 返信として送る。返信は元のメッセージへの参照を持つので、リアクションから記録を探せる
    reply = await message.reply(format_cash_reply(result))
    for emoji in _reaction_emojis(categories):
        await reply.add_reaction(emoji)
    # TODO: 予算の状態（result.budget）を受け取れるようになったら、新たに超えた閾値ごとに
    #       summary.format_budget_alert() の通知を同じ DM に送る（→ docs/module/discord_bot_design.md）


def _reaction_emojis(categories: list[Category]) -> list[str]:
    return [c.emoji for c in categories[:MAX_REACTIONS]]


async def handle_reaction(
    client: discord.Client,
    payload: discord.RawReactionActionEvent,
    owner_id: int,
    api: ApiClient,
) -> None:
    if not _is_owner_dm(payload.user_id, payload.guild_id, owner_id):
        return

    # キャッシュに無い DM でも、ID だけでメッセージの取得と送信ができる
    channel = client.get_partial_messageable(
        payload.channel_id, type=discord.ChannelType.private
    )
    reply: discord.Message | None = None
    try:
        categories = await api.fetch_categories()
        category = _find_category_by_emoji(categories, str(payload.emoji))
        # カテゴリの絵文字でないリアクション（👍 など）のたびに、Discord の API を呼ばない
        if category is None:
            return

        reply = await channel.fetch_message(payload.message_id)
        if reply.author != client.user or reply.reference is None:
            return
        original_id = reply.reference.message_id
        if original_id is None:
            return

        transaction_id = await api.find_transaction_id_by_source_ref(
            _source_ref(original_id)
        )
        # アプリから削除された記録は、何もしない
        if transaction_id is None:
            return
        # 今と同じカテゴリでも呼ぶ。確定にすることもルールの上書きも、何度行っても結果が変わらない
        await api.select_category(transaction_id, category.id)
    except Exception:
        logger.exception(
            "カテゴリを変更できませんでした: メッセージ %s", payload.message_id
        )
        try:
            if reply is not None:
                await reply.reply(CATEGORY_ERROR_REPLY)
            else:
                await channel.send(CATEGORY_ERROR_REPLY)
        except Exception:
            logger.exception("変更できなかったことを送れませんでした")


def _find_category_by_emoji(categories: list[Category], emoji: str) -> Category | None:
    # 異体字セレクタや肌の色の違う絵文字は、別の絵文字として扱う
    return next((c for c in categories if c.emoji == emoji), None)


def _source_ref(message_id: int) -> str:
    # API の側と形がずれるとリアクションから記録が見つからなくなるため、入口の値から作る
    return f"{Source.DISCORD}:{message_id}"
