from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class StoredMessage:
    id: int
    group_id: int
    telegram_message_id: int
    user_id: int
    username: str
    text: str
    created_at: str


@dataclass(slots=True)
class ApprovedGroup:
    group_id: int
    group_title: str
    approved_at: str

