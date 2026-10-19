from dataclasses import dataclass


@dataclass(frozen=True)
class ApiTokens:
    app: str
    bot: str
