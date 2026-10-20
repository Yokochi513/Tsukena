from dataclasses import dataclass


@dataclass(frozen=True)
class MailMessage:
    message_id: str
    sender: str
    subject: str
    body: str
