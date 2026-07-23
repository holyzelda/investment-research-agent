from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ScrollingMessage:
    id: int
    title: str
    summary: str | None
    link_url: str | None
    province: str | None
    publish_time: datetime | None
    tags: str | None
