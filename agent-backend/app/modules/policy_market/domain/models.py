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


@dataclass(frozen=True)
class TopicOption:
    value: str
    count: int


@dataclass(frozen=True)
class MarketOverview:
    total: int
    trend_percent: float | None
    range_label: str
    topic_options: list[TopicOption]


def parse_tags(tags: str | None) -> list[str]:
    if not tags or not tags.strip():
        return []
    return [tag.strip() for tag in tags.split(",") if tag.strip()]
