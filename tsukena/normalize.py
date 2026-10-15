# 全角の英数字・記号（！〜～）を半角に変えるための対応表
_FULLWIDTH_TO_HALFWIDTH = {code: code - 0xFEE0 for code in range(0xFF01, 0xFF5F)}


def normalize(text: str) -> str:
    """店名・メモを、分類ルールの照合に使うキー（merchant_key）に正規化する。

    全角英数字・記号の半角化と英字の小文字化を行い、空白（全角を含む）はすべて取り除く。
    「ユニクロ 渋谷店」と「ユニクロ渋谷店」を同じ店として扱うためである。
    カタカナの半角・全角などは変えない。
    """
    # split() は全角の空白も区切りとして扱う
    return "".join(text.translate(_FULLWIDTH_TO_HALFWIDTH).lower().split())
