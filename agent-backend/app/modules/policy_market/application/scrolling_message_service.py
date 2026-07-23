from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.policy_market.domain.models import ScrollingMessage
from app.modules.policy_market.infrastructure.persistence.orm import ScrollingMessageORM


class ScrollingMessageService:
    async def list_messages(
        self,
        session: AsyncSession,
        *,
        now: datetime | None = None,
    ) -> list[ScrollingMessage]:
        query_time = now or datetime.now()
        statement = (
            select(ScrollingMessageORM)
            .where(
                ScrollingMessageORM.is_deleted == 0,
                ScrollingMessageORM.status == 1,
                or_(
                    ScrollingMessageORM.expire_time.is_(None),
                    ScrollingMessageORM.expire_time > query_time,
                ),
            )
            .order_by(
                ScrollingMessageORM.sort_order.desc(),
                ScrollingMessageORM.rating.desc(),
                ScrollingMessageORM.publish_time.desc(),
                ScrollingMessageORM.id.desc(),
            )
        )
        rows = (await session.execute(statement)).scalars().all()
        return [
            ScrollingMessage(
                id=row.id,
                title=row.title,
                summary=row.summary,
                link_url=row.link_url,
                province=row.province,
                publish_time=row.publish_time,
                tags=row.tags,
            )
            for row in rows
        ]
