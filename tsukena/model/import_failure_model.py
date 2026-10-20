import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class ImportFailure:
    message_id: str
    sender: str
    subject: str
    reason: str
    failed_at: datetime.datetime
