from dataclasses import dataclass
from datetime import datetime
from typing import Any


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


@dataclass(frozen=True)
class ConsultationAnswer:
    answer: str
    province_code: str | None
    source_data: dict[str, Any]


@dataclass(frozen=True)
class SourceFile:
    """政策源文件的字节内容与展示元信息。

    知识库来源在飞书上，外部用户打不开飞书；本系统代理下载后用这个结构回传。
    """
    content: bytes
    filename: str
    content_type: str


@dataclass(frozen=True)
class ConsultationRecord:
    id: int
    user_id: str
    question: str
    answer: str | None
    province_code: str | None
    topic: str | None
    status: str
    source_data: dict[str, Any] | None
    created_at: datetime | None
    answered_at: datetime | None
    updated_at: datetime | None


def parse_tags(tags: str | None) -> list[str]:
    if not tags or not tags.strip():
        return []
    return [tag.strip() for tag in tags.split(",") if tag.strip()]
