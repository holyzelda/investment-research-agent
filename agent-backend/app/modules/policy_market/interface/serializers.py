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


def _with_download_urls(source_data):
    """给知识库来源补上后端代理下载地址。

    在序列化层补而不是落库时补：历史快照里的 references 也能立刻用上下载能力，
    不需要数据迁移；地址变了也不用改存量数据。

    只补 wiki 类（飞书文件，外部用户打不开原链接）；web 类是公网链接，前端直接跳。
    """
    if not isinstance(source_data, dict):
        return source_data
    references = source_data.get("references")
    if not isinstance(references, list):
        return source_data

    enriched = []
    for item in references:
        if not isinstance(item, dict):
            continue
        token = str(item.get("token") or "").strip()
        if item.get("type") == "wiki" and token:
            item = {**item, "downloadUrl": f"/ir/policy-market/source-files/{token}"}
        enriched.append(item)
    return {**source_data, "references": enriched}


def serialize_consultation_detail(record: ConsultationRecord) -> dict:
    return {
        **serialize_consultation_summary(record),
        "answer": record.answer,
        "provinceCode": record.province_code,
        "topic": record.topic,
        "sourceData": _with_download_urls(record.source_data),
    }
