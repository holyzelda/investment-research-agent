from app.modules.policy_market.domain.models import MarketOverview, ScrollingMessage, parse_tags


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
