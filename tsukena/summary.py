from .model.import_failure_model import ImportFailure
from .model.record_model import RecordResult

UNCATEGORIZED_LABEL = "未分類"
NO_SUBJECT_LABEL = "（件名なし）"


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


def format_import_failure(failure: ImportFailure) -> str:
    """取り込めなかったメールの通知の文面を組み立てる（→ docs/design.md 4.4）。

    送り主・件名・理由と、取り込み直す手順を書く。本文は載せない。
    """
    subject = failure.subject if failure.subject != "" else NO_SUBJECT_LABEL
    # 7日は、取り込みが問い合わせる日数（services.importer.LOOKBACK_DAYS）。
    # summary は純粋ロジックなのでサービス層を import せず、文面に書く
    return (
        "📭 取り込めないメールがありました\n"
        f"送り主: {failure.sender}\n"
        f"件名: {subject}\n"
        f"理由: {failure.reason}\n"
        "このメールの形に、解析がまだ対応していない可能性があります。"
        "解析を直してから、アプリの設定の「取り込めなかったメール」で「取り込み直す」を押してください"
        "（メールが届いてから7日以内に限ります）"
    )
