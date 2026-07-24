from app.modules.policy_market.domain.models import (
    ConsultationRecord,
    MarketOverview,
    ScrollingMessage,
    parse_tags,
)


def _serialize_tags(tags: str | None) -> list[str]:
    return parse_tags(tags)


def serialize_messages(messages: list[ScrollingMessage]) -> list[dict]:
    return [
        {
            "id": message.id,
            "title": message.title,
            "summary": message.summary,
            "linkUrl": message.link_url,
            "province": message.province,
            "publishTime": message.publish_time.isoformat() if message.publish_time else None,
            "tags": _serialize_tags(message.tags),
        }
        for message in messages
    ]


def serialize_overview(overview: MarketOverview) -> dict:
    return {
        "total": overview.total,
        "trendPercent": overview.trend_percent,
        "rangeLabel": overview.range_label,
        "topicOptions": [
            {"value": item.value, "label": item.value, "count": item.count}
            for item in overview.topic_options
        ],
    }


def serialize_consultation_summary(record: ConsultationRecord) -> dict:
    return {
        "id": record.id,
        "title": record.question,
        "question": record.question,
        "status": record.status,
        "createdAt": record.created_at.isoformat() if record.created_at else None,
        "answeredAt": record.answered_at.isoformat() if record.answered_at else None,
    }


def serialize_consultation_detail(record: ConsultationRecord) -> dict:
    return {
        **serialize_consultation_summary(record),
        "answer": record.answer,
        "provinceCode": record.province_code,
        "topic": record.topic,
        "sourceData": record.source_data,
    }
