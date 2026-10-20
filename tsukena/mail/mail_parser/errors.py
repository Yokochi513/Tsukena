class UnparsableMailError(Exception):
    """メールから支払いを取り出せなかった。reason は取り込めなかったメールの一覧に出す"""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
