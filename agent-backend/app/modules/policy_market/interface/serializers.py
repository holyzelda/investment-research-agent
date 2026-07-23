from app.modules.policy_market.domain.models import ScrollingMessage


def _serialize_tags(tags: str | None) -> list[str]:
    if not tags or not tags.strip():
        return []
    return [tag.strip() for tag in tags.split(",") if tag.strip()]


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
