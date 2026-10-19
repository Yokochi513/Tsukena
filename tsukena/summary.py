from .model.record_model import RecordResult

UNCATEGORIZED_LABEL = "未分類"


def format_cash_reply(result: RecordResult) -> str:
    """現金を記録したときの返事の文面を組み立てる。

    例: 「🍚 食費 800円 で記録しました」。カテゴリが未設定なら「未分類」と表示する。
    """
    # TODO: 予算の状態（budget）を受け取れるようになったら、「（今月あと 32,000円）」を足す
    #       （→ docs/module/discord_bot_design.md の summary.format_cash_reply()）
    if result.transaction is None:
        raise ValueError("記録されていない結果からは返事を作れません")
    category = (
        f"{result.category.emoji} {result.category.name}"
        if result.category is not None
        else UNCATEGORIZED_LABEL
    )
    return f"{category} {result.transaction.amount:,}円 で記録しました"
